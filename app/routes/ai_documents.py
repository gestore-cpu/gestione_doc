from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.services.pdf_ai import (
    extract_text_from_pdf,
    generate_summary,
    classify_document,
    extract_dates,
    detect_signatures
)
from app.services.focusme import generate_task_from_doc, send_ceo_suggestion
from app.services.notifications import notify_missing_or_expired
from app.services.persistence import salva_risultato_analisi
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from sqlalchemy.orm import Session
from app.services.lean_check import check_lean_principles
from app.services.obeya_sync import sync_with_focusme_ai

router = APIRouter(prefix="/ai-documents", tags=["AI Document Intelligence"])

@router.post("/analyze")
async def analyze_pdf(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo PDF ammessi")

    try:
        # 🧠 Estrazione testo
        content = await extract_text_from_pdf(file)

        # ✨ Analisi AI
        summary = generate_summary(content)
        classification = classify_document(content)
        dates = extract_dates(content)
        signatures = detect_signatures(content)

        result = {
            "filename": file.filename,
            "summary": summary,
            "classification": classification,
            "dates": dates,
            "signatures": signatures,
            "uploader": user.email,
        }

        documento = salva_risultato_analisi(result, db)

        # 🔄 Sincronizza con Obeya solo se non ancora sincronizzato
        if not documento.synced:
            await sync_with_focusme_ai(documento)
            print(f"[SYNC OBEYA] Documento {documento.id} sincronizzato con successo.")

        # ✅ Task AI su FocusMe
        await generate_task_from_doc(result, user)

        # 🚨 Verifica problemi (scadenze, firme, obsolescenza)
        await notify_missing_or_expired(result)

        await send_ceo_suggestion(result)

        return {"message": "Documento analizzato", "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore durante l’analisi: {e}") 