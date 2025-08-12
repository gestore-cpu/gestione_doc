"""
Decorator per sicurezza e controllo accessi.
Include idempotency, rate limiting e validazioni.
"""

import logging
from functools import wraps
from flask import request, jsonify, current_app
from security.idempotency import use_idempotency, generate_idempotency_key
from infra.redis_client import get_redis_client
import time

logger = logging.getLogger(__name__)

def require_idempotency(param: str = "idempotency_key"):
    """
    Decorator per richiedere idempotency key.
    
    Args:
        param (str): Nome del parametro per la chiave idempotente
        
    Returns:
        function: Decorator function
    """
    def wrap(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            # Cerca la chiave idempotente nei parametri o headers
            key = request.args.get(param) or request.headers.get("X-Idempotency-Key")
            
            if not key:
                return jsonify({
                    "error": "missing_idempotency_key",
                    "message": f"Chiave idempotente richiesta in parametro '{param}' o header 'X-Idempotency-Key'"
                }), 400
            
            # Controlla se la chiave è già stata usata
            ttl = current_app.config.get("IDEMP_TTL_SEC", 7200)
            if not use_idempotency(key, ttl):
                return jsonify({
                    "status": "duplicate",
                    "idempotency_key": key,
                    "message": "Operazione già eseguita con questa chiave idempotente"
                }), 200
            
            # Esegui la funzione originale
            return fn(*args, **kwargs)
        return inner
    return wrap

def auto_idempotency(user_based: bool = True):
    """
    Decorator per idempotency automatica basata sui dati della richiesta.
    
    Args:
        user_based (bool): Se True, include l'utente nella chiave
        
    Returns:
        function: Decorator function
    """
    def wrap(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            from flask_login import current_user
            
            # Genera chiave basata sui dati della richiesta
            request_data = {
                "method": request.method,
                "path": request.path,
                "data": request.get_data(as_text=True),
                "args": dict(request.args)
            }
            
            if user_based and current_user.is_authenticated:
                request_data["user_id"] = current_user.id
            
            # Genera chiave idempotente
            import json
            data_str = json.dumps(request_data, sort_keys=True)
            key = generate_idempotency_key(data_str, current_user.id if user_based and current_user.is_authenticated else None)
            
            # Controlla idempotency
            ttl = current_app.config.get("IDEMP_TTL_SEC", 7200)
            if not use_idempotency(key, ttl):
                return jsonify({
                    "status": "duplicate",
                    "idempotency_key": key,
                    "message": "Operazione già eseguita con dati identici"
                }), 200
            
            # Esegui la funzione originale
            return fn(*args, **kwargs)
        return inner
    return wrap

def rate_limit(max_requests: int = 60, window_seconds: int = 60, key_prefix: str = "rate_limit"):
    """
    Decorator per rate limiting basato su Redis.
    
    Args:
        max_requests (int): Numero massimo di richieste
        window_seconds (int): Finestra temporale in secondi
        key_prefix (str): Prefisso per le chiavi Redis
        
    Returns:
        function: Decorator function
    """
    def wrap(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            from flask_login import current_user
            
            try:
                redis_client = get_redis_client()
                
                # Genera chiave per rate limiting
                if current_user.is_authenticated:
                    rate_key = f"{key_prefix}:{current_user.id}:{request.path}"
                else:
                    rate_key = f"{key_prefix}:anonymous:{request.remote_addr}:{request.path}"
                
                now = time.time()
                window_start = now - window_seconds
                
                # Usa Redis Sorted Set per tracking
                redis_client.zremrangebyscore(rate_key, 0, window_start)
                
                # Conta richieste nella finestra
                request_count = redis_client.zcard(rate_key)
                
                if request_count >= max_requests:
                    return jsonify({
                        "error": "rate_limit_exceeded",
                        "message": f"Troppe richieste. Limite: {max_requests} per {window_seconds}s",
                        "retry_after": window_seconds
                    }), 429
                
                # Aggiungi richiesta corrente
                redis_client.zadd(rate_key, {str(now): now})
                redis_client.expire(rate_key, window_seconds)
                
                # Aggiungi header con info rate limit
                response = fn(*args, **kwargs)
                if hasattr(response, 'headers'):
                    response.headers['X-RateLimit-Limit'] = str(max_requests)
                    response.headers['X-RateLimit-Remaining'] = str(max_requests - request_count - 1)
                    response.headers['X-RateLimit-Reset'] = str(int(now + window_seconds))
                
                return response
                
            except Exception as e:
                logger.error(f"❌ Errore rate limiting: {e}")
                # In caso di errore Redis, permette la richiesta
                return fn(*args, **kwargs)
        
        return inner
    return wrap

def require_json_content_type():
    """
    Decorator per richiedere Content-Type application/json.
    
    Returns:
        function: Decorator function
    """
    def wrap(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    "error": "invalid_content_type",
                    "message": "Content-Type deve essere application/json"
                }), 400
            
            return fn(*args, **kwargs)
        return inner
    return wrap

def validate_required_fields(*required_fields):
    """
    Decorator per validare campi obbligatori nel JSON.
    
    Args:
        *required_fields: Lista di campi obbligatori
        
    Returns:
        function: Decorator function
    """
    def wrap(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            data = request.get_json() or {}
            
            missing_fields = []
            for field in required_fields:
                if field not in data or data[field] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    "error": "missing_required_fields",
                    "message": f"Campi obbligatori mancanti: {', '.join(missing_fields)}",
                    "missing_fields": missing_fields
                }), 400
            
            return fn(*args, **kwargs)
        return inner
    return wrap

def log_audit(action: str, resource_type: str = None):
    """
    Decorator per logging audit delle operazioni.
    
    Args:
        action (str): Azione eseguita
        resource_type (str): Tipo di risorsa
        
    Returns:
        function: Decorator function
    """
    def wrap(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            from flask_login import current_user
            import json
            
            start_time = time.time()
            
            try:
                # Esegui la funzione originale
                result = fn(*args, **kwargs)
                
                # Log successo
                audit_data = {
                    "action": action,
                    "resource_type": resource_type,
                    "user_id": current_user.id if current_user.is_authenticated else None,
                    "user_email": current_user.email if current_user.is_authenticated else None,
                    "ip_address": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent"),
                    "method": request.method,
                    "path": request.path,
                    "status_code": result[1] if isinstance(result, tuple) else 200,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "timestamp": time.time()
                }
                
                logger.info(f"📝 AUDIT: {json.dumps(audit_data)}")
                
                return result
                
            except Exception as e:
                # Log errore
                audit_data = {
                    "action": action,
                    "resource_type": resource_type,
                    "user_id": current_user.id if current_user.is_authenticated else None,
                    "user_email": current_user.email if current_user.is_authenticated else None,
                    "ip_address": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent"),
                    "method": request.method,
                    "path": request.path,
                    "error": str(e),
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "timestamp": time.time()
                }
                
                logger.error(f"❌ AUDIT ERROR: {json.dumps(audit_data)}")
                raise
        
        return inner
    return wrap
