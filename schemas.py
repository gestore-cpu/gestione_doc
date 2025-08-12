"""
Schemi Pydantic per le API AI dei documenti.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class ReportAIResponse(BaseModel):
    """
    Schema per la risposta del report AI.
    """
    success: bool
    timestamp: str
    documenti_analizzati: int
    reparti_coinvolti: int
    report: str
    dati_bruti: List[Dict[str, Any]]
    statistiche: Dict[str, Any]


class StatisticheAIResponse(BaseModel):
    """
    Schema per le statistiche AI.
    """
    documenti_analizzati: int
    compliance_rate: float
    alert_critici: int
    reparti_virtuosi: int
    reparti_problematici: int
    documenti_prioritari: int
    raccomandazioni: int
    timestamp: str


class ReportCompletoAIResponse(BaseModel):
    """
    Schema per il report AI completo.
    """
    success: bool
    timestamp: str
    report: str


class DatiDocumentoAI(BaseModel):
    """
    Schema per i dati di un documento nell'analisi AI.
    """
    reparto: str
    documento: str
    uploader: str
    data_creazione: str
    versione_attuale: str
    versione_usata: str
    firme: int
    download: int
    letture: int
    ultima_firma: Optional[str]
    ultima_lettura: Optional[str]
    stato_compliance: str
    anomalie: List[str]
    anomalie_count: int


class AlertCriticoAI(BaseModel):
    """
    Schema per un alert critico dell'AI.
    """
    tipo: str
    documento: str
    reparto: str
    severita: str
    azione: str


class RepartoVirtuosoAI(BaseModel):
    """
    Schema per un reparto virtuoso dell'AI.
    """
    reparto: str
    compliance_rate: float
    documenti: int


class RepartoProblematicoAI(BaseModel):
    """
    Schema per un reparto problematico dell'AI.
    """
    reparto: str
    compliance_rate: float
    anomalie: int
    azione: str


class DocumentoPrioritarioAI(BaseModel):
    """
    Schema per un documento prioritario dell'AI.
    """
    documento: str
    reparto: str
    priorita: str
    anomalie: List[str]


class RaccomandazioneAI(BaseModel):
    """
    Schema per una raccomandazione dell'AI.
    """
    tipo: str
    descrizione: str
    azione: str


class AnalisiAutomaticaAI(BaseModel):
    """
    Schema per l'analisi automatica dell'AI.
    """
    alert_critici: List[AlertCriticoAI]
    raccomandazioni: List[RaccomandazioneAI]
    reparti_virtuosi: List[RepartoVirtuosoAI]
    reparti_problematici: List[RepartoProblematicoAI]
    documenti_prioritari: List[DocumentoPrioritarioAI]


class StatisticheGeneraliAI(BaseModel):
    """
    Schema per le statistiche generali dell'AI.
    """
    total_documenti: int
    total_reparti: int
    compliant: int
    in_attesa: int
    non_utilizzati: int
    anomalie_totali: int
    compliance_rate_generale: float


class RisultatoAnalisiAI(BaseModel):
    """
    Schema per il risultato completo dell'analisi AI.
    """
    success: bool
    timestamp: str
    documenti_analizzati: int
    prompt_ai: str
    statistiche_ai: StatisticheGeneraliAI
    analisi_automatica: AnalisiAutomaticaAI
    dati_bruti: List[DatiDocumentoAI]
