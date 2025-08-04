"""
Modulo per il tracciamento delle letture dei documenti.
"""

import logging
from datetime import datetime
from flask import current_app, request
from flask_login import current_user
from models import db, DocumentReadLog, Document

logger = logging.getLogger(__name__)


def track_document_read(document, user=None, duration=None):
    """
    Traccia la lettura di un documento.
    
    Args:
        document: Oggetto Document
        user: Utente che ha letto (opzionale, usa current_user se None)
        duration (int): Durata lettura in secondi (opzionale)
        
    Returns:
        DocumentReadLog: Il log di lettura creato
    """
    try:
        if user is None:
            user = current_user
        
        if not user.is_authenticated:
            logger.warning("Tentativo di tracciare lettura da utente non autenticato")
            return None
        
        # Verifica se è la prima lettura
        existing_read = DocumentReadLog.query.filter_by(
            user_id=user.id,
            document_id=document.id
        ).first()
        
        is_first_read = existing_read is None
        
        # Crea il log di lettura
        read_log = DocumentReadLog(
            user_id=user.id,
            document_id=document.id,
            is_first_read=is_first_read,
            read_duration=duration,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )
        
        db.session.add(read_log)
        db.session.commit()
        
        # Log anche nell'audit
        from utils.audit_logger import log_event
        evento = "👁️ Prima lettura" if is_first_read else "👁️ Rilettura"
        log_event(document, evento, user_override=user)
        
        logger.info(f"Lettura tracciata: documento {document.id} da {user.email}")
        return read_log
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore nel tracciamento lettura: {str(e)}")
        return None


def has_user_read_document(user, document):
    """
    Verifica se un utente ha letto un documento.
    
    Args:
        user: Oggetto User
        document: Oggetto Document
        
    Returns:
        bool: True se l'utente ha letto il documento
    """
    if not user.is_authenticated:
        return False
    
    existing_log = DocumentReadLog.query.filter_by(
        document_id=document.id, 
        user_id=user.id
    ).first()
    
    return existing_log is not None


def get_user_read_stats(user):
    """
    Ottiene le statistiche di lettura di un utente.
    
    Args:
        user: Oggetto User
        
    Returns:
        dict: Statistiche di lettura
    """
    try:
        total_reads = DocumentReadLog.query.filter_by(user_id=user.id).count()
        first_reads = DocumentReadLog.query.filter_by(
            user_id=user.id, 
            is_first_read=True
        ).count()
        
        # Documenti non letti
        all_documents = Document.query.count()
        unread_documents = all_documents - total_reads
        
        return {
            'total_reads': total_reads,
            'first_reads': first_reads,
            'unread_documents': unread_documents,
            'read_percentage': round((total_reads / all_documents * 100) if all_documents > 0 else 0, 1)
        }
        
    except Exception as e:
        logger.error(f"Errore nel calcolo statistiche lettura: {str(e)}")
        return {}


def get_document_read_stats(document):
    """
    Ottiene le statistiche di lettura per un documento.
    
    Args:
        document: Oggetto Document
        
    Returns:
        dict: Statistiche di lettura
    """
    total_reads = len(document.read_logs)
    unique_readers = len(set(log.user_id for log in document.read_logs))
    first_reads = len([log for log in document.read_logs if log.is_first_read])
    
    return {
        'total_reads': total_reads,
        'unique_readers': unique_readers,
        'first_reads': first_reads,
        're_reads': total_reads - first_reads
    }


def get_mandatory_documents_not_read(user):
    """
    Ottiene i documenti obbligatori non letti da un utente.
    
    Args:
        user: Oggetto User
        
    Returns:
        list: Lista di documenti obbligatori non letti
    """
    try:
        # Documenti critici (policy, HACCP, GDPR, etc.)
        mandatory_docs = Document.query.filter(
            Document.is_critical == True
        ).all()
        
        unread_mandatory = []
        for doc in mandatory_docs:
            if not has_user_read_document(user, doc):
                unread_mandatory.append(doc)
        
        return unread_mandatory
        
    except Exception as e:
        logger.error(f"Errore nel recupero documenti obbligatori: {str(e)}")
        return []


def get_read_duration_stats(document):
    """
    Ottiene statistiche sulla durata di lettura di un documento.
    
    Args:
        document: Oggetto Document
        
    Returns:
        dict: Statistiche sulla durata
    """
    try:
        reads_with_duration = DocumentReadLog.query.filter(
            DocumentReadLog.document_id == document.id,
            DocumentReadLog.read_duration.isnot(None)
        ).all()
        
        if not reads_with_duration:
            return {
                'avg_duration': 0,
                'min_duration': 0,
                'max_duration': 0,
                'total_reads_with_duration': 0
            }
        
        durations = [r.read_duration for r in reads_with_duration]
        
        return {
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations),
            'total_reads_with_duration': len(durations)
        }
        
    except Exception as e:
        logger.error(f"Errore nel calcolo statistiche durata: {str(e)}")
        return {} 