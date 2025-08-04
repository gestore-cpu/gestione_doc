from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.database import Base

class RichiestaSblocco(Base):
    __tablename__ = "richieste_sblocco"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documenti_analizzati.id"))
    user_email = Column(String, nullable=False)
    motivo = Column(Text, nullable=False)
    stato = Column(String, default="in_attesa")  # in_attesa, approvata, rifiutata
    risposta_admin = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow) 