import os
from typing import List, Optional, Dict, Any
from openai import OpenAI

_CLIENT = None

def _client():
    """Ritorna il client OpenAI riutilizzabile per risparmiare memoria"""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=30.0  # Timeout breve per evitare 504
        )
    return _CLIENT

class FileSearchProvider:
    def __init__(self, vector_store_id: Optional[str] = None):
        self.client = _client()
        self.vector_store_id = vector_store_id or self._ensure_default_store()

    def _ensure_default_store(self) -> str:
        """Crea o recupera il vector store di default"""
        try:
            # Prova a recuperare store esistente
            stores = self.client.vector_stores.list()
            for store in stores.data:
                if store.name == "DOCS-Default-Store":
                    return store.id
            
            # Crea nuovo store se non esiste
            vs = self.client.vector_stores.create(name="DOCS-Default-Store")
            return vs.id
        except Exception as e:
            print(f"Errore nella gestione vector store: {e}")
            # Fallback: usa un ID fittizio per ora
            return "docs-default-store"

    def upload_file(self, file_path: str) -> str:
        """
        Carica un file nel vector store
        
        Args:
            file_path: Percorso del file da caricare
            
        Returns:
            openai_file_id: ID del file caricato
        """
        try:
            # Carica file nel vector store
            file_obj = self.client.vector_stores.files.upload(
                vector_store_id=self.vector_store_id,
                file={"path": file_path}
            )
            return file_obj.id  # openai_file_id
        except Exception as e:
            print(f"Errore nell'upload del file {file_path}: {e}")
            raise

    def qa(self, query: str) -> str:
        """
        Esegue una query con file search e restituisce risposta con citazioni
        
        Args:
            query: Domanda dell'utente
            
        Returns:
            Risposta con citazioni dai file
        """
        try:
            # Risposta con tool file_search + citazioni
            resp = self.client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                tools=[{"type": "file_search"}],
                attachments=[{"vector_store_id": self.vector_store_id}],
                input=(
                    "Rispondi usando SOLO i file allegati. "
                    "Alla fine inserisci citazioni con brevi estratti «…» e nome file.\n"
                    f"Domanda: {query}"
                ),
            )
            return getattr(resp, "output_text", None) or str(resp)
        except Exception as e:
            print(f"Errore nella query QA: {e}")
            return f"Errore durante l'elaborazione della domanda: {e}"
