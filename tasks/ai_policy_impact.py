#!/usr/bin/env python3
"""
Job scheduler per report AI di impatto delle policy attive.
"""

import json
import openai
from datetime import datetime, timedelta
from models import AccessRequest, AutoPolicy, PolicyImpactReport, User
from extensions import db
from utils.logging import log_audit_event
from utils.mail import send_admin_notification

def ai_policy_impact_report_job():
    """
    Job mensile per generare report AI di impatto delle policy attive.
    Analizza le richieste gestite automaticamente negli ultimi 30 giorni.
    """
    try:
        print("[AI Policy Impact Report] Inizio generazione report...")
        start_time = datetime.utcnow()
        
        # Calcola periodo di analisi (ultimi 30 giorni)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        # Recupera richieste gestite automaticamente
        auto_requests = AccessRequest.query.filter(
            AccessRequest.created_at >= start_date,
            AccessRequest.created_at <= end_date,
            AccessRequest.risposta_admin.ilike('%Decisione automatica tramite policy%')
        ).all()
        
        print(f"[AI Policy Impact Report] Trovate {len(auto_requests)} richieste automatiche")
        
        # Calcola statistiche base
        total_requests = len(auto_requests)
        approve_count = len([r for r in auto_requests if r.status == 'approve'])
        deny_count = len([r for r in auto_requests if r.status == 'deny'])
        
        # Calcola success rate (decisioni non modificate manualmente)
        success_count = len([r for r in auto_requests if not getattr(r, 'modified_by_admin', False)])
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0.0
        
        # Analizza breakdown per policy
        policy_breakdown = analyze_policy_breakdown(auto_requests)
        
        # Identifica casi di errore
        error_cases = identify_error_cases(auto_requests)
        
        # Prepara dati per AI
        analysis_data = prepare_analysis_data(auto_requests, policy_breakdown, error_cases)
        
        # Genera analisi AI
        ai_analysis = generate_ai_analysis(analysis_data, {
            'total_requests': total_requests,
            'approve_count': approve_count,
            'deny_count': deny_count,
            'success_rate': success_rate,
            'period_start': start_date,
            'period_end': end_date
        })
        
        # Calcola tempo di elaborazione
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Crea report
        report = PolicyImpactReport(
            total_auto_processed=total_requests,
            approve_count=approve_count,
            deny_count=deny_count,
            success_rate=success_rate,
            ai_analysis=ai_analysis,
            policy_breakdown=policy_breakdown,
            error_cases=error_cases,
            period_start=start_date,
            period_end=end_date,
            processing_time=processing_time
        )
        
        db.session.add(report)
        db.session.commit()
        
        # Log audit
        log_audit_event(
            action="ai_policy_impact_report_generated",
            details=f"Report impatto policy generato - ID: {report.id}, Richieste: {total_requests}, Success Rate: {success_rate:.1f}%",
            extra_info={
                'report_id': report.id,
                'total_requests': total_requests,
                'success_rate': success_rate,
                'processing_time': processing_time
            }
        )
        
        # Invia notifica admin
        send_admin_notification(
            subject="📊 Report AI Impatto Policy Generato",
            body=f"""
            È stato generato il report AI di impatto delle policy attive.
            
            📈 Statistiche:
            - Richieste gestite automaticamente: {total_requests}
            - Approvazioni: {approve_count}
            - Dinieghi: {deny_count}
            - Tasso di successo: {success_rate:.1f}%
            - Periodo analizzato: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}
            
            ID Report: {report.id}
            """,
            link=f"/admin/policy_impact_reports/{report.id}"
        )
        
        print(f"[AI Policy Impact Report] Report generato con successo - ID: {report.id}")
        return report
        
    except Exception as e:
        print(f"[AI Policy Impact Report] Errore durante la generazione: {str(e)}")
        log_audit_event(
            action="ai_policy_impact_report_error",
            details=f"Errore generazione report impatto policy: {str(e)}",
            extra_info={'error': str(e)}
        )
        raise

