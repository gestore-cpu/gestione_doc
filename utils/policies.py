"""
Utility per la gestione delle policy automatiche di accesso ai documenti.
"""

import json
from datetime import datetime
from models import AutoPolicy, AccessRequest, AuthorizedAccess
from utils.logging import log_audit_event
from utils.mail import send_access_request_notifications

def match_policy(policy, user, document, note=""):
    """
    Controlla se la policy corrisponde ai dati dell'utente e del documento.
    
    Args:
        policy: Oggetto AutoPolicy da valutare
        user: Oggetto User che fa la richiesta
        document: Oggetto Document richiesto
        note: Nota opzionale della richiesta
        
    Returns:
        bool: True se la policy corrisponde, False altrimenti
    """
    try:
        if policy.condition_type == 'json':
            return _match_json_policy(policy, user, document, note)
        else:
            return _match_natural_policy(policy, user, document, note)
    except Exception as e:
        print(f"Errore valutazione policy {policy.id}: {e}")
        return False

def _match_json_policy(policy, user, document, note):
    """
    Valuta policy con condizione in formato JSON.
    """
    try:
        condition_data = json.loads(policy.condition)
        
        # Prepara dati per valutazione
        request_data = {
            'user_role': user.role,
            'user_company': document.company.name if document.company else "",
            'user_department': document.department.name if document.department else "",
            'document_company': document.company.name if document.company else "",
            'document_department': document.department.name if document.department else "",
            'document_name': document.title or document.original_filename,
            'document_tags': [tag.name for tag in document.tags] if hasattr(document, 'tags') and document.tags else [],
            'note': note
        }
        
        # Usa il metodo di valutazione del modello AutoPolicy
        return policy.evaluate_condition(request_data)
        
    except (json.JSONDecodeError, KeyError, AttributeError) as e:
        print(f"Errore parsing condizione JSON policy {policy.id}: {e}")
        return False

def _match_natural_policy(policy, user, document, note):
    """
    Valuta policy con condizione in linguaggio naturale.
    """
    condition_lower = policy.condition.lower()
    
    # Condizioni predefinite
    if "admin" in condition_lower and "user_role" in condition_lower:
        return user.role == 'admin'
    
    if "same company" in condition_lower or "stessa azienda" in condition_lower:
        user_company = document.company.name if document.company else ""
        doc_company = document.company.name if document.company else ""
        return user_company == doc_company and user_company != ""
    
    if "same department" in condition_lower or "stesso reparto" in condition_lower:
        user_dept = document.department.name if document.department else ""
        doc_dept = document.department.name if document.department else ""
        return user_dept == doc_dept and user_dept != ""
    
    if "confidential" in condition_lower or "confidenziale" in condition_lower:
        doc_tags = [tag.name.lower() for tag in document.tags] if hasattr(document, 'tags') and document.tags else []
        return 'confidenziale' in doc_tags or 'riservato' in doc_tags
    
    if "guest" in condition_lower and "deny" in condition_lower:
        return user.role == 'guest'
    
    return False

def apply_auto_policies(user, document, note=""):
    """
    Applica tutte le policy attive a una richiesta di accesso.
    
    Args:
        user: Oggetto User che fa la richiesta
        document: Oggetto Document richiesto
        note: Nota opzionale della richiesta
        
    Returns:
        dict: Risultato dell'applicazione delle policy
    """
    try:
        # Recupera tutte le policy attive ordinate per priorità
        active_policies = AutoPolicy.query.filter_by(active=True).order_by(AutoPolicy.priority.asc()).all()
        
        for policy in active_policies:
            if match_policy(policy, user, document, note):
                return {
                    'applied': True,
                    'action': policy.action,
                    'policy_id': policy.id,
                    'policy_name': policy.name,
                    'reason': f'Regola automatica: {policy.name}'
                }
        
        # Nessuna policy corrisponde
        return {
            'applied': False,
            'reason': 'Nessuna regola automatica corrisponde'
        }
        
    except Exception as e:
        print(f"Errore applicazione policy automatiche: {e}")
        return {
            'applied': False,
            'reason': f'Errore applicazione policy: {str(e)}'
        }

