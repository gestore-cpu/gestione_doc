from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class VersioneAnalisiAI(Base):
    __tablename__ = "versioni_analisi_ai"

    id = Column(Integer, primary_key=True)
    documento_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    titolo = Column(String(255))
    descrizione = Column(Text)
    aforisma = Column(String(255))
    autore = Column(String(100))
    generata_da_ai = Column(Boolean, default=True)
    attiva = Column(Boolean, default=False)
    data_creazione = Column(DateTime, default=datetime.utcnow)

    documento = relationship("Document", back_populates="versioni_ai") 