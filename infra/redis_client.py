"""
Redis client per cache e idempotency distribuita.
Gestisce connessioni Redis per l'applicazione.
"""

import redis
import os
import logging
from typing import Optional, Any
from flask import current_app

logger = logging.getLogger(__name__)

# Client Redis globale
_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """
    Ottiene il client Redis singleton.
    
    Returns:
        redis.Redis: Client Redis configurato
    """
    global _redis_client
    
    if _redis_client is None:
        try:
            redis_url = current_app.config.get("REDIS_URL", "redis://localhost:6379/2")
            _redis_client = redis.Redis.from_url(
                redis_url, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connessione
            _redis_client.ping()
            logger.info(f"✅ Connessione Redis stabilita: {redis_url}")
            
        except Exception as e:
            logger.error(f"❌ Errore connessione Redis: {e}")
            # Fallback a client mock per sviluppo
            _redis_client = MockRedisClient()
            logger.warning("⚠️ Usando Redis mock per sviluppo")
    
    return _redis_client

def close_redis_client():
    """Chiude la connessione Redis."""
    global _redis_client
    if _redis_client and not isinstance(_redis_client, MockRedisClient):
        _redis_client.close()
        _redis_client = None
        logger.info("🔌 Connessione Redis chiusa")

class MockRedisClient:
    """
    Client Redis mock per sviluppo senza Redis.
    Mantiene i dati in memoria per test.
    """
    
    def __init__(self):
        self._data = {}
        self._expiry = {}
        logger.info("🔧 Inizializzato Redis mock")
    
    def set(self, name: str, value: Any, nx: bool = False, ex: int = None) -> bool:
        """Simula SET con opzioni NX e EX."""
        if nx and name in self._data:
            return False
        
        self._data[name] = str(value)
        if ex:
            import time
            self._expiry[name] = time.time() + ex
        
        return True
    
    def get(self, name: str) -> Optional[str]:
        """Simula GET con controllo expiry."""
        if name not in self._data:
            return None
        
        # Controlla expiry
        if name in self._expiry:
            import time
            if time.time() > self._expiry[name]:
                del self._data[name]
                del self._expiry[name]
                return None
        
        return self._data[name]
    
    def delete(self, *names) -> int:
        """Simula DELETE."""
        count = 0
        for name in names:
            if name in self._data:
                del self._data[name]
                if name in self._expiry:
                    del self._expiry[name]
                count += 1
        return count
    
    def exists(self, *names) -> int:
        """Simula EXISTS."""
        count = 0
        for name in names:
            if name in self._data:
                # Controlla expiry
                if name in self._expiry:
                    import time
                    if time.time() > self._expiry[name]:
                        del self._data[name]
                        del self._expiry[name]
                        continue
                count += 1
        return count
    
    def ping(self) -> bool:
        """Simula PING."""
        return True
    
    def close(self):
        """Simula CLOSE."""
        self._data.clear()
        self._expiry.clear()

# Alias per comodità
r = get_redis_client
