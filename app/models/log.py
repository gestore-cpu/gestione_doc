from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base

class LogAttivitaDocumento(Base):
    __tablename__ = "log_attivita_documenti"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("utenti.id"))
    document_id = Column(String)
    azione = Column(String)  # "upload", "download", "richiesta_sblocco", "accesso_negato", ...
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip = Column(String)
    user_agent = Column(String) 