from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class AccessLog(Base):
    __tablename__ = "access_log"
    id = Column(Integer, primary_key=True)
    user_email = Column(String)
    document_id = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow) 