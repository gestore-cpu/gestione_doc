import os
from datetime import datetime, timedelta
import httpx
from app.models.log import LogAttivitaDocumento

def invia_task_focusme_ai(descrizione, categoria):
    payload = {
        "titolo": "\U0001F512 Alert sicurezza documenti",
        "descrizione": descrizione,
        "categoria": categoria,
        "origine": "docs.mercurysurgelati.org",
        "priorita": "alta"
    }
    headers = {"Authorization": f"Bearer {os.getenv('FOCUSME_API_TOKEN')}", "Content-Type": "application/json"}
    try:
        httpx.post("https://focus.mercurysurgelati.org/api/task", json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"Errore invio alert FocusMe: {e}")

def genera_alert_sicurezza(db):
    eventi = []
    da = datetime.utcnow() - timedelta(days=1)
    logs = db.query(LogAttivitaDocumento).filter(LogAttivitaDocumento.timestamp >= da).all()
    # Download notturni
    for log in logs:
        ora = log.timestamp.hour
        if log.azione == "download" and (0 <= ora <= 6):
            eventi.append({
                "tipo": "download_notturno",
                "user_id": log.user_id,
                "document_id": log.document_id,
                "timestamp": log.timestamp
            })
    # (Altre regole: tentativi falliti, download massivo, accesso non autorizzato)
    # TODO: Estendere con altre regole come richiesto
    for evento in eventi:
        descrizione = (
            f"\u26a0\ufe0f Attività sospetta: {evento['tipo']} da utente {evento['user_id']} "
            f"sul documento {evento['document_id']} alle {evento['timestamp']}"
        )
        invia_task_focusme_ai(descrizione, categoria="Sicurezza") 