"""
Middleware per l'audit delle richieste autenticate.
Registra automaticamente tutte le azioni degli utenti nel sistema di sicurezza.
"""

import json
import logging
from datetime import datetime
from flask import request, g, current_app
from flask_login import current_user
from extensions import db
from models import SecurityAuditLog
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def get_client_ip() -> str:
    """
    Ottiene l'indirizzo IP reale del client considerando proxy e load balancer.
    
    Returns:
        str: Indirizzo IP del client
    """
    # Controlla headers in ordine di priorità
    headers_to_check = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_REAL_IP',
        'HTTP_X_FORWARDED_HOST',
        'REMOTE_ADDR'
    ]
    
    for header in headers_to_check:
        ip = request.environ.get(header)
        if ip:
            # Se X-Forwarded-For contiene più IP, prendi il primo
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            return ip
    
    # Fallback
    return request.remote_addr or 'unknown'


def extract_object_info() -> tuple[Optional[str], Optional[int]]:
    """
    Estrae informazioni sull'oggetto dalla richiesta.
    
    Returns:
        tuple: (object_type, object_id)
    """
    object_type = None
    object_id = None
    
    # Controlla view_args per parametri URL
    if hasattr(request, 'view_args') and request.view_args:
        # Cerca ID comuni nei parametri URL
        for key, value in request.view_args.items():
            if key.endswith('_id') and isinstance(value, int):
                object_type = key.replace('_id', '')
                object_id = value
                break
            elif key == 'id' and isinstance(value, int):
                # Deduce il tipo dall'endpoint
                endpoint = request.endpoint or ''
                if 'document' in endpoint:
                    object_type = 'document'
                elif 'user' in endpoint:
                    object_type = 'user'
                elif 'file' in endpoint:
                    object_type = 'file'
                else:
                    object_type = 'unknown'
                object_id = value
                break
    
    # Controlla JSON payload per POST/PUT
    if request.is_json and request.method in ['POST', 'PUT', 'PATCH']:
        try:
            json_data = request.get_json()
            if json_data:
                # Cerca ID comuni nel payload
                for key in ['document_id', 'file_id', 'user_id', 'id']:
                    if key in json_data and isinstance(json_data[key], int):
                        object_type = key.replace('_id', '') if key != 'id' else 'unknown'
                        object_id = json_data[key]
                        break
        except Exception:
            pass  # Ignora errori di parsing JSON
    
    return object_type, object_id


