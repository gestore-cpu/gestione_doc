from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from extensions import db
from datetime import datetime

class AnalisiLean(db.Model):
    __tablename__ = "analisi_lean"
    id = Column(Integer, primary_key=True)
    documento_id = Column(Integer, ForeignKey("documents.id"))
    principio = Column(String)
    violazione = Column(Boolean)
    suggerimento = Column(Text)
    creato_il = Column(DateTime, default=datetime.utcnow)
    task_creato = Column(Boolean, default=False)
    autore_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return f"<AnalisiLean {self.id} - Doc {self.documento_id} - {self.principio}>" 