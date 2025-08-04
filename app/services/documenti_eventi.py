from typing import List
from sqlalchemy.orm import Session
from app.models.notifiche import NotificaAI
from app.models.ai_analysis import DocumentoAnalizzato
from models import GuestActivity, DocumentActivityLog, DownloadLog, Document

def get_timeline_eventi_documento(documento_id: int, db: Session) -> List[dict]:
    """
    Recupera la timeline completa degli eventi per un documento.
    
    Args:
        documento_id (int): ID del documento.
        db (Session): Sessione database.
        
    Returns:
        List[dict]: Lista di eventi ordinati per timestamp.
    """
    events = []

    # 1. Notifiche AI
    notifiche = db.query(NotificaAI).filter(NotificaAI.documento_id == documento_id).all()
    for n in notifiche:
        events.append({
            "timestamp": n.data_invio,
            "tipo": "notifica_ai",
            "descrizione": n.messaggio,
            "dettagli": f"Canale: {n.canale} | Esito: {n.esito} | Tipo: {n.tipo_evento}"
        })

    # 2. Analisi AI
    analisi = db.query(DocumentoAnalizzato).filter_by(documento_id=documento_id).first()
    if analisi:
        events.append({
            "timestamp": analisi.data_analisi,
            "tipo": "analisi_ai",
            "descrizione": "Analisi AI completata",
            "dettagli": f"Synced: {analisi.synced} | Violazioni Lean: {getattr(analisi, 'violazioni_lean', 0)}"
        })
        if getattr(analisi, "synced", False) and analisi.synced_at:
            events.append({
                "timestamp": analisi.synced_at,
                "tipo": "sync_obeya",
                "descrizione": "Sincronizzazione FocusMe Obeya",
                "dettagli": "Documento sincronizzato con sistema Obeya"
            })

    # 3. Attività guest
    attivita = db.query(GuestActivity).filter_by(document_id=documento_id).all()
    for a in attivita:
        events.append({
            "timestamp": a.timestamp,
            "tipo": "attività_guest",
            "descrizione": f"Attività guest: {a.action}",
            "dettagli": f"Email: {a.guest_email} | User ID: {a.user_id}"
        })

    # 4. Log attività documento
    activity_logs = db.query(DocumentActivityLog).filter_by(document_id=documento_id).all()
    for log in activity_logs:
        events.append({
            "timestamp": log.timestamp,
            "tipo": "attività_documento",
            "descrizione": f"Azione: {log.action}",
            "dettagli": f"Utente: {log.user.username if log.user else 'N/A'} | Note: {log.note or 'N/A'}"
        })

    # 5. Log download
    download_logs = db.query(DownloadLog).filter_by(document_id=documento_id).all()
    for log in download_logs:
        events.append({
            "timestamp": log.timestamp,
            "tipo": "download",
            "descrizione": "Download documento",
            "dettagli": f"Utente: {log.user.username if log.user else 'N/A'}"
        })

    # 6. Creazione documento
    document = db.query(Document).filter_by(id=documento_id).first()
    if document:
        events.append({
            "timestamp": document.created_at,
            "tipo": "creazione",
            "descrizione": "Documento creato",
            "dettagli": f"Uploader: {document.uploader_email} | Visibilità: {document.visibility}"
        })

    # Ordina per timestamp decrescente
    events.sort(key=lambda x: x["timestamp"], reverse=True)
    return events 