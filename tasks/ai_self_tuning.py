#!/usr/bin/env python3
"""
Job scheduler per auto-tuning automatico delle policy basato sui report di impatto.
"""

import json
import openai
from datetime import datetime, timedelta
from models import AutoPolicy, PolicyImpactReport, PolicyChangeLog
from extensions import db
from utils.logging import log_audit_event
from utils.mail import send_admin_notification

def ai_self_tune_policies_job():
    """
    Job mensile per auto-tuning delle policy basato sui report di impatto.
    Analizza le policy poco efficaci e le ottimizza automaticamente.
    """
    try:
        print("[AI Self-Tuning] Inizio processo di auto-tuning...")
        start_time = datetime.utcnow()
        
        # 1. Recupera ultimo report di impatto
        last_report = PolicyImpactReport.query.order_by(
            PolicyImpactReport.created_at.desc()
        ).first()
        
        if not last_report:
            print("[AI Self-Tuning] Nessun report di impatto trovato.")
            return
        
        print(f"[AI Self-Tuning] Utilizzando report #{last_report.id} del {last_report.created_at.strftime('%d/%m/%Y')}")
        
        # 2. Recupera policy attive
        active_policies = AutoPolicy.query.filter_by(active=True).all()
        
        if not active_policies:
            print("[AI Self-Tuning] Nessuna policy attiva trovata.")
            return
        
        print(f"[AI Self-Tuning] Trovate {len(active_policies)} policy attive")
        
        # 3. Analizza performance delle policy
        policy_performance = analyze_policy_performance(active_policies, last_report)
        
        # 4. Identifica policy da ottimizzare
        policies_to_optimize = identify_policies_to_optimize(policy_performance)
        
        if not policies_to_optimize:
            print("[AI Self-Tuning] Nessuna policy richiede ottimizzazione.")
            return
        
        print(f"[AI Self-Tuning] Identificate {len(policies_to_optimize)} policy da ottimizzare")
        
        # 5. Genera suggerimenti AI per ottimizzazione
        optimization_suggestions = generate_optimization_suggestions(
            policies_to_optimize, 
            last_report, 
            active_policies
        )
        
        # 6. Applica modifiche con validazione
        applied_changes = apply_optimization_changes(optimization_suggestions)
        
        # 7. Calcola tempo di elaborazione
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 8. Log audit e notifiche
        log_audit_event(
            action="ai_self_tuning_completed",
            details=f"Auto-tuning completato - {len(applied_changes)} policy ottimizzate",
            extra_info={
                'report_id': last_report.id,
                'policies_analyzed': len(active_policies),
                'policies_optimized': len(applied_changes),
                'processing_time': processing_time
            }
        )
        
        # 9. Invia notifica admin
        send_admin_notification(
            subject="🤖 Auto-Tuning Policy Completato",
            body=f"""
            Il sistema AI ha completato l'auto-tuning delle policy.
            
            📊 Risultati:
            - Policy analizzate: {len(active_policies)}
            - Policy ottimizzate: {len(applied_changes)}
            - Tempo elaborazione: {processing_time:.2f}s
            
            📋 Modifiche applicate:
            {format_applied_changes(applied_changes)}
            
            Report utilizzato: #{last_report.id}
            """,
            link="/admin/policy_change_logs"
        )
        
        print(f"[AI Self-Tuning] Auto-tuning completato - {len(applied_changes)} policy ottimizzate")
        return applied_changes
        
    except Exception as e:
        print(f"[AI Self-Tuning] Errore durante l'auto-tuning: {str(e)}")
        log_audit_event(
            action="ai_self_tuning_error",
            details=f"Errore auto-tuning: {str(e)}",
            extra_info={'error': str(e)}
        )
        raise

def analyze_policy_performance(active_policies, impact_report):
    """
    Analizza la performance delle policy basandosi sul report di impatto.
    """
    performance_data = {}
    
    # Recupera breakdown delle policy dal report
    policy_breakdown = impact_report.get_policy_breakdown_summary()
    
    for policy in active_policies:
        # Trova statistiche per questa policy
        policy_stats = next(
            (stats for stats in policy_breakdown if stats['policy_id'] == policy.id),
            None
        )
        
        if policy_stats:
            performance_data[policy.id] = {
                'policy': policy,
                'requests_processed': policy_stats['requests_processed'],
                'success_rate': policy_stats['success_rate'],
                'action': policy_stats['action'],
                'needs_optimization': policy_stats['success_rate'] < 70,  # Soglia di ottimizzazione
                'optimization_priority': calculate_optimization_priority(policy_stats)
            }
        else:
            # Policy senza statistiche (nuova o non utilizzata)
            performance_data[policy.id] = {
                'policy': policy,
                'requests_processed': 0,
                'success_rate': 0,
                'action': policy.action,
                'needs_optimization': True,
                'optimization_priority': 'high'
            }
    
    return performance_data

