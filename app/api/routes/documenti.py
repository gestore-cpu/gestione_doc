from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.services.permissions import filter_documents_for_user
from app.models.ai_analysis import DocumentoAnalizzato
from app.dependencies import get_current_user
from app.models.access_log import AccessLog
from datetime import datetime
from fastapi.responses import FileResponse
import os
from app.services.focusme import generate_task_from_doc

router = APIRouter(prefix="/documenti", tags=["Documenti"])

templates = Jinja2Templates(directory="templates")

def log_tentativo_download(email, document_id):
    os.makedirs("logs", exist_ok=True)
    with open("logs/download_blocked.log", "a") as f:
        from datetime import datetime
        f.write(f"{datetime.now()} - {email} → download bloccato per doc {document_id}\n")

@router.get("/")
def get_documenti_filtrati(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Estrai aziende e reparti dell’utente
    aziende_user = [a.nome for a in getattr(user, 'aziende', [])]
    reparti_user = [r.nome for r in getattr(user, 'reparti', [])]

    # Query base filtrata (DB-agnostica)
    documenti = db.query(DocumentoAnalizzato).all()

    documenti_visibili = []
    for doc in documenti:
        if doc.azienda in aziende_user:
            if isinstance(doc.reparto, list):  # JSON list
                if set(doc.reparto).intersection(reparti_user):
                    documenti_visibili.append(doc)
            elif isinstance(doc.reparto, str):  # singolo reparto o JSON string
                import json
                try:
                    reparti_doc = json.loads(doc.reparto)
                    if isinstance(reparti_doc, list):
                        if set(reparti_doc).intersection(reparti_user):
                            documenti_visibili.append(doc)
                    else:
                        if any(rep in doc.reparto for rep in reparti_user):
                            documenti_visibili.append(doc)
                except Exception:
                    if any(rep in doc.reparto for rep in reparti_user):
                        documenti_visibili.append(doc)

    return {"documenti": [d.filename for d in documenti_visibili]}

@router.get("/{document_id}")
def view_documento(document_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = db.query(DocumentoAnalizzato).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(404, "Documento non trovato")
    # Verifica permessi
    if not getattr(user, 'is_admin', False):
        if doc.azienda not in [a.nome for a in getattr(user, 'aziende', [])]:
            raise HTTPException(403)
        if not set(doc.reparto or []).intersection([r.nome for r in getattr(user, 'reparti', [])]):
            raise HTTPException(403)
    # Log accesso
    access_log = AccessLog(user_email=user.email, document_id=doc.id, timestamp=datetime.utcnow())
    db.add(access_log)
    db.commit()
    # Recupera log accessi se admin/ceo
    access_logs = []
    if getattr(user, 'is_admin', False):
        access_logs = db.query(AccessLog).filter_by(document_id=doc.id).order_by(AccessLog.timestamp.desc()).all()
    return templates.TemplateResponse("documenti/view_pdf.html", {
        "request": request,
        "doc": doc,
        "user": user,
        "access_logs": access_logs
    })

@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    doc = db.query(DocumentoAnalizzato).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    # 🛡️ Controllo permessi
    if not getattr(user, 'is_admin', False):
        if doc.azienda not in [a.nome for a in getattr(user, 'aziende', [])]:
            raise HTTPException(403)
        if not set(doc.reparto or []).intersection([r.nome for r in getattr(user, 'reparti', [])]):
            raise HTTPException(403)

    # ⛔ Controllo scadenza
    if doc.dates:
        for date_str, label in doc.dates.items():
            if "scadenza" in label.lower():
                from datetime import datetime
                try:
                    scadenza = datetime.strptime(date_str, "%Y-%m-%d")
                    if scadenza < datetime.now():
                        log_tentativo_download(user.email, doc.id)
                        raise HTTPException(403, "Documento scaduto, accesso negato")
                except Exception:
                    pass  # data malformata: ignora

    # ✅ Se tutto OK → file
    path = f"/storage/{doc.filename}"
    return FileResponse(path, media_type="application/pdf", filename=doc.filename)

@router.post("/{document_id}/richiedi-sblocco")
async def richiedi_sblocco_documento(
    document_id: int,
    motivo: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    doc = db.query(DocumentoAnalizzato).filter_by(id=document_id).first()
    if not doc:
        raise HTTPException(404, "Documento non trovato")

    payload = {
        "titolo": f"Richiesta sblocco documento: {doc.filename}",
        "descrizione": (
            f"L’utente {user.email} ha richiesto l’accesso al documento scaduto "
            f"[{doc.filename}].\nMotivo dichiarato: {motivo}."
        ),
        "categoria": "Richiesta Accesso",
        "documento": doc.filename,
        "origine": "docs.mercurysurgelati.org"
    }

    await generate_task_from_doc(payload, user)

    return {"status": "ok", "message": "Richiesta inviata. Sarai ricontattato."} 