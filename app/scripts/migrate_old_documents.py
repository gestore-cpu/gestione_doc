from app.models.ai_analysis import DocumentoAnalizzato
from app.services.qr_generator import generate_qr_for_document
from sqlalchemy.orm import Session
import os

def retro_generate_qrs(db: Session):
    docs = db.query(DocumentoAnalizzato).all()
    for doc in docs:
        qr_path = f"static/qrcodes/{doc.id}.png"
        if not os.path.exists(qr_path):
            metadata = {
                "area": doc.lean_check.get("area") if doc.lean_check else "Altro",
                "azienda": "Mercury",  # o da campo associato
                "reparti": ["Storico"]
            }
            generate_qr_for_document(doc.id, doc.filename, metadata) 