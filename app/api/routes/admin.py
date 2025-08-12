from fastapi import Request, Form, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.mail import send_email  # se esiste
from app.services.focusme import generate_task_from_doc
from app.models.richiesta_sblocco import RichiestaSblocco
from app.models import User
from fastapi import Depends
from sqlalchemy.orm import Session
from app.dependencies import get_current_user, db
from sqlalchemy import func, String
from datetime import datetime
from fastapi.responses import StreamingResponse
import csv
import io
from typing import Optional

templates = Jinja2Templates(directory="templates")

@router.get("/richieste-sblocco")
def richieste_sblocco_admin(request: Request, db: Session = Depends(db), user: User = Depends(get_current_user)):
    if not getattr(user, 'is_admin', False):
        raise HTTPException(403)
    richieste = db.query(RichiestaSblocco).order_by(RichiestaSblocco.timestamp.desc()).all()
    return templates.TemplateResponse("admin/richieste_sblocco.html", {
        "request": request,
        "richieste": richieste
    })

@router.get("/richieste-sblocco/stats")
def dashboard_richieste_sblocco(request: Request, db: Session = Depends(db), user: User = Depends(get_current_user)):
    if not getattr(user, 'is_admin', False):
        raise HTTPException(403)
    totali = db.query(func.count(RichiestaSblocco.id)).scalar()
    per_stato = db.query(RichiestaSblocco.stato, func.count()).group_by(RichiestaSblocco.stato).all()
    per_documento = db.query(RichiestaSblocco.document_id, func.count()).group_by(RichiestaSblocco.document_id).order_by(func.count().desc()).limit(5).all()
    per_utente = db.query(RichiestaSblocco.user_email, func.count()).group_by(RichiestaSblocco.user_email).order_by(func.count().desc()).limit(5).all()
    # Tempo medio risposta (in giorni, tra timestamp e ora, solo per richieste chiuse)
    richieste_chiuse = db.query(RichiestaSblocco).filter(RichiestaSblocco.stato != "in_attesa").all()
    if richieste_chiuse:
        tempo_medio = sum([(datetime.now() - r.timestamp).days for r in richieste_chiuse]) / len(richieste_chiuse)
    else:
        tempo_medio = None
    return templates.TemplateResponse("admin/stats_sblocco.html", {
        "request": request,
        "totali": totali,
        "per_stato": per_stato,
        "per_documento": per_documento,
        "per_utente": per_utente,
        "tempo_medio": round(tempo_medio, 2) if tempo_medio else "N/A"
    })

@router.get("/richieste-sblocco/export")
def export_richieste_sblocco_csv(db: Session = Depends(db), user: User = Depends(get_current_user)):
    if not getattr(user, 'is_admin', False):
        raise HTTPException(403)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Email", "Documento", "Stato", "Motivo", "Risposta", "Data"])
    richieste = db.query(RichiestaSblocco).order_by(RichiestaSblocco.timestamp.desc()).all()
    for r in richieste:
        writer.writerow([
            r.id,
            r.user_email,
            r.document_id,
            r.stato,
            r.motivo,
            r.risposta_admin or "",
            r.timestamp.strftime("%Y-%m-%d %H:%M")
        ])
    output.seek(0)
    filename = f"richieste_sblocco_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})

@router.get("/richieste-sblocco/list")
def lista_richieste_sblocco(
    request: Request,
    stato: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    da: Optional[str] = Query(None),
    a: Optional[str] = Query(None),
    db: Session = Depends(db),
    user: User = Depends(get_current_user)
):
    if not getattr(user, 'is_admin', False):
        raise HTTPException(403)
    query = db.query(RichiestaSblocco)
    if stato:
        query = query.filter(RichiestaSblocco.stato == stato)
    if search:
        search_lower = f"%{search.lower()}%"
        query = query.filter(
            (RichiestaSblocco.user_email.ilike(search_lower)) |
            (func.cast(RichiestaSblocco.document_id, String).ilike(search_lower))
        )
    if da:
        query = query.filter(RichiestaSblocco.timestamp >= datetime.fromisoformat(da))
    if a:
        query = query.filter(RichiestaSblocco.timestamp <= datetime.fromisoformat(a))
    richieste = query.order_by(RichiestaSblocco.timestamp.desc()).all()
    return templates.TemplateResponse("admin/lista_richieste.html", {
        "request": request,
        "richieste": richieste,
        "stato": stato,
        "search": search,
        "da": da,
        "a": a
    })

def notifica_esito_richiesta(richiesta: RichiestaSblocco, db: Session):
    subject = f"Esito richiesta sblocco: {richiesta.document_id}"
    body = f"""
Ciao,

la tua richiesta di accesso al documento ID {richiesta.document_id} è stata **{richiesta.stato.upper()}**.

Motivo del moderatore:
{richiesta.risposta_admin or '(nessuna risposta)'}

Grazie,
Team Documenti
"""
    try:
        send_email(to=richiesta.user_email, subject=subject, body=body)
    except Exception:
        pass
    # Notifica FocusMe AI (opzionale)
    user = db.query(User).filter_by(email=richiesta.user_email).first()
    import asyncio
    asyncio.create_task(generate_task_from_doc({
        "titolo": f"Esito richiesta sblocco – Documento {richiesta.document_id}",
        "descrizione": (
            f"La tua richiesta è stata {richiesta.stato.upper()}.\n"
            f"Risposta dell’amministratore: {richiesta.risposta_admin}"
        ),
        "categoria": "Notifica Utente",
        "documento": richiesta.document_id,
        "origine": "docs.mercurysurgelati.org"
    }, user=user))

@router.post("/richieste-sblocco/{id}/rispondi")
def rispondi_richiesta_sblocco(id: int, azione: str = Form(...), risposta_admin: str = Form(""), db: Session = Depends(db), user: User = Depends(get_current_user)):
    if not getattr(user, 'is_admin', False):
        raise HTTPException(403)
    richiesta = db.query(RichiestaSblocco).get(id)
    if not richiesta:
        raise HTTPException(404)
    richiesta.stato = "approvata" if azione == "approva" else "rifiutata"
    richiesta.risposta_admin = risposta_admin
    db.commit()
    notifica_esito_richiesta(richiesta, db)
    return RedirectResponse("/admin/richieste-sblocco", status_code=303)

@router.get("/le-mie-richieste")
def le_mie_richieste(request: Request, db: Session = Depends(db), user: User = Depends(get_current_user)):
    richieste = db.query(RichiestaSblocco).filter_by(user_email=user.email).order_by(RichiestaSblocco.timestamp.desc()).all()
    return templates.TemplateResponse("user/le_mie_richieste.html", {
        "request": request,
        "richieste": richieste
    }) 