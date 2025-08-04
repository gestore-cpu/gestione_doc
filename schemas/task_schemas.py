"""
Schemi per validazione dati TaskAI - Prompt 26 FASE 2
Implementazione degli schemi per validazione e serializzazione dei dati TaskAI.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from models import PrioritaTask, OrigineTask


@dataclass
class TaskAICreate:
    """
    Schema per creazione di un nuovo task AI.
    """
    titolo: str
    descrizione: Optional[str] = None
    data_scadenza: Optional[datetime] = None
    priorita: Optional[str] = "Medium"
    origine: Optional[str] = "Manuale"
    
    def __post_init__(self):
        """Validazione dopo l'inizializzazione."""
        if not self.titolo or not self.titolo.strip():
            raise ValueError("Titolo del task è obbligatorio")
        
        # Validazione priorità
        if self.priorita and self.priorita not in [p.value for p in PrioritaTask]:
            raise ValueError(f"Priorità non valida. Valori ammessi: {[p.value for p in PrioritaTask]}")
        
        # Validazione origine
        if self.origine and self.origine not in [o.value for o in OrigineTask]:
            raise ValueError(f"Origine non valida. Valori ammessi: {[o.value for o in OrigineTask]}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte lo schema in dizionario."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskAICreate':
        """Crea un'istanza da dizionario."""
        return cls(**data)


@dataclass
class TaskAIUpdate:
    """
    Schema per aggiornamento di un task AI esistente.
    """
    titolo: Optional[str] = None
    descrizione: Optional[str] = None
    data_scadenza: Optional[datetime] = None
    priorita: Optional[str] = None
    origine: Optional[str] = None
    stato: Optional[bool] = None
    
    def __post_init__(self):
        """Validazione dopo l'inizializzazione."""
        # Validazione priorità
        if self.priorita and self.priorita not in [p.value for p in PrioritaTask]:
            raise ValueError(f"Priorità non valida. Valori ammessi: {[p.value for p in PrioritaTask]}")
        
        # Validazione origine
        if self.origine and self.origine not in [o.value for o in OrigineTask]:
            raise ValueError(f"Origine non valida. Valori ammessi: {[o.value for o in OrigineTask]}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte lo schema in dizionario, escludendo i valori None."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskAIUpdate':
        """Crea un'istanza da dizionario."""
        return cls(**data)


@dataclass
class TaskAIRead:
    """
    Schema per lettura di un task AI.
    """
    id: int
    titolo: str
    descrizione: Optional[str]
    data_scadenza: Optional[datetime]
    priorita: str
    origine: str
    stato: bool
    data_creazione: datetime
    is_completed: bool
    is_overdue: bool
    days_until_deadline: Optional[int]
    priority_color: str
    status_color: str
    origine_badge_class: str
    origine_display: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte lo schema in dizionario."""
        result = asdict(self)
        # Converti datetime in stringhe ISO
        if result['data_scadenza']:
            result['data_scadenza'] = result['data_scadenza'].isoformat()
        if result['data_creazione']:
            result['data_creazione'] = result['data_creazione'].isoformat()
        return result
    
    @classmethod
    def from_task_ai(cls, task_ai) -> 'TaskAIRead':
        """Crea un'istanza da un oggetto TaskAI."""
        return cls(
            id=task_ai.id,
            titolo=task_ai.titolo,
            descrizione=task_ai.descrizione,
            data_scadenza=task_ai.data_scadenza,
            priorita=task_ai.priorita.value if task_ai.priorita else None,
            origine=task_ai.origine.value if task_ai.origine else None,
            stato=task_ai.stato,
            data_creazione=task_ai.data_creazione,
            is_completed=task_ai.is_completed,
            is_overdue=task_ai.is_overdue,
            days_until_deadline=task_ai.days_until_deadline,
            priority_color=task_ai.priority_color,
            status_color=task_ai.status_color,
            origine_badge_class=task_ai.origine_badge_class,
            origine_display=task_ai.origine_display
        )


@dataclass
class TaskAIFilter:
    """
    Schema per filtri avanzati sui task AI.
    """
    stato: Optional[bool] = None
    origine: Optional[str] = None
    priorita: Optional[str] = None
    scaduti: Optional[bool] = None
    search: Optional[str] = None
    sort_by: Optional[str] = "data_creazione"
    sort_order: Optional[str] = "desc"
    
    def __post_init__(self):
        """Validazione dopo l'inizializzazione."""
        # Validazione origine
        if self.origine and self.origine not in [o.value for o in OrigineTask]:
            raise ValueError(f"Origine non valida. Valori ammessi: {[o.value for o in OrigineTask]}")
        
        # Validazione priorità
        if self.priorita and self.priorita not in [p.value for p in PrioritaTask]:
            raise ValueError(f"Priorità non valida. Valori ammessi: {[p.value for p in PrioritaTask]}")
        
        # Validazione sort_by
        valid_sort_fields = ['data_creazione', 'data_scadenza', 'priorita', 'titolo']
        if self.sort_by and self.sort_by not in valid_sort_fields:
            raise ValueError(f"Campo ordinamento non valido. Valori ammessi: {valid_sort_fields}")
        
        # Validazione sort_order
        if self.sort_order and self.sort_order not in ['asc', 'desc']:
            raise ValueError("Ordine di ordinamento non valido. Valori ammessi: asc, desc")
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte lo schema in dizionario, escludendo i valori None."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskAIFilter':
        """Crea un'istanza da dizionario."""
        return cls(**data)


@dataclass
class TaskAIStats:
    """
    Schema per statistiche sui task AI.
    """
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    completion_rate: float
    origine_stats: Dict[str, Dict[str, int]]
    priority_stats: Dict[str, Dict[str, int]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte lo schema in dizionario."""
        return asdict(self)
    
    @classmethod
    def calculate_from_tasks(cls, tasks) -> 'TaskAIStats':
        """Calcola statistiche da una lista di task."""
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.is_completed])
        overdue_tasks = len([t for t in tasks if t.is_overdue])
        
        # Statistiche per origine
        origine_stats = {}
        for task in tasks:
            origine = task.origine.value
            if origine not in origine_stats:
                origine_stats[origine] = {'total': 0, 'completed': 0}
            origine_stats[origine]['total'] += 1
            if task.is_completed:
                origine_stats[origine]['completed'] += 1
        
        # Statistiche per priorità
        priority_stats = {}
        for task in tasks:
            priorita = task.priorita.value
            if priorita not in priority_stats:
                priority_stats[priorita] = {'total': 0, 'completed': 0}
            priority_stats[priorita]['total'] += 1
            if task.is_completed:
                priority_stats[priorita]['completed'] += 1
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return cls(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=total_tasks - completed_tasks,
            overdue_tasks=overdue_tasks,
            completion_rate=completion_rate,
            origine_stats=origine_stats,
            priority_stats=priority_stats
        )


# Funzioni di utilità per validazione
def validate_task_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida i dati di un task e restituisce i dati validati.
    
    Args:
        data: Dizionario con i dati del task
        
    Returns:
        Dizionario con i dati validati
        
    Raises:
        ValueError: Se i dati non sono validi
    """
    validated_data = {}
    
    # Validazione titolo
    if 'titolo' in data:
        titolo = data['titolo'].strip() if data['titolo'] else ''
        if not titolo:
            raise ValueError("Titolo del task è obbligatorio")
        validated_data['titolo'] = titolo
    
    # Validazione descrizione
    if 'descrizione' in data:
        validated_data['descrizione'] = data['descrizione'].strip() if data['descrizione'] else None
    
    # Validazione priorità
    if 'priorita' in data and data['priorita']:
        priorita = data['priorita']
        if priorita not in [p.value for p in PrioritaTask]:
            raise ValueError(f"Priorità non valida. Valori ammessi: {[p.value for p in PrioritaTask]}")
        validated_data['priorita'] = priorita
    
    # Validazione origine
    if 'origine' in data and data['origine']:
        origine = data['origine']
        if origine not in [o.value for o in OrigineTask]:
            raise ValueError(f"Origine non valida. Valori ammessi: {[o.value for o in OrigineTask]}")
        validated_data['origine'] = origine
    
    # Validazione stato
    if 'stato' in data:
        validated_data['stato'] = bool(data['stato'])
    
    # Validazione data scadenza
    if 'data_scadenza' in data:
        if data['data_scadenza']:
            try:
                if isinstance(data['data_scadenza'], str):
                    validated_data['data_scadenza'] = datetime.fromisoformat(data['data_scadenza'].replace('Z', '+00:00'))
                else:
                    validated_data['data_scadenza'] = data['data_scadenza']
            except ValueError:
                raise ValueError("Formato data scadenza non valido")
        else:
            validated_data['data_scadenza'] = None
    
    return validated_data


def serialize_task_ai(task_ai) -> Dict[str, Any]:
    """
    Serializza un oggetto TaskAI in dizionario per JSON.
    
    Args:
        task_ai: Oggetto TaskAI da serializzare
        
    Returns:
        Dizionario con i dati serializzati
    """
    return {
        'id': task_ai.id,
        'titolo': task_ai.titolo,
        'descrizione': task_ai.descrizione,
        'data_scadenza': task_ai.data_scadenza.isoformat() if task_ai.data_scadenza else None,
        'priorita': task_ai.priorita.value if task_ai.priorita else None,
        'origine': task_ai.origine.value if task_ai.origine else None,
        'stato': task_ai.stato,
        'data_creazione': task_ai.data_creazione.isoformat(),
        'is_completed': task_ai.is_completed,
        'is_overdue': task_ai.is_overdue,
        'days_until_deadline': task_ai.days_until_deadline,
        'priority_color': task_ai.priority_color,
        'status_color': task_ai.status_color,
        'origine_badge_class': task_ai.origine_badge_class,
        'origine_display': task_ai.origine_display
    } 