def calculate_optimization_priority(policy_stats):
    """
    Calcola la priorità di ottimizzazione per una policy.
    """
    success_rate = policy_stats['success_rate']
    requests_processed = policy_stats['requests_processed']
    
    if success_rate < 50:
        return 'critical'
    elif success_rate < 70:
        return 'high'
    elif success_rate < 85:
        return 'medium'
    else:
        return 'low'

def identify_policies_to_optimize(performance_data):
    """
    Identifica le policy che necessitano ottimizzazione.
    """
    policies_to_optimize = []
    
    for policy_id, data in performance_data.items():
        if data['needs_optimization'] and data['requests_processed'] > 0:
            policies_to_optimize.append({
                'policy': data['policy'],
                'current_performance': data,
                'optimization_priority': data['optimization_priority']
            })
    
    # Ordina per priorità di ottimizzazione
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    policies_to_optimize.sort(
        key=lambda x: priority_order.get(x['optimization_priority'], 4)
    )
    
    return policies_to_optimize

def generate_optimization_suggestions(policies_to_optimize, impact_report, all_policies):
    """
    Genera suggerimenti AI per l'ottimizzazione delle policy.
    """
    # Prepara dati per l'AI
    optimization_data = {
        'impact_report': {
            'total_requests': impact_report.total_auto_processed,
            'success_rate': impact_report.success_rate,
            'analysis': impact_report.ai_analysis,
            'error_cases': impact_report.get_error_cases_summary(),
            'recommendations': impact_report.get_recommendations_summary()
        },
        'policies_to_optimize': [
            {
                'id': item['policy'].id,
                'name': item['policy'].name,
                'condition': item['policy'].condition,
                'action': item['policy'].action,
                'explanation': item['policy'].explanation,
                'priority': item['policy'].priority,
                'confidence': item['policy'].confidence,
                'current_performance': item['current_performance'],
                'optimization_priority': item['optimization_priority']
            }
            for item in policies_to_optimize
        ],
        'all_active_policies': [
            {
                'id': p.id,
                'name': p.name,
                'condition': p.condition,
                'action': p.action,
                'explanation': p.explanation
            }
            for p in all_policies
        ]
    }
    
    # Prompt per l'AI
    prompt = f"""
Analizza le policy che necessitano ottimizzazione basandoti sui seguenti dati:

📊 REPORT DI IMPATTO:
- Success Rate Generale: {optimization_data['impact_report']['success_rate']:.1f}%
- Richieste Totali: {optimization_data['impact_report']['total_requests']}
- Analisi AI: {optimization_data['impact_report']['analysis'][:500]}...

🔍 POLICY DA OTTIMIZZARE:
{json.dumps(optimization_data['policies_to_optimize'], ensure_ascii=False, indent=2)}

📋 POLICY ATTIVE (per contesto):
{json.dumps(optimization_data['all_active_policies'], ensure_ascii=False, indent=2)}

Genera suggerimenti di ottimizzazione per le policy con performance basse.
Considera:
1. Pattern di errore dal report di impatto
2. Condizioni troppo restrittive o permissive
3. Azioni inappropriate per il contesto
4. Priorità e confidenza da regolare

Rispondi in JSON con questo formato:
{{
    "optimizations": [
        {{
            "policy_id": 123,
            "reason": "Motivo dell'ottimizzazione",
            "new_condition": "condizione_aggiornata",
            "new_action": "approve/deny",
            "new_explanation": "spiegazione_aggiornata",
            "new_priority": 1-5,
            "new_confidence": 0-100,
            "expected_impact": "descrizione impatto atteso"
        }}
    ]
}}

Suggerisci solo modifiche significative e ben giustificate.
"""

    try:
        ai_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Sei un ottimizzatore esperto di regole di accesso documentale. Analizzi policy con performance basse e suggerisci miglioramenti specifici e giustificati."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        response_content = ai_response["choices"][0]["message"]["content"]
        optimization_data = json.loads(response_content)
        
        return optimization_data.get("optimizations", [])
        
    except Exception as e:
        print(f"[AI Self-Tuning] Errore nella generazione suggerimenti: {str(e)}")
        return []

