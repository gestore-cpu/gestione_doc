"""
Job scheduler per la revisione periodica AI delle policy automatiche.
"""

import json
import openai
from datetime import datetime, timedelta
from sqlalchemy import func
from models import AccessRequest, AutoPolicy, PolicyReview, User
from extensions import db
from utils.logging import log_audit_event
from utils.mail import send_admin_notification

def ai_review_policies_job():
    """
    Job mensile per la revisione AI delle policy automatiche.
    Eseguito il primo giorno del mese alle 3:00.
    """
    try:
        print("[AI Review Policies] Iniziando revisione periodica...")
        
        # 1. Recupero richieste ultimo mese
        start_date = datetime.utcnow() - timedelta(days=30)
        requests = AccessRequest.query.filter(
            AccessRequest.created_at >= start_date
        ).join(User).all()
        
        # 2. Recupero policy attive
        active_policies = AutoPolicy.query.filter_by(active=True).all()
        
        # 3. Statistiche periodo
        total_requests = len(requests)
        auto_approved = sum(1 for r in requests if r.status == 'approved' and r.risposta_ai)
        auto_denied = sum(1 for r in requests if r.status == 'denied' and r.risposta_ai)
        manual_review = total_requests - auto_approved - auto_denied
        
        # 4. Struttura dati per AI
        data = {
            "period": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": datetime.utcnow().strftime('%Y-%m-%d'),
                "total_requests": total_requests,
                "auto_approved": auto_approved,
                "auto_denied": auto_denied,
                "manual_review": manual_review
            },
            "requests": [{
                "id": r.id,
                "user_role": r.user.role if r.user else "N/A",
                "user_company": r.document.company.name if r.document and r.document.company else "N/A",
                "document_name": r.document.title or r.document.original_filename if r.document else "N/A",
                "document_company": r.document.company.name if r.document and r.document.company else "N/A",
                "status": r.status,
                "note": r.note or "",
                "auto_decision": bool(r.risposta_ai),
                "created_at": r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else "N/A"
            } for r in requests],
            "policies": [{
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "condition": p.condition,
                "action": p.action,
                "priority": p.priority,
                "confidence": p.confidence,
                "active": p.active
            } for p in active_policies]
        }
        
        # 5. Prompt AI
        prompt = f"""
Sei un consulente di sicurezza documentale aziendale esperto in policy di accesso automatiche.

Analizza i seguenti dati delle richieste di accesso degli ultimi 30 giorni e delle policy attive:

PERIODO ANALIZZATO:
- Da: {data['period']['start_date']} a {data['period']['end_date']}
- Richieste totali: {data['period']['total_requests']}
- Auto-approvate: {data['period']['auto_approved']}
- Auto-negate: {data['period']['auto_denied']}
- Revisione manuale: {data['period']['manual_review']}

RICHIESTE DI ACCESSO:
{json.dumps(data['requests'], ensure_ascii=False, indent=2)}

POLICY ATTIVE:
{json.dumps(data['policies'], ensure_ascii=False, indent=2)}

Genera un report completo che includa:

1. VALUTAZIONE EFFICACIA POLICY ATTIVE:
   - Analisi performance di ogni policy
   - Identificazione policy poco efficaci
   - Suggerimenti di ottimizzazione

2. PATTERN EMERGENTI:
   - Nuovi pattern di richieste non coperti
   - Trend temporali o per ruolo/azienda
   - Anomalie o comportamenti sospetti

3. SUGGERIMENTI MODIFICHE POLICY ESISTENTI:
   - Policy da modificare con nuove condizioni
   - Policy da disattivare per inefficacia
   - Aggiustamenti di priorità o confidenza

4. NUOVE POLICY PROPOSTE:
   - Regole per pattern non coperti
   - Policy preventive per rischi emergenti
   - Ottimizzazioni basate sui dati

Rispondi in formato JSON con:
{{
    "report": "Report dettagliato in italiano",
    "suggestions": [
        {{
            "type": "modify|disable|new",
            "policy_id": null,
            "condition": "condizione JSON o naturale",
            "action": "approve|deny",
            "priority": 1-5,
            "confidence": 0-100,
            "explanation": "motivazione del suggerimento"
        }}
    ],
    "summary": "Riassunto esecutivo"
}}
"""
        
        # 6. Chiamata AI
        ai_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sei un esperto consulente di sicurezza documentale aziendale. Fornisci analisi precise e suggerimenti pratici."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        # 7. Parsing risposta AI
        try:
            ai_data = json.loads(ai_response["choices"][0]["message"]["content"])
        except json.JSONDecodeError:
            # Fallback se AI non restituisce JSON valido
            ai_data = {
                "report": ai_response["choices"][0]["message"]["content"],
                "suggestions": [],
                "summary": "Analisi AI completata"
            }
        
        # 8. Salvataggio review
        review = PolicyReview(
            report=ai_data.get("report", ""),
            suggestions=ai_data.get("suggestions", []),
            status='pending'
        )
        
        db.session.add(review)
        db.session.commit()
        
        # 9. Log audit
        log_audit_event(
            action="ai_policy_review_created",
            details=f"Review AI policy creata: ID {review.id}",
            user_id=None,  # Sistema automatico
            extra_info={
                'review_id': review.id,
                'total_requests': total_requests,
                'active_policies': len(active_policies),
                'suggestions_count': len(ai_data.get("suggestions", []))
            }
        )
        
        # 10. Notifica admin
        admin_users = User.query.filter_by(role='admin').all()
        for admin in admin_users:
            send_admin_notification(
                user=admin,
                subject="📊 Nuovo Report Revisione AI Policy",
                message=f"""
È disponibile un nuovo report di revisione AI delle policy automatiche.

📋 Dettagli:
- ID Review: {review.id}
- Periodo: {data['period']['start_date']} - {data['period']['end_date']}
- Richieste analizzate: {total_requests}
- Policy attive: {len(active_policies)}
- Suggerimenti: {len(ai_data.get("suggestions", []))}

🔗 Visualizza report: /admin/policy_reviews/{review.id}
                """,
                action_url=f"/admin/policy_reviews/{review.id}",
                action_text="Visualizza Report"
            )
        
        print(f"[AI Review Policies] Review {review.id} creata con successo")
        return review
        
    except Exception as e:
        print(f"[AI Review Policies] Errore durante revisione: {e}")
        
        # Log errore
        log_audit_event(
            action="ai_policy_review_error",
            details=f"Errore revisione AI policy: {str(e)}",
            user_id=None,
            extra_info={'error': str(e)}
        )
        
        return None

