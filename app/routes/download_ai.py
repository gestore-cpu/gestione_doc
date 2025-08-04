from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, get_current_user
from app.models import Document
from app.services.ai import ai_filter_documents
from typing import List

router = APIRouter(prefix="/ai/download", tags=["AI - Download"])

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    document_ids: List[int]

@router.post("/search", response_model=QueryResponse)
def search_documents_ai(request: QueryRequest, db: Session = Depends(get_db), user = Depends(get_current_user)):
    if user.role not in ["admin", "user"]:
        raise HTTPException(status_code=403, detail="Accesso negato")

    # Recupera tutti i documenti disponibili all’utente
    all_docs = db.query(Document).all()
    # Applica filtro AI (simulato o reale)
    filtered_ids = ai_filter_documents(request.query, all_docs, user)
    return {"document_ids": filtered_ids} 