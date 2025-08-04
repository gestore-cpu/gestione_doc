from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class InsightQMSAI(Base):
    __tablename__ = "insight_qms_ai"
    
    id = Column(Integer, primary_key=True)
    insight_text = Column(Text, nullable=False)
    insight_type = Column(String(50), nullable=False)  # scadenza, mancante, revisione, struttura
    severity = Column(String(20), nullable=False)  # critico, attenzione, informativo
    stato = Column(String(20), default="attivo")  # attivo, risolto, ignorato
    documento_id = Column(Integer, ForeignKey("documenti_qms.id"), nullable=True)
    modulo_qms = Column(String(50), nullable=True)
    data_creazione = Column(DateTime, default=datetime.utcnow)
    task_id = Column(Integer, ForeignKey('task.id'), nullable=True)
    
    # Relazioni
    documento = relationship("DocumentiQMS", backref="insights_ai")
    task = relationship("Task", backref="qms_insight", uselist=False) 