def generate_policy_review_summary():
    """
    Genera un riassunto delle review AI per dashboard admin.
    """
    try:
        # Statistiche review
        stats = PolicyReview.get_review_statistics()
        
        # Review recenti
        recent_reviews = PolicyReview.get_recent_reviews(5)
        
        # Suggerimenti totali
        total_suggestions = sum(r.get_suggestions_count() for r in recent_reviews)
        applied_suggestions = sum(r.get_applied_suggestions_count() for r in recent_reviews)
        
        return {
            'stats': stats,
            'recent_reviews': recent_reviews,
            'total_suggestions': total_suggestions,
            'applied_suggestions': applied_suggestions,
            'suggestion_rate': (applied_suggestions / total_suggestions * 100) if total_suggestions > 0 else 0
        }
        
    except Exception as e:
        print(f"Errore generazione summary review: {e}")
        return {
            'stats': {'total': 0, 'pending': 0, 'reviewed': 0, 'applied': 0},
            'recent_reviews': [],
            'total_suggestions': 0,
            'applied_suggestions': 0,
            'suggestion_rate': 0
        }

def apply_ai_suggestion(suggestion_data):
    """
    Applica un suggerimento AI creando una nuova policy.
    """
    try:
        from models import AutoPolicy
        
        # Crea nuova policy dal suggerimento
        new_policy = AutoPolicy(
            name=f"Policy AI - {datetime.utcnow().strftime('%Y%m%d_%H%M')}",
            description=suggestion_data.get('explanation', 'Policy generata da AI'),
            condition=suggestion_data.get('condition', ''),
            action=suggestion_data.get('action', 'approve'),
            priority=suggestion_data.get('priority', 3),
            confidence=suggestion_data.get('confidence', 70),
            active=False  # Richiede attivazione manuale
        )
        
        db.session.add(new_policy)
        db.session.commit()
        
        # Log audit
        log_audit_event(
            action="ai_suggestion_applied",
            details=f"Policy creata da suggerimento AI: {new_policy.id}",
            user_id=None,
            extra_info={
                'policy_id': new_policy.id,
                'suggestion_data': suggestion_data
            }
        )
        
        return new_policy
        
    except Exception as e:
        print(f"Errore applicazione suggerimento AI: {e}")
        db.session.rollback()
        return None 