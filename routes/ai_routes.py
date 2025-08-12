"""
Route Flask per l'analisi AI dei documenti.
Analisi intelligente di download, firme, documenti obbligatori e attività utenti.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from services.ai.gpt_provider import GptProvider
from services.ai.filesearch_provider import FileSearchProvider
from services.document_service import get_document_text, get_document_path
from models import db, SecurityAuditLog
from models.ai_mapping import AIMapping
from datetime import datetime
import json
import time

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")
provider = GptProvider()
fs = FileSearchProvider()

# === RATE LIMITING ===
ai_rate_limit_window = 60  # secondi
ai_rate_limit_max = 10     # chiamate per finestra
ai_rate_limit_logs = {}    # Cache per rate limiting

def check_ai_rate_limit(user_id: int) -> tuple[bool, str]:
    """
    Verifica il rate limit per le chiamate AI.
    
    Args:
        user_id (int): ID dell'utente
        
    Returns:
        tuple[bool, str]: (is_allowed, message)
    """
    now = time.time()
    user_key = f"ai_{user_id}"
    
    # Inizializza log per l'utente se non esiste
    if user_key not in ai_rate_limit_logs:
        ai_rate_limit_logs[user_key] = []
    
    # Rimuovi chiamate vecchie
    ai_rate_limit_logs[user_key] = [
        ts for ts in ai_rate_limit_logs[user_key] 
        if now - ts < ai_rate_limit_window
    ]
    
    # Verifica se il limite è superato
    if len(ai_rate_limit_logs[user_key]) >= ai_rate_limit_max:
        return False, f"Rate limit superato: massimo {ai_rate_limit_max} chiamate AI per {ai_rate_limit_window} secondi"
    
    # Aggiungi chiamata corrente
    ai_rate_limit_logs[user_key].append(now)
    return True, "OK"

def _resolve_text(doc_id):
    """Risolve il testo da usare per l'analisi AI."""
    body = request.get_json(silent=True) or {}
    if body.get("text"):
        return body["text"]
    # fallback al service document
    return get_document_text(doc_id)

