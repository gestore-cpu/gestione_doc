from app.models.ai_analysis import DocumentoAnalizzato
from sqlalchemy.orm import Session

def salva_risultato_analisi(result: dict, db: Session):
    analisi = DocumentoAnalizzato(
        filename=result["filename"],
        uploader_email=result["uploader"],
        summary=result.get("summary"),
        classification=result.get("classification"),
        dates=result.get("dates"),
        signatures=result.get("signatures"),
        lean_check=result.get("lean_check")
    )
    db.add(analisi)
    db.commit()
    db.refresh(analisi)
    return analisi 