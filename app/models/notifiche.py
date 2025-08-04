from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from datetime import datetime
from app.database import Base
from pydantic import BaseModel
from typing import List, Literal

class NotificaCritica(Base):
    __tablename__ = "notifiche_critiche"
    id = Column(Integer, primary_key=True)
    tipo = Column(String)  # es: "errore_ai", "sync_fail", "violazione_lean"
    messaggio = Column(Text)
    documento_id = Column(Integer, ForeignKey("documenti_analizzati.id"))
    visualizzata = Column(Boolean, default=False)
    data_creazione = Column(DateTime, default=datetime.utcnow) 

class NotificaAI(Base):
    __tablename__ = "notifiche_ai"

    id = Column(Integer, primary_key=True)
    utente_email = Column(String(255))
    messaggio = Column(Text)
    oggetto = Column(String(255))
    tipo_evento = Column(String(100))  # es: 'violazione_lean', 'sync_fallito'
    canale = Column(String(50))        # email, whatsapp, entrambi
    esito = Column(String(50))         # inviato, errore, retry
    data_invio = Column(DateTime, default=datetime.utcnow) 
    letta = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow) 
    documento_id = Column(Integer, ForeignKey("documents.id"))  # Documento collegato
    utente_id = Column(Integer, ForeignKey("users.id"))  # Utente destinatario

class NotificheBloccate(Base):
    __tablename__ = "notifiche_bloccate"
    id = Column(Integer, primary_key=True)
    utente_id = Column(Integer, ForeignKey("users.id"))
    tipo_evento = Column(String(100))  # es: 'lean_warning', 'errore_ai', ecc.

class BulkNotificheModel(BaseModel):
    ids: List[int]
    azione: Literal["segna_lette", "elimina", "archivia"] 