def _log_ai_activity(doc_id: int, action: str, success: bool = True, error: str = None):
    """Logga l'attività AI per audit."""
    try:
        log = SecurityAuditLog(
            ts=datetime.utcnow(),
            user_id=current_user.id if current_user.is_authenticated else None,
            ip=request.remote_addr,
            action=f"AI_{action}",
            object_type="document",
            object_id=doc_id,
            meta={
                "ai_model": provider.model,
                "success": success,
                "error": error,
                "user_agent": request.headers.get('User-Agent', '')
            },
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Errore nel logging AI activity: {str(e)}")

@ai_bp.post("/tag/<int:doc_id>")
@login_required
def ai_tag(doc_id: int):
    """
    Tagga un documento con metadati strutturati.
    
    Args:
        doc_id (int): ID del documento da taggare
        
    Returns:
        JSON con i metadati estratti
    """
    # Rate limiting
    is_allowed, rate_limit_msg = check_ai_rate_limit(current_user.id)
    if not is_allowed:
        return jsonify({'error': 'Rate limit exceeded', 'message': rate_limit_msg}), 429
    
    try:
        text = _resolve_text(doc_id)
        data = provider.tag(text)
        
        _log_ai_activity(doc_id, "TAG", success=True)
        
        return jsonify(data), 200
        
    except Exception as e:
        error_msg = str(e)
        _log_ai_activity(doc_id, "TAG", success=False, error=error_msg)
        return jsonify({"error": error_msg}), 500

@ai_bp.post("/summarize/<int:doc_id>")
@login_required
def ai_summarize(doc_id: int):
    """
    Genera un riassunto del documento.
    
    Args:
        doc_id (int): ID del documento da riassumere
        
    Returns:
        JSON con il riassunto
    """
    # Rate limiting
    is_allowed, rate_limit_msg = check_ai_rate_limit(current_user.id)
    if not is_allowed:
        return jsonify({'error': 'Rate limit exceeded', 'message': rate_limit_msg}), 429
    
    try:
        text = _resolve_text(doc_id)
        max_words = (request.get_json(silent=True) or {}).get("max_words", 120)
        summary = provider.summarize(text, max_words=max_words)
        
        _log_ai_activity(doc_id, "SUMMARIZE", success=True)
        
        return jsonify({"summary": summary}), 200
        
    except Exception as e:
        error_msg = str(e)
        _log_ai_activity(doc_id, "SUMMARIZE", success=False, error=error_msg)
        return jsonify({"error": error_msg}), 500

@ai_bp.post("/extract/<int:doc_id>")
@login_required
def ai_extract(doc_id: int):
    """
    Estrae informazioni strutturate dal documento secondo uno schema JSON.
    
    Args:
        doc_id (int): ID del documento
        
    Returns:
        JSON con i dati estratti
    """
    # Rate limiting
    is_allowed, rate_limit_msg = check_ai_rate_limit(current_user.id)
    if not is_allowed:
        return jsonify({'error': 'Rate limit exceeded', 'message': rate_limit_msg}), 429
    
    try:
        body = request.get_json() or {}
        schema = body.get("schema")
        if not schema:
            return jsonify({"error": "schema mancante"}), 400
            
        text = body.get("text") or get_document_text(doc_id)
        out = provider.extract(text, schema)
        
        _log_ai_activity(doc_id, "EXTRACT", success=True)
        
        return jsonify(out), 200
        
    except Exception as e:
        error_msg = str(e)
        _log_ai_activity(doc_id, "EXTRACT", success=False, error=error_msg)
        return jsonify({"error": error_msg}), 500

@ai_bp.post("/qa")
@login_required
def ai_qa():
    """
    Risponde a una domanda basandosi sul contesto fornito.
    
    Returns:
        JSON con la risposta
    """
    # Rate limiting
    is_allowed, rate_limit_msg = check_ai_rate_limit(current_user.id)
    if not is_allowed:
        return jsonify({'error': 'Rate limit exceeded', 'message': rate_limit_msg}), 429
    
    try:
        body = request.get_json() or {}
        question = body.get("query") or body.get("question")
        if not question:
            return jsonify({"error": "query mancante"}), 400
            
        context = body.get("text") or ""
        
        # opzionale: se passi doc_id, recupera testo
        doc_id = body.get("doc_id")
        if doc_id and not context:
            context = get_document_text(int(doc_id))
            
        answer = provider.qa(context, question)
        
        # Log dell'attività QA
        if doc_id:
            _log_ai_activity(int(doc_id), "QA", success=True)
        else:
            # Log generico per QA senza doc_id
            try:
                log = SecurityAuditLog(
                    ts=datetime.utcnow(),
                    user_id=current_user.id if current_user.is_authenticated else None,
                    ip=request.remote_addr,
                    action="AI_QA",
                    object_type="general",
                    object_id=None,
                    meta={
                        "ai_model": provider.model,
                        "success": True,
                        "question": question[:100] + "..." if len(question) > 100 else question
                    },
                    user_agent=request.headers.get('User-Agent', '')
                )
                db.session.add(log)
                db.session.commit()
            except Exception as e:
                current_app.logger.error(f"Errore nel logging QA activity: {str(e)}")
        
        return jsonify({"answer": answer}), 200
        
    except Exception as e:
        error_msg = str(e)
        # Log dell'errore
        try:
            log = SecurityAuditLog(
                ts=datetime.utcnow(),
                user_id=current_user.id if current_user.is_authenticated else None,
                ip=request.remote_addr,
                action="AI_QA",
                object_type="general",
                object_id=None,
                meta={
                    "ai_model": provider.model,
                    "success": False,
                    "error": error_msg
                },
                user_agent=request.headers.get('User-Agent', '')
            )
            db.session.add(log)
            db.session.commit()
        except Exception as log_e:
            current_app.logger.error(f"Errore nel logging QA error: {str(log_e)}")
            
        return jsonify({"error": error_msg}), 500

@ai_bp.post("/fs/upload/<int:doc_id>")
@login_required
def ai_fs_upload(doc_id: int):
    """
    Carica un documento nel vector store per il file search.
    
    Args:
        doc_id (int): ID del documento da caricare
        
    Returns:
        JSON con il risultato dell'upload
    """
    # Rate limiting
    is_allowed, rate_limit_msg = check_ai_rate_limit(current_user.id)
    if not is_allowed:
        return jsonify({'error': 'Rate limit exceeded', 'message': rate_limit_msg}), 429
    
    try:
        # Verifica che l'utente abbia accesso al documento
        from models import Document
        document = Document.query.get(doc_id)
        if not document:
            return jsonify({"error": "Documento non trovato"}), 404
        
        # TODO: Verifica autorizzazioni utente per questo documento
        # if not current_user.can_access_document(doc_id):
        #     return jsonify({"error": "Accesso non autorizzato"}), 403
        
        # Ottieni il percorso del file
        file_path = get_document_path(doc_id)
        
        # Carica nel vector store
        openai_file_id = fs.upload_file(file_path)
        
        # Salva mapping nel database
        mapping = AIMapping.query.filter_by(doc_id=doc_id).first()
        if not mapping:
            mapping = AIMapping(
                doc_id=doc_id, 
                openai_file_id=openai_file_id, 
                vector_store_id=fs.vector_store_id
            )
            db.session.add(mapping)
        else:
            mapping.openai_file_id = openai_file_id
            mapping.vector_store_id = fs.vector_store_id
        
        db.session.commit()
        
        _log_ai_activity(doc_id, "FS_UPLOAD", success=True)
        
        return jsonify({
            "ok": True, 
            "doc_id": doc_id, 
            "openai_file_id": openai_file_id
        }), 200
        
    except Exception as e:
        error_msg = str(e)
        _log_ai_activity(doc_id, "FS_UPLOAD", success=False, error=error_msg)
        return jsonify({"error": error_msg}), 500

@ai_bp.post("/fs/qa")
@login_required
def ai_fs_qa():
    """
    Esegue una query con file search sui documenti caricati.
    
    Returns:
        JSON con la risposta e citazioni
    """
    # Rate limiting
    is_allowed, rate_limit_msg = check_ai_rate_limit(current_user.id)
    if not is_allowed:
        return jsonify({'error': 'Rate limit exceeded', 'message': rate_limit_msg}), 429
    
    try:
        body = request.get_json() or {}
        query = body.get("query") or body.get("question")
        if not query:
            return jsonify({"error": "query mancante"}), 400
        
        # Esegui query con file search
        answer = fs.qa(query)
        
        # Log dell'attività
        try:
            log = SecurityAuditLog(
                ts=datetime.utcnow(),
                user_id=current_user.id if current_user.is_authenticated else None,
                ip=request.remote_addr,
                action="AI_FS_QA",
                object_type="file_search",
                object_id=None,
                meta={
                    "ai_model": "gpt-4o-mini",
                    "success": True,
                    "query": query[:100] + "..." if len(query) > 100 else query,
                    "vector_store_id": fs.vector_store_id
                },
                user_agent=request.headers.get('User-Agent', '')
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Errore nel logging FS QA activity: {str(e)}")
        
        return jsonify({"answer": answer}), 200
        
    except Exception as e:
        error_msg = str(e)
        # Log dell'errore
        try:
            log = SecurityAuditLog(
                ts=datetime.utcnow(),
                user_id=current_user.id if current_user.is_authenticated else None,
                ip=request.remote_addr,
                action="AI_FS_QA",
                object_type="file_search",
                object_id=None,
                meta={
                    "ai_model": "gpt-4o-mini",
                    "success": False,
                    "error": error_msg
                },
                user_agent=request.headers.get('User-Agent', '')
            )
            db.session.add(log)
            db.session.commit()
        except Exception as log_e:
            current_app.logger.error(f"Errore nel logging FS QA error: {str(log_e)}")
            
        return jsonify({"error": error_msg}), 500

@ai_bp.post("/batch/autotag/run")
@login_required
def ai_batch_autotag_run():
    """
    Esegue manualmente il job di autotagging batch.
    
    Returns:
        JSON con il risultato dell'operazione
    """
    # Rate limiting
    is_allowed, rate_limit_msg = check_ai_rate_limit(current_user.id)
    if not is_allowed:
        return jsonify({'error': 'Rate limit exceeded', 'message': rate_limit_msg}), 429
    
    try:
        # TODO: proteggi con ruolo admin
        from scheduler_config import job_ai_autotag_recent
        
        # Log dell'inizio
        _log_ai_activity(None, "BATCH_AUTOTAG", success=True)
        
        # Esegui il job
        job_ai_autotag_recent()
        
        return jsonify({"ok": True, "message": "Autotagging completato"}), 200
        
    except Exception as e:
        error_msg = str(e)
        _log_ai_activity(None, "BATCH_AUTOTAG", success=False, error=error_msg)
        return jsonify({"ok": False, "error": error_msg}), 500
