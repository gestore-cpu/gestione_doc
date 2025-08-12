from app import db

class AIMapping(db.Model):
    __tablename__ = "ai_mapping"
    
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, index=True, unique=True, nullable=False)
    openai_file_id = db.Column(db.String(128), nullable=False)
    vector_store_id = db.Column(db.String(128), nullable=False)  # 1 store condiviso o per-tenant
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    def __repr__(self):
        return f'<AIMapping {self.doc_id} -> {self.openai_file_id}>'
