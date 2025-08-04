from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class FormazioneAssegnata(Base):
    __tablename__ = "formazione_assegnata"

    id = Column(Integer, primary_key=True)
    modulo_id = Column(Integer, ForeignKey("moduli_formativi.id"))
    utente_id = Column(Integer, ForeignKey("utenti.id"))
    stato = Column(String(50), default="assegnato")  # letto, completato, scaduto, ecc.
    data_assegnazione = Column(DateTime(timezone=True), server_default=func.now())
    data_completamento = Column(DateTime(timezone=True), nullable=True) 