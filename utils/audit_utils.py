"""
Utility per logging di audit e sicurezza.
Gestisce il log centralizzato di eventi di sicurezza e audit.
"""

import logging
from datetime import datetime
from flask import request, current_app
from flask_login import current_user
from extensions import db
from models import SecurityAuditLog

logger = logging.getLogger(__name__)


def get_client_ip():
    """
    Ottiene l'IP del client dal request.
    
    Returns:
        str: Indirizzo IP del client
    """
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        # Proxy setup - prendi il primo IP
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif request.environ.get('HTTP_X_REAL_IP'):
        return request.environ['HTTP_X_REAL_IP']
    else:
        return request.environ.get('REMOTE_ADDR', 'unknown')


def get_user_agent():
    """
    Ottiene lo User-Agent del client.
    
    Returns:
        str: User-Agent header
    """
    return request.headers.get('User-Agent', 'unknown')[:255]  # Limita a 255 caratteri


def log_audit_event(user_id, action, object_type=None, object_id=None, meta=None):
    """
    Registra un evento di audit nel log di sicurezza.
    
    Args:
        user_id (int): ID dell'utente che ha eseguito l'azione (None per utenti anonimi)
        action (str): Tipo di azione eseguita
        object_type (str, optional): Tipo di oggetto interessato
        object_id (int, optional): ID dell'oggetto interessato
        meta (dict, optional): Metadati aggiuntivi
        
    Returns:
        bool: True se il log è stato salvato con successo
    """
    try:
        audit_log = SecurityAuditLog(
            user_id=user_id,
            ip=get_client_ip(),
            action=action,
            object_type=object_type,
            object_id=object_id,
            meta=meta,
            user_agent=get_user_agent()
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
        logger.info(f"Audit log creato: {action} by user {user_id} on {object_type}:{object_id}")
        
        # === CONTROLLO ALERT DI SICUREZZA ===
        if user_id:  # Solo per utenti autenticati
            try:
                from services.alert_service import alert_service
                alert_service.check_alert_rules(user_id, action, object_id)
            except Exception as e:
                logger.error(f"Errore controllo alert per azione {action}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Errore creazione audit log: {e}")
        db.session.rollback()
        return False


def log_security_event(user_id, action, details, severity='medium', object_type=None, object_id=None):
    """
    Registra un evento di sicurezza specifico.
    
    Args:
        user_id (int): ID dell'utente coinvolto
        action (str): Azione che ha scatenato l'evento
        details (str): Dettagli dell'evento
        severity (str): Livello di severità ('low', 'medium', 'high')
        object_type (str, optional): Tipo di oggetto interessato
        object_id (int, optional): ID dell'oggetto interessato
        
    Returns:
        bool: True se il log è stato salvato con successo
    """
    meta = {
        'severity': severity,
        'details': details,
        'event_type': 'security'
    }
    
    if object_type:
        meta['object_type'] = object_type
    if object_id:
        meta['object_id'] = object_id
    
    return log_audit_event(user_id, f"security_{action}", object_type, object_id, meta)


def log_file_access(user_id, file_id, action, success=True, reason=None):
    """
    Registra un accesso a un file.
    
    Args:
        user_id (int): ID dell'utente
        file_id (int): ID del file
        action (str): Tipo di accesso ('view', 'download', 'upload', 'delete')
        success (bool): Se l'accesso è stato autorizzato
        reason (str, optional): Motivo del blocco (se success=False)
        
    Returns:
        bool: True se il log è stato salvato con successo
    """
    action_name = f"file_{action}_{'success' if success else 'denied'}"
    
    meta = {
        'success': success,
        'action_type': action
    }
    
    if not success and reason:
        meta['denial_reason'] = reason
    
    return log_audit_event(user_id, action_name, 'file', file_id, meta)


def log_authentication_event(user_id, action, success=True, details=None):
    """
    Registra un evento di autenticazione.
    
    Args:
        user_id (int): ID dell'utente (None per tentativi falliti)
        action (str): Tipo di autenticazione ('login', 'logout', 'password_change')
        success (bool): Se l'autenticazione è riuscita
        details (str, optional): Dettagli aggiuntivi
        
    Returns:
        bool: True se il log è stato salvato con successo
    """
    action_name = f"auth_{action}_{'success' if success else 'failed'}"
    
    meta = {
        'success': success,
        'auth_type': action
    }
    
    if details:
        meta['details'] = details
    
    return log_audit_event(user_id, action_name, 'user', user_id, meta)


def log_admin_action(admin_user_id, action, target_user_id=None, details=None):
    """
    Registra un'azione amministrativa.
    
    Args:
        admin_user_id (int): ID dell'amministratore
        action (str): Azione eseguita
        target_user_id (int, optional): ID dell'utente target
        details (str, optional): Dettagli dell'azione
        
    Returns:
        bool: True se il log è stato salvato con successo
    """
    meta = {
        'admin_action': True,
        'action_type': action
    }
    
    if target_user_id:
        meta['target_user_id'] = target_user_id
    if details:
        meta['details'] = details
    
    return log_audit_event(admin_user_id, f"admin_{action}", 'user', target_user_id, meta)


def get_audit_logs(action_filter=None, user_id_filter=None, object_type_filter=None, 
                   start_date=None, end_date=None, limit=100, offset=0):
    """
    Recupera i log di audit con filtri opzionali.
    
    Args:
        action_filter (list, optional): Lista di azioni da includere
        user_id_filter (int, optional): Filtra per ID utente
        object_type_filter (str, optional): Filtra per tipo di oggetto
        start_date (datetime, optional): Data di inizio
        end_date (datetime, optional): Data di fine
        limit (int): Numero massimo di risultati
        offset (int): Offset per paginazione
        
    Returns:
        list: Lista di record SecurityAuditLog
    """
    try:
        query = SecurityAuditLog.query
        
        if action_filter:
            query = query.filter(SecurityAuditLog.action.in_(action_filter))
        
        if user_id_filter:
            query = query.filter(SecurityAuditLog.user_id == user_id_filter)
        
        if object_type_filter:
            query = query.filter(SecurityAuditLog.object_type == object_type_filter)
        
        if start_date:
            query = query.filter(SecurityAuditLog.ts >= start_date)
        
        if end_date:
            query = query.filter(SecurityAuditLog.ts <= end_date)
        
        return query.order_by(SecurityAuditLog.ts.desc())\
                   .offset(offset)\
                   .limit(limit)\
                   .all()
        
    except Exception as e:
        logger.error(f"Errore recupero audit logs: {e}")
        return []


def get_user_activity_summary(user_id, days=30):
    """
    Ottiene un riassunto dell'attività di un utente.
    
    Args:
        user_id (int): ID dell'utente
        days (int): Numero di giorni da considerare
        
    Returns:
        dict: Riassunto attività con contatori per tipo di azione
    """
    try:
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        logs = get_audit_logs(
            user_id_filter=user_id,
            start_date=start_date,
            limit=1000  # Limite alto per il riassunto
        )
        
        activity_summary = {}
        for log in logs:
            action = log.action
            if action not in activity_summary:
                activity_summary[action] = 0
            activity_summary[action] += 1
        
        return {
            'user_id': user_id,
            'period_days': days,
            'total_actions': len(logs),
            'actions_breakdown': activity_summary,
            'first_activity': logs[-1].ts.isoformat() if logs else None,
            'last_activity': logs[0].ts.isoformat() if logs else None
        }
        
    except Exception as e:
        logger.error(f"Errore riassunto attività utente {user_id}: {e}")
        return {
            'user_id': user_id,
            'period_days': days,
            'total_actions': 0,
            'actions_breakdown': {},
            'first_activity': None,
            'last_activity': None,
            'error': str(e)
        }
