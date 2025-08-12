#!/usr/bin/env python3
"""
Utility per il logging degli eventi di richieste di accesso.
"""

import json
from datetime import datetime
from extensions import db
from models import AuditLog


def log_access_request_event(event_type, file_id, user_id, admin_id=None, extra_data=None):
    """
    Registra un evento di richiesta di accesso nei log di audit.
    
    Args:
        event_type (str): Tipo di evento ('request_created', 'request_approved', 'request_denied')
        file_id (int): ID del file richiesto
        user_id (int): ID dell'utente che ha fatto la richiesta
        admin_id (int, optional): ID dell'admin che ha gestito la richiesta
        extra_data (dict, optional): Dati aggiuntivi (es. motivazione diniego)
    """
    try:
        # Crea il log di audit
        log = AuditLog(
            user_id=user_id,
            document_id=file_id,
            azione=event_type,
            note=json.dumps(extra_data) if extra_data else None
        )
        
        # Aggiungi al database
        db.session.add(log)
        db.session.commit()
        
        print(f"✅ Log audit registrato: {event_type} per file {file_id} da utente {user_id}")
        
    except Exception as e:
        print(f"❌ Errore durante il logging audit: {str(e)}")
        db.session.rollback()
        raise


def log_request_created(file_id, user_id, reason=None):
    """
    Registra la creazione di una richiesta di accesso.
    
    Args:
        file_id (int): ID del file richiesto
        user_id (int): ID dell'utente che ha fatto la richiesta
        reason (str, optional): Motivazione della richiesta
    """
    extra_data = {'reason': reason} if reason else None
    log_access_request_event('request_created', file_id, user_id, extra_data=extra_data)


def log_request_approved(file_id, user_id, admin_id, response_message=None):
    """
    Registra l'approvazione di una richiesta di accesso.
    
    Args:
        file_id (int): ID del file richiesto
        user_id (int): ID dell'utente che ha fatto la richiesta
        admin_id (int): ID dell'admin che ha approvato
        response_message (str, optional): Messaggio di risposta
    """
    extra_data = {
        'admin_id': admin_id,
        'response_message': response_message,
        'action': 'approved'
    }
    log_access_request_event('request_approved', file_id, user_id, admin_id, extra_data)


def log_request_denied(file_id, user_id, admin_id, response_message=None):
    """
    Registra il diniego di una richiesta di accesso.
    
    Args:
        file_id (int): ID del file richiesto
        user_id (int): ID dell'utente che ha fatto la richiesta
        admin_id (int): ID dell'admin che ha negato
        response_message (str): Motivazione del diniego
    """
    extra_data = {
        'admin_id': admin_id,
        'response_message': response_message,
        'action': 'denied'
    }
    log_access_request_event('request_denied', file_id, user_id, admin_id, extra_data)


def get_access_request_logs(limit=100):
    """
    Recupera i log delle richieste di accesso.
    
    Args:
        limit (int): Numero massimo di log da recuperare
        
    Returns:
        list: Lista dei log di richieste di accesso
    """
    try:
        logs = AuditLog.query.filter(
            AuditLog.azione.in_(['request_created', 'request_approved', 'request_denied'])
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        return logs
        
    except Exception as e:
        print(f"❌ Errore durante il recupero dei log: {str(e)}")
        return []


def get_access_request_stats():
    """
    Recupera statistiche sui log delle richieste di accesso.
    
    Returns:
        dict: Statistiche sui log
    """
    try:
        total_requests = AuditLog.query.filter(
            AuditLog.azione == 'request_created'
        ).count()
        
        approved_requests = AuditLog.query.filter(
            AuditLog.azione == 'request_approved'
        ).count()
        
        denied_requests = AuditLog.query.filter(
            AuditLog.azione == 'request_denied'
        ).count()
        
        return {
            'total_requests': total_requests,
            'approved_requests': approved_requests,
            'denied_requests': denied_requests,
            'approval_rate': (approved_requests / total_requests * 100) if total_requests > 0 else 0
        }
        
    except Exception as e:
        print(f"❌ Errore durante il calcolo delle statistiche: {str(e)}")
        return {
            'total_requests': 0,
            'approved_requests': 0,
            'denied_requests': 0,
            'approval_rate': 0
        } 