def analyze_policy_breakdown(auto_requests):
    """
    Analizza le statistiche per ogni policy utilizzata.
    """
    policy_stats = {}
    
    for request in auto_requests:
        # Estrai policy ID dal messaggio di risposta
        policy_id = extract_policy_id_from_response(request.risposta_admin)
        
        if policy_id:
            if policy_id not in policy_stats:
                policy_stats[policy_id] = {
                    'policy_id': policy_id,
                    'requests_processed': 0,
                    'approve_count': 0,
                    'deny_count': 0,
                    'success_count': 0
                }
            
            policy_stats[policy_id]['requests_processed'] += 1
            
            if request.status == 'approve':
                policy_stats[policy_id]['approve_count'] += 1
            elif request.status == 'deny':
                policy_stats[policy_id]['deny_count'] += 1
            
            # Controlla se la decisione è stata modificata manualmente
            if not getattr(request, 'modified_by_admin', False):
                policy_stats[policy_id]['success_count'] += 1
    
    # Calcola success rate per ogni policy
    breakdown = []
    for policy_id, stats in policy_stats.items():
        success_rate = (stats['success_count'] / stats['requests_processed'] * 100) if stats['requests_processed'] > 0 else 0.0
        
        # Recupera info policy
        policy = AutoPolicy.query.get(policy_id)
        policy_name = policy.name if policy else f"Policy #{policy_id}"
        action = policy.action if policy else 'unknown'
        
        breakdown.append({
            'policy_id': policy_id,
            'policy_name': policy_name,
            'action': action,
            'requests_processed': stats['requests_processed'],
            'approve_count': stats['approve_count'],
            'deny_count': stats['deny_count'],
            'success_rate': success_rate
        })
    
    return breakdown

def identify_error_cases(auto_requests):
    """
    Identifica possibili casi di errore o falsi positivi/negativi.
    """
    error_cases = []
    
    # Casi di richieste modificate manualmente (possibili errori)
    modified_requests = [r for r in auto_requests if getattr(r, 'modified_by_admin', False)]
    if modified_requests:
        error_cases.append({
            'type': 'manual_modifications',
            'count': len(modified_requests),
            'description': 'Richieste modificate manualmente dopo decisione automatica',
            'examples': [
                {
                    'request_id': r.id,
                    'original_status': r.status,
                    'modified_status': getattr(r, 'modified_status', 'unknown'),
                    'modification_reason': getattr(r, 'modification_reason', 'N/A')
                }
                for r in modified_requests[:5]  # Limita a 5 esempi
            ]
        })
    
    # Casi di richieste ripetute (possibili falsi negativi)
    user_file_combinations = {}
    for request in auto_requests:
        key = f"{request.user_id}_{request.file_id}"
        if key not in user_file_combinations:
            user_file_combinations[key] = []
        user_file_combinations[key].append(request)
    
    repeated_requests = [requests for requests in user_file_combinations.values() if len(requests) > 1]
    if repeated_requests:
        error_cases.append({
            'type': 'repeated_requests',
            'count': len(repeated_requests),
            'description': 'Utenti che hanno ripetuto richieste dopo diniego automatico',
            'examples': [
                {
                    'user_id': requests[0].user_id,
                    'file_id': requests[0].file_id,
                    'request_count': len(requests),
                    'first_request': requests[0].created_at.isoformat(),
                    'last_request': requests[-1].created_at.isoformat()
                }
                for requests in repeated_requests[:3]  # Limita a 3 esempi
            ]
        })
    
    # Casi di richieste con note lunghe (possibili contestazioni)
    long_note_requests = [r for r in auto_requests if r.motivazione and len(r.motivazione) > 100]
    if long_note_requests:
        error_cases.append({
            'type': 'long_notes',
            'count': len(long_note_requests),
            'description': 'Richieste con note lunghe (possibili contestazioni)',
            'examples': [
                {
                    'request_id': r.id,
                    'note_length': len(r.motivazione),
                    'note_preview': r.motivazione[:50] + '...' if len(r.motivazione) > 50 else r.motivazione
                }
                for r in long_note_requests[:3]  # Limita a 3 esempi
            ]
        })
    
    return error_cases