def sanitize_meta_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rimuove dati sensibili dai metadati prima del salvataggio.
    
    Args:
        data: Dati da sanitizzare
        
    Returns:
        Dict: Dati sanitizzati
    """
    sensitive_keys = [
        'password', 'password_hash', 'secret', 'token', 'key',
        'credentials', 'auth', 'session', 'csrf_token'
    ]
    
    def sanitize_dict(d):
        if not isinstance(d, dict):
            return d
        
        sanitized = {}
        for k, v in d.items():
            key_lower = str(k).lower()
            if any(sens in key_lower for sens in sensitive_keys):
                sanitized[k] = '***HIDDEN***'
            elif isinstance(v, dict):
                sanitized[k] = sanitize_dict(v)
            elif isinstance(v, list):
                sanitized[k] = [sanitize_dict(item) if isinstance(item, dict) else item for item in v]
            else:
                sanitized[k] = v
        return sanitized
    
    return sanitize_dict(data)


def should_audit_request() -> bool:
    """
    Determina se la richiesta deve essere sottoposta ad audit.
    
    Returns:
        bool: True se deve essere tracciata
    """
    # Non tracciare richieste di asset statici
    if request.endpoint in ['static', None]:
        return False
    
    # Non tracciare richieste di health check o debug
    if request.path.startswith(('/static/', '/favicon.ico', '/_debug')):
        return False
    
    # Non tracciare richieste GET di sola lettura a meno che non siano critiche
    if request.method == 'GET':
        critical_paths = [
            '/admin/', '/download/', '/docs/', '/api/',
            '/export/', '/report/', '/audit/', '/alert/'
        ]
        if not any(request.path.startswith(path) for path in critical_paths):
            return False
    
    # Traccia sempre POST, PUT, DELETE, PATCH
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        return True
    
    # Traccia GET critici
    return True


def log_request_audit(user_id: Optional[int], ip: str, action: str, 
                     object_type: Optional[str], object_id: Optional[int],
                     meta: Dict[str, Any], user_agent: Optional[str]) -> None:
    """
    Salva l'audit log nel database.
    
    Args:
        user_id: ID dell'utente (None per utenti non autenticati)
        ip: Indirizzo IP
        action: Azione eseguita
        object_type: Tipo di oggetto
        object_id: ID dell'oggetto
        meta: Metadati della richiesta
        user_agent: User agent del browser
    """
    try:
        audit_log = SecurityAuditLog(
            user_id=user_id,
            ip=ip,
            action=action,
            object_type=object_type,
            object_id=object_id,
            meta=sanitize_meta_data(meta),
            user_agent=user_agent[:255] if user_agent else None  # Tronca se troppo lungo
        )
        
        db.session.add(audit_log)
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Errore salvataggio audit log: {e}")
        db.session.rollback()


def check_alert_rules(user_id: Optional[int], action: str, object_id: Optional[int]) -> None:
    """
    Verifica le regole di alert di sicurezza.
    Implementazione placeholder - sarà completata nel step 5.
    
    Args:
        user_id: ID dell'utente
        action: Azione eseguita
        object_id: ID dell'oggetto
    """
    # TODO: Implementare nel step 5 - Regole Alert
    pass


class AuditMiddleware:
    """
    Middleware Flask per l'audit automatico delle richieste.
    """
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        Inizializza il middleware con l'app Flask.
        
        Args:
            app: Istanza dell'app Flask
        """
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """
        Eseguito prima di ogni richiesta.
        """
        # Salva informazioni sulla richiesta per l'uso successivo
        g.audit_start_time = datetime.utcnow()
        g.audit_ip = get_client_ip()
    
    def after_request(self, response):
        """
        Eseguito dopo ogni richiesta completata.
        
        Args:
            response: Oggetto response Flask
            
        Returns:
            Response: Response modificata
        """
        try:
            # Verifica se la richiesta deve essere tracciata
            if not should_audit_request():
                return response
            
            # Ottieni informazioni utente
            user_id = current_user.id if current_user.is_authenticated else None
            
            # Se l'utente non è autenticato, traccia solo richieste critiche
            if not user_id and request.method == 'GET':
                return response
            
            # Costruisci l'azione
            action = f"{request.method} {request.endpoint or request.path}"
            
            # Estrai informazioni sull'oggetto
            object_type, object_id = extract_object_info()
            
            # Costruisci metadati
            meta = {
                'method': request.method,
                'path': request.path,
                'endpoint': request.endpoint,
                'status_code': response.status_code,
                'response_time_ms': int((datetime.utcnow() - g.audit_start_time).total_seconds() * 1000),
                'content_length': response.content_length,
                'referrer': request.referrer
            }
            
            # Aggiungi parametri query se presenti
            if request.args:
                meta['query_params'] = dict(request.args)
            
            # Aggiungi payload JSON se presente (sanitizzato)
            if request.is_json and request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    json_data = request.get_json()
                    if json_data:
                        meta['json_payload'] = json_data
                except Exception:
                    meta['json_payload'] = 'ERROR_PARSING_JSON'
            
            # Ottieni user agent
            user_agent = request.headers.get('User-Agent')
            
            # Salva audit log
            log_request_audit(
                user_id=user_id,
                ip=g.audit_ip,
                action=action,
                object_type=object_type,
                object_id=object_id,
                meta=meta,
                user_agent=user_agent
            )
            
            # Verifica regole di alert (se user_id presente)
            if user_id:
                check_alert_rules(user_id, action, object_id)
            
        except Exception as e:
            logger.error(f"Errore in audit middleware: {e}")
            # Non propagare l'errore per non interrompere la richiesta
        
        return response
