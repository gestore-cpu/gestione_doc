import asyncio
from app.models import Document, DocumentoAnalizzato
from app.models.analisi_lean import AnalisiLean
from app.services.pdf_ai import extract_text_from_pdf, generate_summary, classify_document
from app.services.lean_checker import check_lean_principles
from app.services.persistence import salva_risultato_analisi
from app.services.obeya_sync import sync_with_focusme_ai
from app.services.notifiche_ai import invia_notifica_ai
from sqlalchemy.orm import Session
from datetime import datetime
import csv

async def analizza_documenti_non_analizzati(db: Session, from_date=None, to_date=None):
    # Recupera documenti non ancora analizzati AI
    query = db.query(Document).filter(Document.ai_analyzed == False)
    if from_date:
        query = query.filter(Document.created_at >= from_date)
    if to_date:
        query = query.filter(Document.created_at <= to_date)
    documenti = query.all()
    report = []
    for doc in documenti:
        try:
            testo = await extract_text_from_pdf(doc.filepath)
            if not testo:
                await invia_notifica_ai(doc.uploader_email, f"[AI][ERR] Documento ID {doc.id} – errore: Testo mancante o file corrotto", "Errore Analisi AI")
                print(f"[AI][ERR] Documento ID {doc.id} – errore: Testo mancante o file corrotto")
                report.append([doc.id, doc.filename, 'errore testo', ''])
                continue
            summary = generate_summary(testo)
            classification = classify_document(testo)
            lean = check_lean_principles(testo)
            result = {
                "filename": doc.filename,
                "uploader": doc.uploader_email,
                "summary": summary,
                "classification": classification,
                "dates": {},
                "signatures": {},
                "lean_check": lean
            }
            documento_ai = salva_risultato_analisi(result, db)
            await sync_with_focusme_ai(documento_ai)
            if not documento_ai.synced:
                await invia_notifica_ai(doc.uploader_email, f"[AI][SYNC FAIL] Documento ID {doc.id} non sincronizzato con Obeya", "Sync Obeya Fallito")
            doc.ai_analyzed = True
            db.commit()
            print(f"[AI][OK] Documento ID {doc.id} analizzato e sincronizzato")
            report.append([doc.id, doc.filename, 'ok', 'sincronizzato'])
        except Exception as e:
            await invia_notifica_ai(doc.uploader_email, f"[AI][ERR] Documento ID {doc.id} – errore: {e}", "Errore Analisi AI")
            print(f"[AI][ERR] Documento ID {doc.id} – errore: {e}")
            report.append([doc.id, doc.filename, 'errore', str(e)])
    # Salva report CSV
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = f"batch_report_{now}.csv"
    with open(report_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Nome', 'Stato AI', 'Esito Sync'])
        writer.writerows(report)
    print(f"[AI][REPORT] Report batch salvato in {report_path}")
    return report_path 