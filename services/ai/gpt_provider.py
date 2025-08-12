import os
import json
import time
import random
from typing import Any, Dict, Optional
from openai import OpenAI

_DEFAULT_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "30"))
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_CLIENT = None

def _client():
    """Ritorna il client OpenAI riutilizzabile."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _CLIENT

def _with_retry(fn, max_attempts=3):
    """Esegue una funzione con retry e backoff progressivo."""
    for attempt in range(1, max_attempts + 2):  # 5 tentativi soft
        try:
            return fn()
        except Exception as e:
            if attempt >= max_attempts + 2:
                raise
            # backoff progressivo + jitter
            time.sleep(1.2 * attempt + random.random())

class GptProvider:
    def __init__(self, model: Optional[str] = None):
        self.model = model or DEFAULT_MODEL

    def _parse_structured(self, resp):
        """
        Tenta prima l'output strutturato (Structured Outputs), poi il testo.
        Nota: le versioni SDK possono cambiare: se output_parsed non esiste,
        fai fallback a output_text / dict walk.
        """
        parsed = getattr(resp, "output_parsed", None)
        if parsed:
            return parsed
        text = getattr(resp, "output_text", None)
        if text:
            return json.loads(text)
        # Fallback ultra-sicuro
        data = resp.to_dict()
        try:
            # pesca il primo chunk testuale
            choices = data.get("output", []) or data.get("choices", [])
            if choices:
                content = choices[0].get("content", [])
                for part in content:
                    if part.get("type") in ("output_text", "text"):
                        return json.loads(part.get("text", "{}"))
        except Exception:
            pass
        raise RuntimeError("Impossibile estrarre JSON strutturato dalla risposta")

    def tag(self, text: str) -> Dict[str, Any]:
        """
        Tagga un documento con metadati strutturati.
        
        Args:
            text (str): Testo del documento da taggare
            
        Returns:
            Dict[str, Any]: Metadati strutturati del documento
        """
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "azienda": {"type": "string"},
                "reparto": {"type": "string"},
                "tipologia": {"type": "string", "description": "es. Fattura, Verbale Audit, DDT, Contratto, Policy, Altro"},
                "sensibilita": {"type": "string", "enum": ["pubblico","interno","riservato","personale/GDPR"]},
                "scadenze": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "data": {"type": "string", "format": "date"},
                            "descrizione": {"type": "string"}
                        },
                        "required": ["data","descrizione"]
                    }
                }
            },
            "required": ["tipologia","sensibilita"]
        }
        
        resp = _with_retry(lambda: _client().responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": [{"type":"text","text":
                    "Sei un assistente che produce SOLO JSON valido aderente allo schema. "
                    "Se un campo non è deducibile, restituisci stringa vuota o lista vuota."
                }]},
                {"role": "user", "content": [{"type": "text", "text": text[:12000]}]}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "DocTags", "schema": schema, "strict": True}
            },
            timeout=_DEFAULT_TIMEOUT
        ))
        return self._parse_structured(resp)  # JSON conforme allo schema  ✅

    def summarize(self, text: str, max_words: int = 120) -> str:
        """
        Genera un riassunto del documento.
        
        Args:
            text (str): Testo del documento da riassumere
            max_words (int): Numero massimo di parole per il riassunto
            
        Returns:
            str: Riassunto del documento
        """
        resp = _with_retry(lambda: _client().responses.create(
            model=self.model,
            input=f"Riassumi in massimo {max_words} parole, tono neutro:\n\n{text[:12000]}",
            timeout=_DEFAULT_TIMEOUT
        ))
        # fallback solo testo
        return getattr(resp, "output_text", None) or resp.to_dict()

    def explain_alert(self, context: str) -> str:
        """
        Spiega un download alert con contesto e azioni consigliate.
        
        Args:
            context (str): Contesto dell'alert
            
        Returns:
            str: Spiegazione e azioni consigliate
        """
        prompt = (
            "Sei un analista sicurezza. Fornisci una spiegazione breve (max 160 parole) "
            "del perché questo download alert è sospetto o meno, con 3 azioni consigliate. "
            "Usa bullet point e tono professionale.\n\n"
            "[CONTESTO]\n" + context
        )
        resp = _with_retry(lambda: _client().responses.create(
            model=self.model,
            input=prompt,
            timeout=_DEFAULT_TIMEOUT
        ))
        return getattr(resp, "output_text", None) or str(resp)

    def extract(self, text: str, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estrae informazioni strutturate dal documento secondo uno schema JSON.
        
        Args:
            text (str): Testo del documento
            json_schema (Dict[str, Any]): Schema JSON per l'estrazione
            
        Returns:
            Dict[str, Any]: Dati estratti secondo lo schema
        """
        resp = _with_retry(lambda: _client().responses.create(
            model=self.model,
            input=[
                {"role":"system","content":[{"type":"text","text":
                    "Produci SOLO JSON valido che aderisca allo schema."
                }]},
                {"role":"user","content":[{"type":"text","text": text[:12000]}]}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "CustomExtract", "schema": json_schema, "strict": True}
            },
            timeout=_DEFAULT_TIMEOUT
        ))
        return self._parse_structured(resp)

    def qa(self, context: str, question: str) -> str:
        """
        Risponde a una domanda basandosi sul contesto fornito.
        
        Args:
            context (str): Contesto del documento
            question (str): Domanda da porre
            
        Returns:
            str: Risposta alla domanda
        """
        prompt = (
            "Rispondi SOLO usando il contesto seguente. Se la risposta non è nel contesto, di': "
            "'Non presente nei documenti'. Aggiungi citazioni con brevi estratti tra «». "
            f"\n\n[CONTESTO]\n{context[:12000]}\n\n[DOMANDA]\n{question}"
        )
        resp = _with_retry(lambda: _client().responses.create(
            model=self.model, 
            input=prompt,
            timeout=_DEFAULT_TIMEOUT
        ))
        return getattr(resp, "output_text", None) or resp.to_dict()
