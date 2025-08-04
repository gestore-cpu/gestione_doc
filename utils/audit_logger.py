"""
Modulo per il logging automatico degli eventi sui documenti.
"""

import logging
from flask import current_app
from flask_login import current_user
from models import db, DocumentAuditLog

logger = logging.getLogger(__name__)


def log_event(document, evento, note_ai=None, user_override=None):
    """
    Registra un evento di audit per un documento.
    
    Args:
        document: Oggetto Document
        evento (str): Descrizione dell'evento
        note_ai (str, optional): Note aggiuntive generate dall'AI
        user_override: Utente specifico (se diverso da current_user)
        
    Returns:
        DocumentAuditLog: Il log creato
    """
    try:
        # Determina l'utente
        user_id = None
        if user_override:
            user_id = user_override.id if hasattr(user_override, 'id') else user_override
        elif current_user.is_authenticated:
            user_id = current_user.id
        
        # Crea il log
        log = DocumentAuditLog(
            document_id=document.id,
            user_id=user_id,
            evento=evento,
            note_ai=note_ai
        )
        
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"Audit log creato: {evento} per documento {document.id}")
        return log
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore nel logging audit: {str(e)}")
        return None


def log_download_event(document, user=None):
    """
    Registra un evento di download.
    
    Args:
        document: Oggetto Document
        user: Utente che ha scaricato (opzionale)
    """
    user_display = user.email if user else (current_user.email if current_user.is_authenticated else "Sistema")
    evento = f"📥 Download eseguito da {user_display}"
    log_event(document, evento, user_override=user)


def log_upload_event(document, user=None):
    """
    Registra un evento di upload.
    
    Args:
        document: Oggetto Document
        user: Utente che ha caricato (opzionale)
    """
    user_display = user.email if user else (current_user.email if current_user.is_authenticated else "Sistema")
    evento = f"📤 Upload eseguito da {user_display}"
    log_event(document, evento, user_override=user)


def log_approval_event(document, approver, approval_type="admin"):
    """
    Registra un evento di approvazione.
    
    Args:
        document: Oggetto Document
        approver: Utente che ha approvato
        approval_type (str): Tipo di approvazione ("admin", "ceo", "ai")
    """
    tipo_map = {
        "admin": "✅ Approvazione Admin",
        "ceo": "👑 Approvazione CEO", 
        "ai": "🧠 Approvazione AI"
    }
    evento = f"{tipo_map.get(approval_type, 'Approvazione')} da {approver.email}"
    log_event(document, evento, user_override=approver)


def log_signature_event(document, signer):
    """
    Registra un evento di firma.
    
    Args:
        document: Oggetto Document
        signer: Utente che ha firmato
    """
    evento = f"✍️ Firma digitale da {signer.email}"
    log_event(document, evento, user_override=signer)


def log_access_denied_event(document, user=None, reason="Permessi insufficienti"):
    """
    Registra un evento di accesso negato.
    
    Args:
        document: Oggetto Document
        user: Utente che ha tentato l'accesso (opzionale)
        reason (str): Motivo del rifiuto
    """
    user_display = user.email if user else (current_user.email if current_user.is_authenticated else "Sistema")
    evento = f"🚫 Accesso negato a {user_display}"
    note_ai = f"Motivo: {reason}"
    log_event(document, evento, note_ai=note_ai, user_override=user)


def log_modification_event(document, field_name, old_value=None, new_value=None):
    """
    Registra un evento di modifica.
    
    Args:
        document: Oggetto Document
        field_name (str): Nome del campo modificato
        old_value: Valore precedente (opzionale)
        new_value: Nuovo valore (opzionale)
    """
    evento = f"✏️ Modifica campo '{field_name}'"
    note_ai = None
    if old_value is not None and new_value is not None:
        note_ai = f"Da: {old_value} → A: {new_value}"
    log_event(document, evento, note_ai=note_ai)


def log_archive_event(document, archived=True):
    """
    Registra un evento di archiviazione/ripristino.
    
    Args:
        document: Oggetto Document
        archived (bool): True se archiviato, False se ripristinato
    """
    if archived:
        evento = "📦 Documento archiviato"
    else:
        evento = "✅ Documento ripristinato"
    log_event(document, evento)


def log_ai_analysis_event(document, analysis_type, details=None):
    """
    Registra un evento di analisi AI.
    
    Args:
        document: Oggetto Document
        analysis_type (str): Tipo di analisi AI
        details (str): Dettagli dell'analisi
    """
    evento = f"🧠 Analisi AI: {analysis_type}"
    log_event(document, evento, note_ai=details)


def log_guest_access_event(document, guest_email, action="access"):
    """
    Registra un evento di accesso guest.
    
    Args:
        document: Oggetto Document
        guest_email (str): Email dell'ospite
        action (str): Tipo di azione ("access", "download", "denied")
    """
    action_map = {
        "access": "👁️ Accesso ospite",
        "download": "📥 Download ospite", 
        "denied": "🚫 Accesso ospite negato"
    }
    evento = f"{action_map.get(action, 'Azione ospite')} - {guest_email}"
    log_event(document, evento)


def get_document_audit_summary(document):
    """
    Ottiene un riepilogo degli eventi di audit per un documento.
    
    Args:
        document: Oggetto Document
        
    Returns:
        dict: Riepilogo degli eventi
    """
    try:
        logs = document.audit_logs.order_by(DocumentAuditLog.timestamp.desc()).all()
        
        summary = {
            'total_events': len(logs),
            'downloads': len([l for l in logs if 'Download' in l.evento]),
            'uploads': len([l for l in logs if 'Upload' in l.evento]),
            'approvals': len([l for l in logs if 'Approvazione' in l.evento]),
            'signatures': len([l for l in logs if 'Firma' in l.evento]),
            'denied_access': len([l for l in logs if 'negato' in l.evento.lower()]),
            'ai_events': len([l for l in logs if 'AI' in l.evento]),
            'last_activity': logs[0].timestamp if logs else None,
            'unique_users': len(set([l.user_id for l in logs if l.user_id]))
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Errore nel calcolo riepilogo audit: {str(e)}")
        return {}


def generate_ai_notes_for_event(evento, context=None):
    """
    Genera note AI automatiche per eventi specifici.
    
    Args:
        evento (str): Tipo di evento
        context (dict): Contesto aggiuntivo
        
    Returns:
        str: Note AI generate
    """
    if "Download negato" in evento:
        return "L'utente ha tentato il download senza permesso o con scadenza superata."
    elif "Accesso ospite scaduto" in evento:
        return "Accesso negato per ospite: accesso scaduto."
    elif "Approvazione CEO" in evento:
        return "Documento approvato dal CEO - processo di validazione completato."
    elif "Firma digitale" in evento:
        return "Documento firmato digitalmente - validità legale confermata."
    elif "Analisi AI" in evento:
        return "Analisi automatica completata - suggerimenti generati."
    elif "Archiviato" in evento:
        return "Documento archiviato per inattività o obsolescenza."
    else:
        return None 