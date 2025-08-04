from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base

class ReviewMensileAI(Base):
    __tablename__ = "review_ai_mensile"

    id = Column(Integer, primary_key=True)
    mese = Column(String, nullable=False)
    utente_id = Column(Integer, ForeignKey("utenti.id"))
    reparto = Column(String)
    documenti_ignorati = Column(Integer)
    documenti_completati = Column(Integer)
    moduli_ai_completati = Column(Integer)
    moduli_ai_ignorati = Column(Integer)
    nota_ai = Column(String)  # suggerimento o nota personalizzata AI 