def apply_optimization_changes(optimization_suggestions):
    """
    Applica le modifiche di ottimizzazione con validazione.
    """
    applied_changes = []
    
    for suggestion in optimization_suggestions:
        try:
            policy_id = suggestion.get('policy_id')
            policy = AutoPolicy.query.get(policy_id)
            
            if not policy:
                print(f"[AI Self-Tuning] Policy {policy_id} non trovata")
                continue
            
            # Validazione modifiche
            if not validate_optimization_suggestion(suggestion):
                print(f"[AI Self-Tuning] Suggerimento per policy {policy_id} non valido")
                continue
            
            # Crea log entry
            log_entry = PolicyChangeLog(
                policy_id=policy.id,
                old_condition=policy.condition,
                old_action=policy.action,
                old_explanation=policy.explanation,
                old_priority=policy.priority,
                old_confidence=policy.confidence,
                new_condition=suggestion.get('new_condition'),
                new_action=suggestion.get('new_action'),
                new_explanation=suggestion.get('new_explanation'),
                new_priority=suggestion.get('new_priority'),
                new_confidence=suggestion.get('new_confidence'),
                change_reason=suggestion.get('reason'),
                impact_score=calculate_impact_score(suggestion),
                changed_by_ai=True
            )
            
            # Aggiorna policy
            policy.condition = suggestion.get('new_condition')
            policy.action = suggestion.get('new_action')
            policy.explanation = suggestion.get('new_explanation')
            policy.priority = suggestion.get('new_priority', policy.priority)
            policy.confidence = suggestion.get('new_confidence', policy.confidence)
            
            # Salva modifiche
            db.session.add(log_entry)
            db.session.commit()
            
            # Log audit
            log_audit_event(
                action="policy_auto_optimized",
                details=f"Policy {policy.id} ottimizzata dall'AI",
                extra_info={
                    'policy_id': policy.id,
                    'reason': suggestion.get('reason'),
                    'expected_impact': suggestion.get('expected_impact'),
                    'impact_score': log_entry.impact_score
                }
            )
            
            applied_changes.append({
                'policy_id': policy.id,
                'policy_name': policy.name,
                'changes': log_entry.get_change_summary(),
                'reason': suggestion.get('reason'),
                'expected_impact': suggestion.get('expected_impact')
            })
            
            print(f"[AI Self-Tuning] Policy {policy.id} ottimizzata: {log_entry.get_change_summary()}")
            
        except Exception as e:
            print(f"[AI Self-Tuning] Errore nell'applicazione modifica per policy {policy_id}: {str(e)}")
            db.session.rollback()
            continue
    
    return applied_changes

def validate_optimization_suggestion(suggestion):
    """
    Valida un suggerimento di ottimizzazione.
    """
    required_fields = ['policy_id', 'new_condition', 'new_action']
    
    for field in required_fields:
        if not suggestion.get(field):
            return False
    
    # Validazione azione
    if suggestion['new_action'] not in ['approve', 'deny']:
        return False
    
    # Validazione priorità
    if 'new_priority' in suggestion:
        if not isinstance(suggestion['new_priority'], int) or suggestion['new_priority'] < 1 or suggestion['new_priority'] > 5:
            return False
    
    # Validazione confidenza
    if 'new_confidence' in suggestion:
        if not isinstance(suggestion['new_confidence'], int) or suggestion['new_confidence'] < 0 or suggestion['new_confidence'] > 100:
            return False
    
    return True

def calculate_impact_score(suggestion):
    """
    Calcola un punteggio di impatto per la modifica.
    """
    impact_score = 50  # Base score
    
    # Modifica azione = alto impatto
    if suggestion.get('new_action') and suggestion['new_action'] != suggestion.get('old_action', ''):
        impact_score += 30
    
    # Modifica condizione = medio impatto
    if suggestion.get('new_condition') and suggestion['new_condition'] != suggestion.get('old_condition', ''):
        impact_score += 20
    
    # Modifica priorità = basso impatto
    if suggestion.get('new_priority') and suggestion['new_priority'] != suggestion.get('old_priority', 3):
        impact_score += 10
    
    return min(impact_score, 100)

def format_applied_changes(applied_changes):
    """
    Formatta le modifiche applicate per la notifica.
    """
    if not applied_changes:
        return "Nessuna modifica applicata."
    
    formatted = []
    for change in applied_changes:
        formatted.append(f"• Policy #{change['policy_id']} ({change['policy_name']}): {change['changes']}")
    
    return "\n".join(formatted)

def trigger_manual_self_tuning():
    """
    Trigger manuale per l'auto-tuning delle policy.
    """
    try:
        print("[AI Self-Tuning] Trigger manuale avviato...")
        changes = ai_self_tune_policies_job()
        return changes
    except Exception as e:
        print(f"[AI Self-Tuning] Errore trigger manuale: {str(e)}")
        raise 