def process_access_request_with_policies(user, document, note=""):
    """
    Processa una richiesta di accesso applicando le policy automatiche.
    
    Args:
        user: Oggetto User che fa la richiesta
        document: Oggetto Document richiesto
        note: Nota opzionale della richiesta
        
    Returns:
        dict: Risultato del processing con dettagli
    """
    from models import AccessRequest, AuthorizedAccess
    from extensions import db
    
    try:
        # Controlla se esiste già una richiesta pendente
        existing_request = AccessRequest.query.filter_by(
            user_id=user.id,
            document_id=document.id,
            status='pending'
        ).first()
        
        if existing_request:
            return {
                'success': False,
                'error': 'Richiesta già pendente per questo documento',
                'request_id': existing_request.id
            }
        
        # Crea la richiesta iniziale
        access_request = AccessRequest(
            user_id=user.id,
            document_id=document.id,
            note=note,
            status='pending'
        )
        
        db.session.add(access_request)
        db.session.flush()  # Per avere l'ID subito
        
        # Applica policy automatiche
        policy_result = apply_auto_policies(user, document, note)
        
        if policy_result['applied']:
            # Decisione automatica
            access_request.status = policy_result['action']
            access_request.risposta_ai = policy_result['reason']
            access_request.resolved_at = datetime.utcnow()
            
            # Se approvata, crea accesso autorizzato
            if policy_result['action'] == 'approve':
                authorized_access = AuthorizedAccess(
                    user_id=user.id,
                    document_id=document.id,
                    granted_at=datetime.utcnow(),
                    granted_by=None,  # Sistema automatico
                    reason=f"Auto-approvato: {policy_result['policy_name']}"
                )
                db.session.add(authorized_access)
            
            # Log audit
            log_audit_event(
                action=f"request_auto_{policy_result['action']}",
                details=f"Richiesta {access_request.id} {policy_result['action']} tramite policy {policy_result['policy_id']}",
                user_id=user.id,
                extra_info={
                    'policy_id': policy_result['policy_id'],
                    'policy_name': policy_result['policy_name'],
                    'document_id': document.id,
                    'auto_decision': True
                }
            )
            
            # Notifica email
            send_access_request_notifications(
                event=policy_result['action'],
                access_request=access_request,
                auto_policy=policy_result['policy_name']
            )
            
            db.session.commit()
            
            return {
                'success': True,
                'auto_decision': True,
                'action': policy_result['action'],
                'policy_name': policy_result['policy_name'],
                'request_id': access_request.id,
                'message': f'Richiesta {policy_result["action"]} automaticamente'
            }
        
        else:
            # Nessuna policy corrisponde, richiesta rimane pending
            db.session.commit()
            
            # Log audit
            log_audit_event(
                action="request_created",
                details=f"Richiesta {access_request.id} creata in attesa di approvazione",
                user_id=user.id,
                extra_info={
                    'document_id': document.id,
                    'auto_decision': False
                }
            )
            
            # Notifica email standard
            send_access_request_notifications(
                event="new_request",
                access_request=access_request
            )
            
            return {
                'success': True,
                'auto_decision': False,
                'action': 'pending',
                'request_id': access_request.id,
                'message': 'Richiesta inviata con successo'
            }
            
    except Exception as e:
        db.session.rollback()
        print(f"Errore processing richiesta accesso: {e}")
        return {
            'success': False,
            'error': f'Errore creazione richiesta: {str(e)}'
        }

def get_policy_statistics():
    """
    Restituisce statistiche sulle policy automatiche.
    
    Returns:
        dict: Statistiche delle policy
    """
    try:
        total_policies = AutoPolicy.query.count()
        active_policies = AutoPolicy.query.filter_by(active=True).count()
        pending_policies = AutoPolicy.query.filter_by(active=False).count()
        
        # Conta decisioni automatiche recenti
        from datetime import datetime, timedelta
        recent_date = datetime.utcnow() - timedelta(days=30)
        
        auto_approved = AccessRequest.query.filter(
            AccessRequest.status == 'approved',
            AccessRequest.risposta_ai.like('Regola automatica:%'),
            AccessRequest.resolved_at >= recent_date
        ).count()
        
        auto_denied = AccessRequest.query.filter(
            AccessRequest.status == 'denied',
            AccessRequest.risposta_ai.like('Regola automatica:%'),
            AccessRequest.resolved_at >= recent_date
        ).count()
        
        return {
            'total_policies': total_policies,
            'active_policies': active_policies,
            'pending_policies': pending_policies,
            'auto_approved_30d': auto_approved,
            'auto_denied_30d': auto_denied,
            'auto_total_30d': auto_approved + auto_denied
        }
        
    except Exception as e:
        print(f"Errore calcolo statistiche policy: {e}")
        return {
            'total_policies': 0,
            'active_policies': 0,
            'pending_policies': 0,
            'auto_approved_30d': 0,
            'auto_denied_30d': 0,
            'auto_total_30d': 0
        } 