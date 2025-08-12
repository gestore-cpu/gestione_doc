"""
Sistema di idempotency basato su Redis.
Gestisce chiavi idempotenti per evitare operazioni duplicate.
"""

import time
import hashlib
import logging
from typing import Optional
from infra.redis_client import get_redis_client

logger = logging.getLogger(__name__)

def generate_idempotency_key(data: str, user_id: Optional[int] = None) -> str:
    """
    Genera una chiave idempotente basata sui dati e opzionalmente l'utente.
    
    Args:
        data (str): Dati da hasciare
        user_id (int, optional): ID utente per isolamento
        
    Returns:
        str: Chiave idempotente
    """
    content = f"{data}:{user_id or 'anonymous'}"
    return hashlib.sha256(content.encode()).hexdigest()

def use_idempotency(key: str, ttl: int = 7200) -> bool:
    """
    Controlla se una chiave idempotente è già stata usata.
    
    Args:
        key (str): Chiave idempotente
        ttl (int): Time to live in secondi (default 2h)
        
    Returns:
        bool: True se prima volta, False se già usata
    """
    try:
        redis_client = get_redis_client()
        redis_key = f"idemp:{key}"
        
        # Prova a settare la chiave con NX (solo se non esiste)
        result = redis_client.set(
            name=redis_key, 
            value=int(time.time()), 
            nx=True, 
            ex=ttl
        )
        
        if result:
            logger.info(f"✅ Nuova chiave idempotente: {key[:8]}...")
            return True
        else:
            logger.info(f"🔄 Chiave idempotente già usata: {key[:8]}...")
            return False
            
    except Exception as e:
        logger.error(f"❌ Errore idempotency per chiave {key[:8]}...: {e}")
        # In caso di errore Redis, permette l'operazione
        return True

def get_idempotency_info(key: str) -> Optional[dict]:
    """
    Ottiene informazioni su una chiave idempotente.
    
    Args:
        key (str): Chiave idempotente
        
    Returns:
        dict: Informazioni sulla chiave o None se non esiste
    """
    try:
        redis_client = get_redis_client()
        redis_key = f"idemp:{key}"
        
        timestamp = redis_client.get(redis_key)
        if timestamp:
            return {
                "key": key,
                "created_at": int(timestamp),
                "exists": True
            }
        return None
        
    except Exception as e:
        logger.error(f"❌ Errore recupero info idempotency: {e}")
        return None

def clear_idempotency_key(key: str) -> bool:
    """
    Cancella una chiave idempotente.
    
    Args:
        key (str): Chiave idempotente
        
    Returns:
        bool: True se cancellata, False se errore
    """
    try:
        redis_client = get_redis_client()
        redis_key = f"idemp:{key}"
        
        result = redis_client.delete(redis_key)
        if result:
            logger.info(f"🗑️ Chiave idempotente cancellata: {key[:8]}...")
            return True
        return False
        
    except Exception as e:
        logger.error(f"❌ Errore cancellazione idempotency: {e}")
        return False

def cleanup_expired_idempotency_keys() -> int:
    """
    Pulisce le chiavi idempotenti scadute.
    Redis fa questo automaticamente, ma può essere utile per manutenzione.
    
    Returns:
        int: Numero di chiavi pulite
    """
    try:
        redis_client = get_redis_client()
        
        # Pattern per trovare tutte le chiavi idempotenti
        pattern = "idemp:*"
        keys = redis_client.keys(pattern)
        
        cleaned = 0
        for key in keys:
            # Redis gestisce automaticamente l'expiry
            # Questo è solo per logging
            if not redis_client.exists(key):
                cleaned += 1
        
        if cleaned > 0:
            logger.info(f"🧹 Pulite {cleaned} chiavi idempotenti scadute")
        
        return cleaned
        
    except Exception as e:
        logger.error(f"❌ Errore pulizia chiavi idempotenti: {e}")
        return 0
