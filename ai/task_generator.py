"""
Modulo per la generazione automatica di task basati sugli insight AI.

Questo modulo si occupa di:
- Generare task automatici per documenti obsoleti/duplicati
- Assegnare priorità e scadenze appropriate
- Collegare task ai moduli FocusMe AI e QMS
- Gestire la logica di routing dei task
"""

from datetime import datetime, timedelta
from flask import url_for
from models import Task, Document, User, db
from extensions import db
import logging

logger = logging.getLogger(__name__)

def genera_task_ai(document, tipo_insight, insight_id=None, modulo_destinazione="FocusMe"):
    """
    Genera un task automatico basato su un insight AI.
    
    Args:
        document (Document): Il documento che ha generato l'insight
        tipo_insight (str): Tipo di insight (obsoleto, duplicato, vecchio, inutilizzato)
        insight_id (int, optional): ID dell'insight che ha generato il task
        modulo_destinazione (str): Modulo di destinazione (FocusMe, QMS)
    
    Returns:
        Task: Il task generato
    """
    try:
        # Determina priorità e scadenza in base al tipo
        priorita, scadenza = _determina_priorita_scadenza(tipo_insight)
        
        # Genera titolo e descrizione
        titolo = _genera_titolo_task(document, tipo_insight)
        descrizione = _genera_descrizione_task(document, tipo_insight)
        
        # Determina assegnatario
        assegnato_a = _determina_assegnatario(document, tipo_insight)
        
        # Genera link al documento
        link_documento = url_for("docs.view_document", document_id=document.id, _external=True)
        
        # Crea il task
        task = Task(
            titolo=titolo,
            descrizione=descrizione,
            priorita=priorita,
            assegnato_a=assegnato_a,
            scadenza=scadenza,
            created_by="AI System",
            insight_id=insight_id
        )
        
        # Aggiungi informazioni aggiuntive nella descrizione
        task.descrizione += f"\n\n📄 Documento: {document.title}"
        task.descrizione += f"\n🔗 Link: {link_documento}"
        task.descrizione += f"\n🏢 Azienda: {document.company.name if document.company else 'N/A'}"
        task.descrizione += f"\n📁 Reparto: {document.department.name if document.department else 'N/A'}"
        task.descrizione += f"\n📅 Data creazione: {document.created_at.strftime('%d/%m/%Y')}"
        
        if document.expiry_date:
            task.descrizione += f"\n⏰ Scadenza: {document.expiry_date.strftime('%d/%m/%Y')}"
        
        # Salva nel database
        db.session.add(task)
        db.session.commit()
        
        logger.info(f"✅ Task AI generato: {task.titolo} (ID: {task.id})")
        return task
        
    except Exception as e:
        logger.error(f"❌ Errore generazione task AI: {e}")
        db.session.rollback()
        raise

def _determina_priorita_scadenza(tipo_insight):
    """
    Determina priorità e scadenza in base al tipo di insight.
    
    Args:
        tipo_insight (str): Tipo di insight
    
    Returns:
        tuple: (priorita, scadenza)
    """
    oggi = datetime.utcnow()
    
    if tipo_insight == "obsoleto":
        return "Critica", oggi + timedelta(days=3)
    elif tipo_insight == "duplicato":
        return "Alta", oggi + timedelta(days=7)
    elif tipo_insight == "vecchio":
        return "Media", oggi + timedelta(days=14)
    elif tipo_insight == "inutilizzato":
        return "Bassa", oggi + timedelta(days=30)
    else:
        return "Media", oggi + timedelta(days=7)

def _genera_titolo_task(document, tipo_insight):
    """
    Genera un titolo appropriato per il task.
    
    Args:
        document (Document): Il documento
        tipo_insight (str): Tipo di insight
    
    Returns:
        str: Titolo del task
    """
    mappatura_titoli = {
        "obsoleto": f"⚠️ Revisione urgente: {document.title}",
        "duplicato": f"🔄 Verifica duplicato: {document.title}",
        "vecchio": f"📅 Aggiornamento consigliato: {document.title}",
        "inutilizzato": f"📊 Analisi utilizzo: {document.title}"
    }
    
    return mappatura_titoli.get(tipo_insight, f"Revisione: {document.title}")

def _genera_descrizione_task(document, tipo_insight):
    """
    Genera una descrizione dettagliata per il task.
    
    Args:
        document (Document): Il documento
        tipo_insight (str): Tipo di insight
    
    Returns:
        str: Descrizione del task
    """
    descrizioni = {
        "obsoleto": f"Il documento '{document.title}' è stato identificato come obsoleto dall'AI. "
                    f"È necessario un aggiornamento immediato per mantenere la conformità.",
        "duplicato": f"Il documento '{document.title}' presenta una similarità elevata con altri documenti. "
                    f"Verificare se è necessario mantenere entrambe le versioni o consolidare.",
        "vecchio": f"Il documento '{document.title}' è stato creato più di un anno fa. "
                    f"Si consiglia una revisione per verificare l'attualità dei contenuti.",
        "inutilizzato": f"Il documento '{document.title}' non è stato accesso negli ultimi 6 mesi. "
                        f"Valutare se è ancora necessario o se può essere archiviato."
    }
    
    return descrizioni.get(tipo_insight, f"Revisione richiesta per il documento '{document.title}'.")

