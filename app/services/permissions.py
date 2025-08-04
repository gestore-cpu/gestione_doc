from typing import List
from app.models.ai_analysis import DocumentoAnalizzato
from app.models import User
from sqlalchemy.orm import Session


def filter_documents_for_user(db: Session, user: User) -> List[DocumentoAnalizzato]:
    """
    Restituisce solo i documenti visibili all'utente in base ad azienda e reparti.
    Compatibile sia con Postgres (ARRAY/JSON) che con SQLite (JSON/Text).
    """
    user_aziende = [az.nome for az in getattr(user, 'aziende', [])]
    user_reparti = [rep.nome for rep in getattr(user, 'reparti', [])]

    # Prova filtro SQL diretto (funziona su Postgres con ARRAY/JSON)
    try:
        docs = db.query(DocumentoAnalizzato).filter(
            DocumentoAnalizzato.azienda.in_(user_aziende),
            DocumentoAnalizzato.reparto.op('json_each.value IN ({})'.format(
                ','.join([f'"{r}"' for r in user_reparti])
            ))
        ).all()
        if docs:
            return docs
    except Exception:
        pass  # fallback a filtro Python

    # Fallback: filtro Python (compatibile con SQLite e ogni backend)
    all_docs = db.query(DocumentoAnalizzato).filter(
        DocumentoAnalizzato.azienda.in_(user_aziende)
    ).all()
    filtered = []
    for doc in all_docs:
        doc_reparti = doc.reparto or []
        if isinstance(doc_reparti, str):
            import json
            try:
                doc_reparti = json.loads(doc_reparti)
            except Exception:
                doc_reparti = [doc_reparti]
        if set(doc_reparti).intersection(user_reparti):
            filtered.append(doc)
    return filtered 