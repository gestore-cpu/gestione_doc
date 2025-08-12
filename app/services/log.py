from app.models.log import LogAttivitaDocumento
from app.database import db

def log_attivita_documento(user, document_id, azione, request):
    log = LogAttivitaDocumento(
        user_id=user.id,
        document_id=document_id,
        azione=azione,
        ip=request.client.host,
        user_agent=request.headers.get("user-agent", "")
    )
    db = next(db())
    db.add(log)
    db.commit() 