def _determina_assegnatario(document, tipo_insight):
    """
    Determina l'assegnatario del task in base al documento e al tipo di insight.
    
    Args:
        document (Document): Il documento
        tipo_insight (str): Tipo di insight
    
    Returns:
        str: Email dell'assegnatario
    """
    # Prova a trovare il responsabile del documento
    if document.uploader_email:
        return document.uploader_email
    
    # Se non c'è un uploader, cerca un admin
    admin = User.query.filter_by(role='admin').first()
    if admin:
        return admin.email
    
    # Fallback
    return "admin@mercurysurgelati.org"

def genera_task_qms(document, tipo_insight, insight_id=None):
    """
    Genera un task specifico per il modulo QMS.
    
    Args:
        document (Document): Il documento
        tipo_insight (str): Tipo di insight
        insight_id (int, optional): ID dell'insight
    
    Returns:
        Task: Il task generato
    """
    # Per QMS, aggiungi informazioni specifiche di processo
    task = genera_task_ai(document, tipo_insight, insight_id, "QMS")
    
    # Aggiungi informazioni QMS specifiche
    task.descrizione += "\n\n🏭 MODULO QMS"
    task.descrizione += "\n📋 Questo task è stato generato automaticamente dal sistema QMS."
    task.descrizione += "\n🔍 Verificare la conformità ai processi aziendali."
    
    return task

def genera_task_focusme(document, tipo_insight, insight_id=None):
    """
    Genera un task specifico per il modulo FocusMe AI.
    
    Args:
        document (Document): Il documento
        tipo_insight (str): Tipo di insight
        insight_id (int, optional): ID dell'insight
    
    Returns:
        Task: Il task generato
    """
    # Per FocusMe, aggiungi informazioni strategiche
    task = genera_task_ai(document, tipo_insight, insight_id, "FocusMe")
    
    # Aggiungi informazioni FocusMe specifiche
    task.descrizione += "\n\n🧠 MODULO FOCUSME AI"
    task.descrizione += "\n📊 Questo task è stato generato automaticamente dal sistema FocusMe AI."
    task.descrizione += "\n🎯 Valutare l'impatto strategico e le opportunità di miglioramento."
    
    return task

def determina_modulo_destinazione(document, tipo_insight):
    """
    Determina il modulo di destinazione in base al documento e al tipo di insight.
    
    Args:
        document (Document): Il documento
        tipo_insight (str): Tipo di insight
    
    Returns:
        str: Modulo di destinazione (QMS o FocusMe)
    """
    # Documenti di processo e certificazione → QMS
    if document.company and document.company.name.lower() in ['processo', 'certificazione', 'qualità']:
        return "QMS"
    
    # Documenti strategici e gestionali → FocusMe
    if document.title.lower() in ['strategia', 'piano', 'obiettivo', 'kpi', 'dashboard']:
        return "FocusMe"
    
    # Per tipo di insight
    if tipo_insight in ["obsoleto", "duplicato"]:
        return "QMS"  # Problemi critici → QMS
    else:
        return "FocusMe"  # Analisi strategica → FocusMe

def genera_task_intelligente(document, tipo_insight, insight_id=None):
    """
    Genera un task con routing intelligente tra QMS e FocusMe.
    
    Args:
        document (Document): Il documento
        tipo_insight (str): Tipo di insight
        insight_id (int, optional): ID dell'insight
    
    Returns:
        Task: Il task generato
    """
    modulo = determina_modulo_destinazione(document, tipo_insight)
    
    if modulo == "QMS":
        return genera_task_qms(document, tipo_insight, insight_id)
    else:
        return genera_task_focusme(document, tipo_insight, insight_id)

def aggiorna_task_esistente(task_id, nuovo_stato, note=None):
    """
    Aggiorna un task esistente.
    
    Args:
        task_id (int): ID del task
        nuovo_stato (str): Nuovo stato
        note (str, optional): Note aggiuntive
    
    Returns:
        Task: Il task aggiornato
    """
    try:
        task = Task.query.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} non trovato")
        
        task.stato = nuovo_stato
        
        if nuovo_stato == "Completato":
            task.completed_at = datetime.utcnow()
        
        if note:
            task.descrizione += f"\n\n📝 Note aggiuntive: {note}"
        
        db.session.commit()
        logger.info(f"✅ Task {task_id} aggiornato: {nuovo_stato}")
        return task
        
    except Exception as e:
        logger.error(f"❌ Errore aggiornamento task {task_id}: {e}")
        db.session.rollback()
        raise

def pulisci_task_obsoleti(giorni=30):
    """
    Pulisce i task obsoleti più vecchi di N giorni.
    
    Args:
        giorni (int): Numero di giorni per considerare un task obsoleto
    
    Returns:
        int: Numero di task eliminati
    """
    try:
        data_limite = datetime.utcnow() - timedelta(days=giorni)
        
        # Trova task completati o annullati più vecchi di N giorni
        task_obsoleti = Task.query.filter(
            Task.stato.in_(['Completato', 'Annullato']),
            Task.created_at < data_limite
        ).all()
        
        count = len(task_obsoleti)
        
        for task in task_obsoleti:
            db.session.delete(task)
        
        db.session.commit()
        logger.info(f"✅ Eliminati {count} task obsoleti")
        return count
        
    except Exception as e:
        logger.error(f"❌ Errore pulizia task obsoleti: {e}")
        db.session.rollback()
        raise 