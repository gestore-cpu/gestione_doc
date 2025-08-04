from sqlalchemy import Column, String

preferenza_notifica = Column(String, default="email")  # opzioni: email, whatsapp, entrambi 