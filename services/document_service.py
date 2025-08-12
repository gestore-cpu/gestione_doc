from typing import Optional, List, Dict, Any
from models import Document, db
import os
import pdfplumber
from docx import Document as DocxDocument

def get_document_text(doc_id: int) -> str:
    """
    Recupera il testo di un documento dal database.
    
    Args:
        doc_id (int): ID del documento
        
    Returns:
        str: Testo del documento
        
    Raises:
        NotImplementedError: Se il documento non esiste o non è leggibile
    """
    # Recupera il documento dal database
    document = Document.query.get(doc_id)
    if not document:
        raise NotImplementedError(f"Documento {doc_id} non trovato")
    
    # Se il documento ha già contenuto testuale salvato, usalo
    if document.contenuto_testuale:
        return document.contenuto_testuale
    
    # Altrimenti, prova a leggere il file
    file_path = os.path.join('uploads', document.filename)
    if not os.path.exists(file_path):
        raise NotImplementedError(f"File {file_path} non trovato")
    
    # Estrai testo in base al tipo di file
    text = extract_text_from_file(file_path)
    
    # Salva il testo estratto nel database per future chiamate
    document.contenuto_testuale = text
    db.session.commit()
    
    return text

def extract_text_from_file(file_path: str) -> str:
    """
    Estrae il testo da un file in base alla sua estensione.
    
    Args:
        file_path (str): Percorso del file
        
    Returns:
        str: Testo estratto dal file
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    
    try:
        if file_extension == '.pdf':
            return extract_text_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            return extract_text_from_docx(file_path)
        elif file_extension in ['.txt', '.md']:
            return extract_text_from_text(file_path)
        else:
            raise NotImplementedError(f"Tipo di file {file_extension} non supportato")
    except Exception as e:
        raise NotImplementedError(f"Errore nell'estrazione del testo: {str(e)}")

def extract_text_from_pdf(file_path: str) -> str:
    """Estrae testo da un file PDF."""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

def extract_text_from_docx(file_path: str) -> str:
    """Estrae testo da un file DOCX."""
    doc = DocxDocument(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text.strip()

def extract_text_from_text(file_path: str) -> str:
    """Estrae testo da un file di testo."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()

def get_document_path(doc_id: int) -> str:
    """
    Ritorna il path locale del file (PDF/DOCX/TXT, ecc.)
    
    Args:
        doc_id (int): ID del documento
        
    Returns:
        str: Percorso completo del file
        
    Raises:
        NotImplementedError: Se il documento non esiste
    """
    # Recupera il documento dal database
    document = Document.query.get(doc_id)
    if not document:
        raise NotImplementedError(f"Documento {doc_id} non trovato")
    
    # Costruisci il percorso del file
    file_path = os.path.join('uploads', document.filename)
    
    # Verifica che il file esista
    if not os.path.exists(file_path):
        raise NotImplementedError(f"File {file_path} non trovato")
    
    return file_path

def list_documents_for_autotag(limit: int = 200) -> List[dict]:
    """
    Ritorna una lista dei documenti recenti/non taggati.
    
    Args:
        limit (int): Numero massimo di documenti da restituire
        
    Returns:
        List[dict]: Lista di documenti con campi minimi {"id": int, "title": str}
    """
    # Query per documenti recenti (ultimi 7 giorni) o senza tag AI
    documents = Document.query.filter(
        # Documenti creati negli ultimi 7 giorni
        Document.created_at >= db.func.date(db.func.now(), '-7 days')
    ).limit(limit).all()
    
    return [
        {
            "id": doc.id,
            "title": doc.title or doc.original_filename,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        }
        for doc in documents
    ]

def save_tags(doc_id: int, tags: Dict[str, Any]) -> None:
    """
    Salva i tag nel DB.
    
    Args:
        doc_id (int): ID del documento
        tags (Dict[str, Any]): Tag da salvare
    """
    document = Document.query.get(doc_id)
    if not document:
        raise ValueError(f"Documento {doc_id} non trovato")
    
    # Salva i tag come JSON nel campo meta o crea campi dedicati
    if not hasattr(document, 'ai_tags'):
        # Se non esiste il campo, salva in meta o crea campo
        if hasattr(document, 'meta'):
            meta = document.meta or {}
            meta['ai_tags'] = tags
            document.meta = meta
        else:
            # Fallback: salva come stringa JSON in un campo esistente
            document.description = f"AI Tags: {str(tags)}"
    else:
        document.ai_tags = tags
    
    db.session.commit()
