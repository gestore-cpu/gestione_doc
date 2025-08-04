from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.base import Base

class SuggerimentoAI(Base):
    __tablename__ = "suggerimenti_ai"

    id = Column(Integer, primary_key=True)
    titolo = Column(String(255), nullable=False)
    contenuto = Column(Text, nullable=False)
    categoria = Column(String(100))  # Es: Sicurezza, Lean, Archiviazione, Governance
    creato_il = Column(DateTime(timezone=True), server_default=func.now())
    completato = Column(Boolean, default=False)
    formativo = Column(Boolean, default=False)
    fonte = Column(String(100))  # Es: "Log", "Documento", "Accesso", "Manuale" 