def prepare_analysis_data(auto_requests, policy_breakdown, error_cases):
    """
    Prepara i dati per l'analisi AI.
    """
    # Raggruppa richieste per utente
    user_stats = {}
    for request in auto_requests:
        user_id = request.user_id
        if user_id not in user_stats:
            user_stats[user_id] = {
                'user_id': user_id,
                'user_name': request.user.name if request.user else 'Unknown',
                'user_role': request.user.role if request.user else 'Unknown',
                'total_requests': 0,
                'approve_count': 0,
                'deny_count': 0
            }
        
        user_stats[user_id]['total_requests'] += 1
        if request.status == 'approve':
            user_stats[user_id]['approve_count'] += 1
        elif request.status == 'deny':
            user_stats[user_id]['deny_count'] += 1
    
    # Raggruppa richieste per file
    file_stats = {}
    for request in auto_requests:
        if request.file:
            file_id = request.file_id
            if file_id not in file_stats:
                file_stats[file_id] = {
                    'file_id': file_id,
                    'file_name': request.file.name,
                    'total_requests': 0,
                    'approve_count': 0,
                    'deny_count': 0
                }
            
            file_stats[file_id]['total_requests'] += 1
            if request.status == 'approve':
                file_stats[file_id]['approve_count'] += 1
            elif request.status == 'deny':
                file_stats[file_id]['deny_count'] += 1
    
    return {
        'requests': [
            {
                'id': r.id,
                'user_name': r.user.name if r.user else 'Unknown',
                'user_role': r.user.role if r.user else 'Unknown',
                'file_name': r.file.name if r.file else 'Unknown',
                'status': r.status,
                'created_at': r.created_at.isoformat(),
                'motivazione': r.motivazione or '',
                'policy_response': r.risposta_admin or '',
                'modified_by_admin': getattr(r, 'modified_by_admin', False)
            }
            for r in auto_requests
        ],
        'user_stats': list(user_stats.values()),
        'file_stats': list(file_stats.values()),
        'policy_breakdown': policy_breakdown,
        'error_cases': error_cases
    }

def generate_ai_analysis(analysis_data, summary_stats):
    """
    Genera l'analisi AI basata sui dati raccolti.
    """
    prompt = f"""
Analizza il seguente dataset di richieste di accesso gestite automaticamente da policy AI:

📊 STATISTICHE GENERALI:
- Totale richieste gestite automaticamente: {summary_stats['total_requests']}
- Approvazioni automatiche: {summary_stats['approve_count']}
- Dinieghi automatici: {summary_stats['deny_count']}
- Tasso di successo: {summary_stats['success_rate']:.1f}%
- Periodo analizzato: {summary_stats['period_start'].strftime('%d/%m/%Y')} - {summary_stats['period_end'].strftime('%d/%m/%Y')}

📋 DATI DETTAGLIATI:
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

Genera un report analitico che includa:

1. 📈 ANALISI DELL'EFFICACIA:
   - Valutazione del tasso di successo delle policy
   - Identificazione delle policy più efficaci
   - Analisi delle policy con problemi

2. 🔍 PATTERN RICORRENTI:
   - Utenti con più richieste automatiche
   - File più richiesti automaticamente
   - Pattern temporali nelle richieste

3. ⚠️ PROBLEMI IDENTIFICATI:
   - Casi di falsi positivi/negativi
   - Richieste contestate o modificate
   - Policy che necessitano ottimizzazione

4. 💡 RACCOMANDAZIONI:
   - Suggerimenti per migliorare le policy
   - Policy da attivare/disattivare
   - Nuove regole da considerare

5. 📊 INSIGHT OPERATIVI:
   - Impatto delle policy sul workflow
   - Benefici quantificabili
   - Aree di miglioramento

Fornisci una risposta strutturata e dettagliata in italiano, con sezioni chiare e raccomandazioni concrete.
"""

    try:
        ai_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sei un consulente esperto di sicurezza documentale aziendale. Analizzi l'efficacia di sistemi di policy automatiche e fornisci raccomandazioni concrete per l'ottimizzazione."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        return ai_response["choices"][0]["message"]["content"]
        
    except Exception as e:
        return f"Errore durante l'analisi AI: {str(e)}"

def extract_policy_id_from_response(response_text):
    """
    Estrae l'ID della policy dal testo di risposta.
    """
    if not response_text:
        return None
    
    # Cerca pattern come "policy #123" o "policy 123"
    import re
    patterns = [
        r'policy\s*#?(\d+)',
        r'policy\s*(\d+)',
        r'tramite\s*policy\s*#?(\d+)',
        r'policy\s*ID\s*(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return None

def trigger_manual_impact_report():
    """
    Trigger manuale per generare report di impatto.
    """
    try:
        print("[AI Policy Impact Report] Trigger manuale avviato...")
        report = ai_policy_impact_report_job()
        return report
    except Exception as e:
        print(f"[AI Policy Impact Report] Errore trigger manuale: {str(e)}")
        raise 