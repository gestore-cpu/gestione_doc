"""
Task per gestione alert AI documenti abbandonati.
Rileva documenti che hanno saltato 2 revisioni consecutive.
"""

import logging
from datetime import datetime, timedelta
from flask import current_app

logger = logging.getLogger(__name__)

def verifica_documenti_abbandonati():
    """
    Verifica documenti che hanno saltato 2 revisioni consecutive.
    Genera alert AI e task di recupero.
    """
    try:
        from app import app
        from models import Document
        
        with app.app_context():
            # Ottieni documenti con frequenza revisione
            documenti = Document.query.filter(
                Document.frequenza_revisione.isnot(None),
                Document.data_ultima_revisione.isnot(None)
            ).all()
            
            documenti_abbandonati = []
            
            for doc in documenti:
                if documento_ha_saltato_due_revisioni(doc):
                    documenti_abbandonati.append(doc)
                    genera_alert_salto_revisioni(doc)
            
            if documenti_abbandonati:
                logger.info(f"⚠️ Trovati {len(documenti_abbandonati)} documenti abbandonati")
                
                # Log dettagliato per audit
                for doc in documenti_abbandonati:
                    giorni_ritardo = (datetime.today().date() - doc.data_ultima_revisione).days
                    logger.warning(
                        f"📋 Documento abbandonato: {doc.title or doc.original_filename} "
                        f"(ID: {doc.id}) - Ultima revisione: {doc.data_ultima_revisione} "
                        f"- Ritardo: {giorni_ritardo} giorni"
                    )
            else:
                logger.info("✅ Nessun documento abbandonato trovato")
                
    except Exception as e:
        logger.error(f"❌ Errore verifica documenti abbandonati: {e}")

def documento_ha_saltato_due_revisioni(doc):
    """
    Verifica se un documento ha saltato 2 revisioni consecutive.
    
    Args:
        doc: Document object
        
    Returns:
        bool: True se ha saltato 2 revisioni, False altrimenti
    """
    if not doc.frequenza_revisione or not doc.data_ultima_revisione:
        return False

    frequenze = {
        "annuale": 365,
        "biennale": 730,
        "mensile": 30,
        "trimestrale": 90,
        "semestrale": 180
    }
    
    giorni_attesi = frequenze.get(doc.frequenza_revisione, 0)
    if giorni_attesi == 0:
        return False

    # Calcola giorni passati dall'ultima revisione
    oggi = datetime.today().date()
    giorni_passati = (oggi - doc.data_ultima_revisione).days
    
    # Verifica se sono passati almeno 2 cicli completi
    return giorni_passati >= 2 * giorni_attesi

def genera_alert_salto_revisioni(doc):
    """
    Genera alert AI per documento che ha saltato 2 revisioni consecutive.
    
    Args:
        doc: Document object
    """
    # Calcola giorni di ritardo
    oggi = datetime.today().date()
    giorni_ritardo = (oggi - doc.data_ultima_revisione).days
    
    # Prepara messaggio alert
    titolo = f"❗ Documento NON revisionato da oltre 2 cicli: {doc.title or doc.original_filename}"
    descrizione = (
        f"⚠️ Documento '{doc.title or doc.original_filename}' non revisionato da oltre 2 cicli di tipo: "
        f"{doc.frequenza_revisione}. Ultima revisione: {doc.data_ultima_revisione.strftime('%d/%m/%Y')}.\n"
        f"Giorni di ritardo: {giorni_ritardo} giorni.\n"
        f"Verifica obbligatoria ai fini compliance."
    )
    
    try:
        from app import db
        from models import Task, Notification
        
        # Crea notifica AI
        notifica = Notification(
            title=titolo,
            message=descrizione,
            level="critical",
            module="DOCS",
            link=f"/admin/docs/{doc.id}/versions",
            user_id=None,  # Notifica globale
            created_at=datetime.utcnow()
        )
        
        db.session.add(notifica)
        db.session.commit()
        logger.info(f"✅ Alert AI generato per documento {doc.id}: {titolo}")
        
        # Crea task AI se mancante
        if not doc.ai_task_id:
            task = Task(
                title=f"Recupero revisione documento – {doc.title or doc.original_filename}",
                description=descrizione,
                priority="alta",
                tipo="revisione_fallita",
                linked_document_id=doc.id,
                assigned_to=None,  # Assegnato automaticamente
                created_at=datetime.utcnow(),
                status="pending"
            )
            
            db.session.add(task)
            db.session.commit()
            
            # Aggiorna documento con task ID
            doc.ai_task_id = task.id
            db.session.commit()
            
            logger.info(f"✅ Task AI creato per recupero documento {doc.id}: {task.title}")
            
    except Exception as e:
        logger.error(f"❌ Errore creazione alert AI per documento {doc.id}: {e}")

def get_documenti_abbandonati():
    """
    Ottiene la lista dei documenti abbandonati per la dashboard.
    
    Returns:
        list: Lista di documenti abbandonati
    """
    try:
        from models import Document
        
        documenti = Document.query.filter(
            Document.frequenza_revisione.isnot(None),
            Document.data_ultima_revisione.isnot(None)
        ).all()
        
        documenti_abbandonati = []
        
        for doc in documenti:
            if documento_ha_saltato_due_revisioni(doc):
                giorni_ritardo = (datetime.today().date() - doc.data_ultima_revisione).days
                doc.giorni_ritardo = giorni_ritardo
                documenti_abbandonati.append(doc)
        
        # Ordina per giorni di ritardo (più critici prima)
        documenti_abbandonati.sort(key=lambda x: x.giorni_ritardo, reverse=True)
        
        return documenti_abbandonati
        
    except Exception as e:
        logger.error(f"❌ Errore ottenimento documenti abbandonati: {e}")
        return []

def get_statistiche_abbandonati():
    """
    Ottiene statistiche sui documenti abbandonati.
    
    Returns:
        dict: Statistiche documenti abbandonati
    """
    try:
        documenti_abbandonati = get_documenti_abbandonati()
        
        # Raggruppa per frequenza revisione
        per_frequenza = {}
        for doc in documenti_abbandonati:
            freq = doc.frequenza_revisione
            if freq not in per_frequenza:
                per_frequenza[freq] = []
            per_frequenza[freq].append(doc)
        
        # Calcola statistiche
        stats = {
            "totali": len(documenti_abbandonati),
            "per_frequenza": per_frequenza,
            "piu_critici": documenti_abbandonati[:5] if documenti_abbandonati else [],
            "media_ritardo": sum(doc.giorni_ritardo for doc in documenti_abbandonati) / len(documenti_abbandonati) if documenti_abbandonati else 0
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Errore calcolo statistiche abbandonati: {e}")
        return {
            "totali": 0,
            "per_frequenza": {},
            "piu_critici": [],
            "media_ritardo": 0
        } 