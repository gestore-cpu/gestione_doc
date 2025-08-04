from fastapi import APIRouter, Request, Depends, Form, Query, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from app.dependencies import is_superadmin, get_db
from app.models.ai_analysis import DocumentoAnalizzato
from app.models.analisi_lean import AnalisiLean
from app.models.notifiche import NotificaAI, BulkNotificheModel
import io
import csv
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from scripts.analisi_batch import analizza_documenti_non_analizzati
from datetime import datetime, timedelta
from fastapi import Body
from app.services.documenti_eventi import get_timeline_eventi_documento
from models import Document
from app.models.analisi_ai_version import VersioneAnalisiAI
from pydantic import BaseModel, Field
from sqlalchemy import and_
from app.services.export_service import ExportService

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/ceo/dashboard", response_class=HTMLResponse)
async def ceo_dashboard(request: Request, user = Depends(is_superadmin), db: Session = Depends(get_db)):
    documenti = db.query(DocumentoAnalizzato).order_by(DocumentoAnalizzato.created_at.desc()).limit(50).all()
    non_sync = db.query(DocumentoAnalizzato).filter_by(synced=False).count()
    lean_issues = db.query(AnalisiLean).filter(AnalisiLean.violazione == True).count()
    # Statistiche notifiche AI (ultima settimana)
    week_ago = datetime.utcnow() - timedelta(days=7)
    tot = db.query(NotificaAI).filter(NotificaAI.data_invio >= week_ago).count()
    err = db.query(NotificaAI).filter(NotificaAI.data_invio >= week_ago, NotificaAI.esito.like('%errore%')).count()
    sync_fail = db.query(NotificaAI).filter(NotificaAI.data_invio >= week_ago, NotificaAI.tipo_evento == 'sync_fallito').count()
    lean_viol = db.query(NotificaAI).filter(NotificaAI.data_invio >= week_ago, NotificaAI.tipo_evento == 'violazione_lean').count()
    stats = {
        "tot": tot,
        "err": err,
        "err_pct": int((err/tot)*100) if tot else 0,
        "sync_fail": sync_fail,
        "sync_pct": int((sync_fail/tot)*100) if tot else 0,
        "lean_viol": lean_viol
    }
    return templates.TemplateResponse("dashboard/ceo_dashboard.html", {
        "request": request,
        "documenti": documenti,
        "non_sync": non_sync,
        "lean_issues": lean_issues,
        "stats": stats,
    })

@router.post("/ceo/analisi-retroattiva")
async def trigger_batch(user = Depends(is_superadmin), db: Session = Depends(get_db), from_date: str = Form(None), to_date: str = Form(None)):
    report_path = await analizza_documenti_non_analizzati(db, from_date, to_date)
    return {"status": "ok", "msg": "Analisi batch completata", "csv": report_path}

@router.get("/ceo/notifiche", response_class=HTMLResponse)
async def notifiche_ceo(request: Request, user=Depends(is_superadmin), db: Session = Depends(get_db), start: str = Query(None), end: str = Query(None), canale: str = Query(None)):
    q = db.query(NotificaAI)
    if start:
        q = q.filter(NotificaAI.data_invio >= datetime.strptime(start, "%Y-%m-%d"))
    if end:
        q = q.filter(NotificaAI.data_invio < datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1))
    if canale:
        q = q.filter(NotificaAI.canale == canale)
    notifiche = q.order_by(NotificaAI.data_invio.desc()).limit(100).all()
    return templates.TemplateResponse("dashboard/notifiche_ceo.html", {
        "request": request,
        "notifiche": notifiche,
    })

@router.get("/ceo/notifiche/export", response_class=StreamingResponse)
async def esporta_notifiche_csv(user=Depends(is_superadmin), db: Session = Depends(get_db), start: str = Query(None), end: str = Query(None), canale: str = Query(None)):
    q = db.query(NotificaAI)
    if start:
        q = q.filter(NotificaAI.data_invio >= datetime.strptime(start, "%Y-%m-%d"))
    if end:
        q = q.filter(NotificaAI.data_invio < datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1))
    if canale:
        q = q.filter(NotificaAI.canale == canale)
    notifiche = q.order_by(NotificaAI.data_invio.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Utente", "Messaggio", "Canale", "Data"])
    for n in notifiche:
        writer.writerow([n.id, n.utente_email, n.messaggio, n.canale, n.data_invio.strftime('%Y-%m-%d %H:%M')])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=notifiche_ai.csv"
    })

