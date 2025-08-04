from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from datetime import datetime
from app.database import Base

class DocumentoAnalizzato(Base):
    __tablename__ = "documenti_analizzati"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    uploader_email = Column(String(255), nullable=False)
    summary = Column(Text)
    classification = Column(String(100))
    dates = Column(JSON)
    signatures = Column(JSON)
    lean_check = Column(JSON)
    qr_code_url = Column(String, nullable=True)
    synced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow) 