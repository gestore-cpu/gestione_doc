"""
Safety switches per Manus Core.
Feature flags, rate limiting e controlli di sicurezza.
"""

import os
import time
from functools import wraps
from flask import request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

# ===== FEATURE FLAGS =====

def is_webhook_enabled():
    """Controlla se i webhook sono abilitati."""
    return os.getenv("MANUS_WEBHOOK_ENABLED", "true").lower() == "true"

def webhook_feature_flag(f):
    """Decorator per disabilitare webhook se necessario."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_webhook_enabled():
            logger.warning("⚠️ Webhook Manus disabilitati via feature flag")
            return jsonify({
                "error": "webhook_disabled",
                "message": "Webhook Manus temporaneamente disabilitati"
            }), 503
        return f(*args, **kwargs)
    return decorated_function

# ===== RATE LIMITING =====

class RateLimiter:
    """Rate limiter semplice per webhook."""
    
    def __init__(self, max_requests=60, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    def is_allowed(self):
        """Controlla se la richiesta è permessa."""
        now = time.time()
        
        # Rimuovi richieste vecchie
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.window_seconds]
        
        # Controlla limite
        if len(self.requests) >= self.max_requests:
            return False
        
        # Aggiungi richiesta corrente
        self.requests.append(now)
        return True

# Rate limiter globale per webhook
webhook_limiter = RateLimiter(max_requests=60, window_seconds=60)

def rate_limit_webhook(f):
    """Decorator per rate limiting sui webhook."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not webhook_limiter.is_allowed():
            logger.warning("⚠️ Rate limit superato per webhook Manus")
            return jsonify({
                "error": "rate_limit_exceeded",
                "message": "Troppe richieste webhook"
            }), 429
        return f(*args, **kwargs)
    return decorated_function

# ===== SECURITY CHECKS =====

def validate_webhook_security():
    """Validazioni di sicurezza per webhook."""
    # Controlla che il secret sia configurato
    secret = current_app.config.get("MANUS_WEBHOOK_SECRET")
    if not secret:
        logger.error("❌ MANUS_WEBHOOK_SECRET non configurato")
        return False
    
    # Controlla che il secret non sia quello di default
    if secret == "your_webhook_secret_here":
        logger.warning("⚠️ MANUS_WEBHOOK_SECRET è quello di default")
        return False
    
    return True

def log_webhook_event(event_type, event_data, success=True):
    """Logga eventi webhook per audit."""
    event_id = request.headers.get("X-Manus-Event-ID")
    delivery_id = request.headers.get("X-Manus-Delivery-ID")
    
    log_data = {
        "event_type": event_type,
        "event_id": event_id,
        "delivery_id": delivery_id,
        "success": success,
        "timestamp": time.time(),
        "ip": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", "")
    }
    
    if success:
        logger.info(f"📨 Webhook {event_type} processato: {log_data}")
    else:
        logger.error(f"❌ Webhook {event_type} fallito: {log_data}")
    
    return log_data

# ===== MONITORING HELPERS =====

class WebhookMetrics:
    """Metriche per monitoraggio webhook."""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.errors_5xx = 0
        self.errors_401 = 0
        self.last_reset = time.time()
        self.reset_interval = 3600  # 1 ora
    
    def record_request(self, success=True, status_code=None):
        """Registra una richiesta webhook."""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            
            if status_code:
                if status_code >= 500:
                    self.errors_5xx += 1
                elif status_code == 401:
                    self.errors_401 += 1
    
    def get_stats(self):
        """Ottieni statistiche correnti."""
        now = time.time()
        
        # Reset periodico
        if now - self.last_reset > self.reset_interval:
            self.reset()
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "errors_5xx": self.errors_5xx,
            "errors_401": self.errors_401,
            "success_rate": (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        }
    
    def reset(self):
        """Reset delle metriche."""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.errors_5xx = 0
        self.errors_401 = 0
        self.last_reset = time.time()

# Metriche globali
webhook_metrics = WebhookMetrics()

def monitor_webhook(f):
    """Decorator per monitoraggio webhook."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        success = False
        status_code = None
        
        try:
            result = f(*args, **kwargs)
            success = True
            status_code = result[1] if isinstance(result, tuple) else 200
            return result
        except Exception as e:
            logger.error(f"❌ Errore webhook: {e}")
            status_code = 500
            raise
        finally:
            webhook_metrics.record_request(success, status_code)
            
            # Log metriche se necessario
            stats = webhook_metrics.get_stats()
            if stats["errors_5xx"] > 5:  # Alert se > 5 errori 5xx
                logger.warning(f"🚨 Troppi errori 5xx: {stats['errors_5xx']}")
    
    return decorated_function

# ===== UTILITY FUNCTIONS =====

def rotate_webhook_secret():
    """Genera un nuovo secret per webhook."""
    import secrets
    new_secret = secrets.token_hex(32)
    logger.info(f"🔄 Nuovo webhook secret generato: {new_secret[:8]}...")
    return new_secret

def check_webhook_health():
    """Health check per webhook."""
    return {
        "webhook_enabled": is_webhook_enabled(),
        "rate_limit_remaining": webhook_limiter.max_requests - len(webhook_limiter.requests),
        "metrics": webhook_metrics.get_stats(),
        "security_valid": validate_webhook_security()
    }