@router.patch("/ceo/notifiche/{id}/letta")
async def segna_notifica_letta(id: int, user=Depends(is_superadmin), db: Session = Depends(get_db)):
    notifica = db.query(NotificaAI).filter_by(id=id).first()
    if not notifica:
        raise HTTPException(404)
    notifica.letta = True
    db.commit()
    return {"ok": True}

@router.patch("/ceo/notifiche/bulk")
async def azioni_bulk_notifiche(bulk: BulkNotificheModel = Body(...), user=Depends(is_superadmin), db: Session = Depends(get_db)):
    """Esegue azioni bulk sulle notifiche AI (segna lette, elimina, archivia)."""
    results = {"updated": 0, "deleted": 0, "archived": 0}
    for id in bulk.ids:
        notifica = db.query(NotificaAI).filter_by(id=id).first()
        if not notifica:
            continue
        if bulk.azione == "segna_lette":
            notifica.letta = True
            results["updated"] += 1
        elif bulk.azione == "elimina":
            db.delete(notifica)
            results["deleted"] += 1
        elif bulk.azione == "archivia":
            if hasattr(notifica, "archiviata"):
                notifica.archiviata = True
                results["archived"] += 1
    db.commit()
    return {"ok": True, **results}

@router.post("/ceo/notifiche/bulk")
async def bulk_azioni_notifiche(
    request: Request,
    user=Depends(is_superadmin),
    db: Session = Depends(get_db)
):
    data = await request.json()
    action = data.get("action")
    ids = data.get("ids", [])
    tipo = data.get("tipo")
    if not getattr(user, "is_ceo", False):
        raise HTTPException(403, detail="Solo CEO autorizzato")
    notifiche = db.query(NotificaAI).filter(NotificaAI.id.in_(ids)).all() if ids else []
    if action == "mark_read":
        for n in notifiche:
            n.letta = True
        db.commit()
        return {"success": True, "updated": len(notifiche)}
    elif action == "delete":
        for n in notifiche:
            db.delete(n)
        db.commit()
        return {"success": True, "deleted": len(notifiche)}
    elif action == "block_type" and tipo:
        from app.models.notifiche import NotificheBloccate
        exists = db.query(NotificheBloccate).filter_by(utente_id=user.id, tipo_evento=tipo).first()
        if not exists:
            block = NotificheBloccate(utente_id=user.id, tipo_evento=tipo)
            db.add(block)
            db.commit()
            return {"success": True, "updated": 1}
        return {"success": True, "updated": 0}
    else:
        raise HTTPException(400, detail="Azione o parametri non validi")

@router.delete("/ceo/notifiche/old")
async def cancella_vecchie_notifiche(user=Depends(is_superadmin), db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=30)
    db.query(NotificaAI).filter(NotificaAI.timestamp < cutoff).delete()
    db.commit()
    return {"ok": True}

@router.get("/ceo/documenti/{id}", response_class=HTMLResponse)
async def dettaglio_documento(id: int, request: Request, db: Session = Depends(get_db), user=Depends(is_superadmin)):
    document = db.query(Document).get(id)
    if not document:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    
    # Recupera versione AI attiva
    versione_ai_attiva = db.query(VersioneAnalisiAI).filter_by(
        documento_id=id, 
        attiva=True
    ).first()
    
    # Recupera uploader
    uploader = db.query(User).filter_by(id=document.user_id).first()
    
    return templates.TemplateResponse("dashboard/dettaglio_documento.html", {
        "request": request,
        "document": document,
        "versione_ai_attiva": versione_ai_attiva,
        "uploader": uploader,
        "company": document.company,
        "department": document.department
    })

@router.patch("/ceo/analisi_ai_versioni/{id}/attiva", response_class=JSONResponse)
async def attiva_versione_ai(id: int, db: Session = Depends(get_db), user=Depends(is_superadmin)):
    v = db.query(VersioneAnalisiAI).get(id)
    if not v:
        return JSONResponse(content={"error": "Versione non trovata"}, status_code=404)
    # Disattiva tutte le altre versioni per lo stesso documento
    db.query(VersioneAnalisiAI).filter(and_(VersioneAnalisiAI.documento_id == v.documento_id, VersioneAnalisiAI.id != v.id)).update({VersioneAnalisiAI.attiva: False})
    v.attiva = True
    db.commit()
    return {"success": True}

@router.delete("/ceo/analisi_ai_versioni/{id}", response_class=JSONResponse)
async def elimina_versione_ai(id: int, db: Session = Depends(get_db), user=Depends(is_superadmin)):
    v = db.query(VersioneAnalisiAI).get(id)
    if not v:
        return JSONResponse(content={"error": "Versione non trovata"}, status_code=404)
    db.delete(v)
    db.commit()
    return {"success": True}

