"""
Client per l'API Manus Core.
Gestisce le chiamate HTTP con retry e gestione errori.
"""

import requests
import time
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class ManusClient:
    """
    Client per l'API Manus Core.
    
    Gestisce l'autenticazione e le chiamate HTTP con retry automatico.
    """
    
    def __init__(self):
        """Inizializza il client con configurazione da app config."""
        self.base = current_app.config["MANUS_BASE_URL"].rstrip("/")
        self.key = current_app.config["MANUS_API_KEY"]
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {self.key}", 
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def _get(self, path, params=None):
        """
        Esegue una richiesta GET con retry automatico.
        
        Args:
            path (str): Path dell'endpoint
            params (dict): Parametri query string
            
        Returns:
            dict: Risposta JSON
            
        Raises:
            requests.HTTPError: Se la richiesta fallisce dopo i retry
        """
        for i in range(3):
            try:
                r = self.s.get(
                    f"{self.base}{path}", 
                    params=params, 
                    timeout=20
                )
                if r.status_code < 500:
                    break
                time.sleep(0.8 * (2 ** i))
            except requests.RequestException as e:
                if i == 2:  # Ultimo tentativo
                    logger.error(f"Errore nella richiesta GET {path}: {e}")
                    raise
                time.sleep(0.8 * (2 ** i))
        
        r.raise_for_status()
        return r.json()

    def _post(self, path, data=None):
        """
        Esegue una richiesta POST con retry automatico.
        
        Args:
            path (str): Path dell'endpoint
            data (dict): Dati da inviare
            
        Returns:
            dict: Risposta JSON
            
        Raises:
            requests.HTTPError: Se la richiesta fallisce dopo i retry
        """
        for i in range(3):
            try:
                r = self.s.post(
                    f"{self.base}{path}", 
                    json=data, 
                    timeout=20
                )
                if r.status_code < 500:
                    break
                time.sleep(0.8 * (2 ** i))
            except requests.RequestException as e:
                if i == 2:  # Ultimo tentativo
                    logger.error(f"Errore nella richiesta POST {path}: {e}")
                    raise
                time.sleep(0.8 * (2 ** i))
        
        r.raise_for_status()
        return r.json()

    # === METODI PER MANUALI ===
    
    def list_manuals(self, azienda_ref: str):
        """
        Lista i manuali disponibili per un'azienda.
        
        Args:
            azienda_ref (str): Riferimento azienda in Manus
            
        Returns:
            list: Lista dei manuali
        """
        return self._get("/manuals", {"org": azienda_ref})

    def get_manual(self, manual_id: str):
        """
        Ottiene i dettagli di un manuale specifico.
        
        Args:
            manual_id (str): ID del manuale
            
        Returns:
            dict: Dettagli del manuale
        """
        return self._get(f"/manuals/{manual_id}")

    # === METODI PER CORSI ===
    
    def list_courses(self, azienda_ref: str):
        """
        Lista i corsi disponibili per un'azienda.
        
        Args:
            azienda_ref (str): Riferimento azienda in Manus
            
        Returns:
            list: Lista dei corsi
        """
        return self._get("/courses", {"org": azienda_ref})

    def get_course(self, course_id: str):
        """
        Ottiene i dettagli di un corso specifico.
        
        Args:
            course_id (str): ID del corso
            
        Returns:
            dict: Dettagli del corso
        """
        return self._get(f"/courses/{course_id}")

    def list_course_completions(self, course_id: str, since_iso: str = None):
        """
        Lista i completamenti di un corso.
        
        Args:
            course_id (str): ID del corso
            since_iso (str): Data ISO da cui filtrare (opzionale)
            
        Returns:
            dict: Lista dei completamenti
        """
        params = {"since": since_iso} if since_iso else None
        return self._get(f"/courses/{course_id}/completions", params)

    # === METODI PER UTENTI ===
    
    def get_user(self, user_id: str):
        """
        Ottiene i dettagli di un utente.
        
        Args:
            user_id (str): ID dell'utente
            
        Returns:
            dict: Dettagli dell'utente
        """
        return self._get(f"/users/{user_id}")

    def list_users(self, azienda_ref: str):
        """
        Lista gli utenti di un'azienda.
        
        Args:
            azienda_ref (str): Riferimento azienda in Manus
            
        Returns:
            list: Lista degli utenti
        """
        return self._get("/users", {"org": azienda_ref})

    # === METODI PER WEBHOOK ===
    
    def register_webhook(self, webhook_url: str, events: list = None):
        """
        Registra un webhook per ricevere notifiche.
        
        Args:
            webhook_url (str): URL del webhook
            events (list): Lista degli eventi da monitorare
            
        Returns:
            dict: Dettagli del webhook registrato
        """
        data = {
            "url": webhook_url,
            "events": events or ["MANUAL_UPDATED", "COURSE_COMPLETED", "COURSE_UPDATED"]
        }
        return self._post("/webhooks", data)

    def list_webhooks(self):
        """
        Lista i webhook registrati.
        
        Returns:
            list: Lista dei webhook
        """
        return self._get("/webhooks")