@router.get("/ceo/documenti/{id}/timeline", response_class=JSONResponse)
async def timeline_documento_json(id: int, db: Session = Depends(get_db), user=Depends(is_superadmin)):
    eventi = get_timeline_eventi_documento(id, db)
    # Serializza i datetime in stringa ISO
    for e in eventi:
        if hasattr(e["timestamp"], "isoformat"):
            e["timestamp"] = e["timestamp"].isoformat()
    return JSONResponse(content=eventi)

@router.get("/ceo/documenti/{id}/analisi_ai_versioni", response_class=JSONResponse)
async def versioni_analisi_ai_json(id: int, db: Session = Depends(get_db), user=Depends(is_superadmin)):
    versioni = db.query(VersioneAnalisiAI).filter_by(documento_id=id).order_by(VersioneAnalisiAI.data_creazione.desc()).all()
    out = []
    for v in versioni:
        out.append({
            "id": v.id,
            "data_creazione": v.data_creazione.isoformat() if v.data_creazione else None,
            "titolo": v.titolo,
            "descrizione": v.descrizione,
            "aforisma": v.aforisma,
            "autore": v.autore,
            "attiva": v.attiva,
            "generata_da_ai": v.generata_da_ai
        })
    return JSONResponse(content=out)

class VersioneAnalisiAICreate(BaseModel):
    titolo: str = Field(..., min_length=3)
    descrizione: str = Field(..., min_length=5)
    aforisma: str = None
    autore: str = None
    generata_da_ai: bool = True
    attiva: bool = False

@router.post("/ceo/documenti/{id}/analisi_ai_versioni", response_class=JSONResponse, status_code=status.HTTP_201_CREATED)
async def crea_versione_analisi_ai(
    id: int,
    db: Session = Depends(get_db),
    user=Depends(is_superadmin),
    payload: VersioneAnalisiAICreate = Body(...)
):
    from app.models.analisi_ai_version import VersioneAnalisiAI
    v = VersioneAnalisiAI(
        documento_id=id,
        titolo=payload.titolo,
        descrizione=payload.descrizione,
        aforisma=payload.aforisma,
        autore=payload.autore,
        generata_da_ai=payload.generata_da_ai,
        attiva=payload.attiva
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return {
        "id": v.id,
        "data_creazione": v.data_creazione.isoformat() if v.data_creazione else None,
        "titolo": v.titolo,
        "descrizione": v.descrizione,
        "aforisma": v.aforisma,
        "autore": v.autore,
        "attiva": v.attiva,
        "generata_da_ai": v.generata_da_ai
    }

class VersioneAnalisiAIUpdate(BaseModel):
    titolo: str = Field(..., min_length=3)
    descrizione: str = Field(..., min_length=5)
    aforisma: str = None
    autore: str = None

@router.patch("/ceo/analisi_ai_versioni/{id}", response_class=JSONResponse)
async def modifica_versione_ai(
    id: int,
    db: Session = Depends(get_db),
    user=Depends(is_superadmin),
    payload: VersioneAnalisiAIUpdate = Body(...)
):
    v = db.query(VersioneAnalisiAI).get(id)
    if not v:
        return JSONResponse(content={"error": "Versione non trovata"}, status_code=404)
    v.titolo = payload.titolo
    v.descrizione = payload.descrizione
    v.aforisma = payload.aforisma
    v.autore = payload.autore
    db.commit()
    return {"success": True}

# === ROUTE ESPORTAZIONE INTELLIGENTE ===

@router.get("/ceo/documenti/{id}/export/pdf")
async def esporta_documento_pdf(
    id: int, 
    db: Session = Depends(get_db), 
    user=Depends(is_superadmin),
    include_versions: bool = Query(False, description="Includi tutte le versioni AI")
):
    """
    Esporta il documento in formato PDF con metadati, timeline e versioni AI.
    
    Args:
        id (int): ID del documento.
        include_versions (bool): Se includere tutte le versioni AI.
        
    Returns:
        StreamingResponse: PDF del documento.
    """
    try:
        export_service = ExportService(db)
        pdf_bytes = export_service.generate_pdf(id, include_versions=include_versions)
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=documento_{id}_analisi.pdf"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella generazione PDF: {str(e)}")

@router.get("/ceo/documenti/{id}/export/csv")
async def esporta_documento_csv(
    id: int, 
    db: Session = Depends(get_db), 
    user=Depends(is_superadmin)
):
    """
    Esporta il documento in formato CSV per audit.
    
    Args:
        id (int): ID del documento.
        
    Returns:
        StreamingResponse: CSV del documento.
    """
    try:
        export_service = ExportService(db)
        return export_service.generate_csv(id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nella generazione CSV: {str(e)}") 