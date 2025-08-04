#!/usr/bin/env python3
"""
Task per revisione ciclica automatica dei documenti.
Gestisce la programmazione e notifica delle revisioni periodiche.
"""

from datetime import datetime, timedelta
from flask import current_app
import logging

# Configurazione logging
logger = logging.getLogger(__name__)

def verifica_revisioni_programmate():
    """
    Verifica documenti che necessitano revisione periodica.
    """
    try:
        from app import app, db
        from models import Document, User
        
        with app.app_context():
            today = datetime.today().date()
            
            # Documenti con frequenza di revisione
            documents = Document.query.filter(
                Document.frequenza_revisione.isnot(None)
            ).all()
            
            logger.info(f"🔍 Verificando {len(documents)} documenti per revisione")
            
            for doc in documents:
                try:
                    # Calcola prossima revisione
                    next_due = doc.calcola_prossima_revisione()
                    
                    if next_due and next_due <= today:
                        logger.info(f"📅 Documento {doc.id} scaduto per revisione: {doc.title}")
                        
                        # Crea task AI per revisione
                        task = crea_task_revisione_ai(doc)
                        
                        if task:
                            # Invia notifiche
                            invia_notifica_revisione(doc, task)
                            
                            # Aggiorna documento con task
                            doc.revisione_task_id = task.id
                            db.session.commit()
                            
                            logger.info(f"✅ Task revisione creato per documento {doc.id}")
                        else:
                            logger.error(f"❌ Errore creazione task per documento {doc.id}")
                    
                except Exception as e:
                    logger.error(f"❌ Errore verifica revisione documento {doc.id}: {e}")
                    continue
            
    except Exception as e:
        logger.error(f"❌ Errore generale verifica revisioni: {e}")

def crea_task_revisione_ai(doc):
    """
    Crea un task AI per la revisione di un documento.
    
    Args:
        doc (Document): Documento da revisionare
        
    Returns:
        Task or None: Task creato o None in caso di errore
    """
    try:
        from app import db
        from models import Task
        
        # Prepara titolo e descrizione
        titolo = f"🔄 Revisione periodica – {doc.title}"
        
        descrizione = f"""
🕒 REVISIONE PERIODICA DOCUMENTO

📄 Documento: {doc.title}
🏢 Azienda: {doc.company.name if doc.company else 'N/A'}
🏭 Reparto: {doc.department.name if doc.department else 'N/A'}
📅 Ultima revisione: {doc.data_ultima_revisione.strftime('%d/%m/%Y') if doc.data_ultima_revisione else 'Non specificata'}
🔄 Frequenza: {doc.frequenza_revisione}
📅 Prossima scadenza: {doc.calcola_prossima_revisione().strftime('%d/%m/%Y') if doc.calcola_prossima_revisione() else 'Non calcolata'}

📋 AZIONI RICHIESTE:
1. Verificare contenuto e validità del documento
2. Aggiornare se necessario
3. Confermare revisione completata
4. Aggiornare data ultima revisione

🔗 Link documento: /admin/docs/{doc.id}

---
Generato automaticamente dal sistema di revisione ciclica
{datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
        
        # Crea task
        task = Task(
            title=titolo,
            description=descrizione.strip(),
            priority="media",
            status="pending",
            tipo="revisione",
            linked_document_id=doc.id,
            created_by=1,  # Sistema
            assigned_to=None,  # Assegnato automaticamente ai responsabili
            due_date=datetime.now() + timedelta(days=30)  # Scadenza 30 giorni
        )
        
        db.session.add(task)
        db.session.commit()
        
        logger.info(f"✅ Task revisione creato: {task.id}")
        return task
        
    except Exception as e:
        logger.error(f"❌ Errore creazione task revisione: {e}")
        return None

def invia_notifica_revisione(doc, task):
    """
    Invia notifiche per revisione documentale.
    
    Args:
        doc (Document): Documento da revisionare
        task (Task): Task di revisione creato
    """
    try:
        from tasks.reminder_tasks import get_responsabili_documento, send_email_reminder
        
        # Ottieni responsabili
        responsabili = get_responsabili_documento(doc)
        
        if not responsabili:
            logger.warning(f"⚠️ Nessun responsabile trovato per documento {doc.id}")
            return
        
        # Prepara messaggio
        subject = f"🔄 Revisione periodica richiesta – {doc.title}"
        
        message = f"""
🔄 REVISIONE PERIODICA DOCUMENTO

📄 Documento: {doc.title}
🏢 Azienda: {doc.company.name if doc.company else 'N/A'}
🏭 Reparto: {doc.department.name if doc.department else 'N/A'}

📅 Ultima revisione: {doc.data_ultima_revisione.strftime('%d/%m/%Y') if doc.data_ultima_revisione else 'Non specificata'}
🔄 Frequenza: {doc.frequenza_revisione}
📅 Prossima scadenza: {doc.calcola_prossima_revisione().strftime('%d/%m/%Y') if doc.calcola_prossima_revisione() else 'Non calcolata'}

📌 Task AI generato: #{task.id}
🔗 Link documento: /admin/docs/{doc.id}

📋 AZIONI RICHIESTE:
1. Verificare contenuto e validità del documento
2. Aggiornare se necessario
3. Confermare revisione completata
4. Aggiornare data ultima revisione

⚠️ IMPORTANTE: La revisione è necessaria per mantenere la compliance documentale.

---
Mercury Document Intelligence
Sistema di Revisione Ciclica Automatica
{datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
        
        # Invia a tutti i responsabili
        for user in responsabili:
            try:
                if user.reminder_email:
                    send_email_reminder(user.email, subject, message)
                    logger.info(f"✅ Notifica revisione inviata a {user.email}")
                
                # TODO: Implementare WhatsApp per revisioni
                if user.reminder_whatsapp and user.phone:
                    logger.info(f"📱 WhatsApp revisione per {user.phone}")
                    
            except Exception as e:
                logger.error(f"❌ Errore invio notifica revisione a {user.email}: {e}")
        
    except Exception as e:
        logger.error(f"❌ Errore invio notifiche revisione: {e}")

def aggiorna_revisione_completata(doc_id, user_id):
    """
    Aggiorna la data di revisione quando completata.
    
    Args:
        doc_id (int): ID del documento
        user_id (int): ID dell'utente che ha completato la revisione
        
    Returns:
        bool: True se aggiornamento riuscito
    """
    try:
        from app import app, db
        from models import Document, Task
        
        with app.app_context():
            doc = Document.query.get(doc_id)
            if not doc:
                logger.error(f"❌ Documento {doc_id} non trovato")
                return False
            
            # Aggiorna data revisione
            doc.aggiorna_revisione()
            
            # Chiudi task di revisione se presente
            if doc.revisione_task_id:
                task = Task.query.get(doc.revisione_task_id)
                if task:
                    task.status = "completed"
                    task.completed_by = user_id
                    task.completed_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"✅ Revisione completata per documento {doc_id}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Errore aggiornamento revisione: {e}")
        return False

def get_documenti_in_revisione():
    """
    Ottiene documenti che necessitano revisione.
    
    Returns:
        list: Lista documenti in revisione
    """
    try:
        from app import app
        from models import Document
        
        with app.app_context():
            today = datetime.today().date()
            
            # Documenti con frequenza di revisione
            documents = Document.query.filter(
                Document.frequenza_revisione.isnot(None)
            ).all()
            
            # Filtra quelli scaduti
            scaduti = []
            for doc in documents:
                next_due = doc.calcola_prossima_revisione()
                if next_due and next_due <= today:
                    scaduti.append(doc)
            
            return scaduti
            
    except Exception as e:
        logger.error(f"❌ Errore ottenimento documenti in revisione: {e}")
        return []

def get_statistiche_revisione():
    """
    Ottiene statistiche sulle revisioni documentali.
    
    Returns:
        dict: Statistiche revisione
    """
    try:
        from app import app
        from models import Document
        
        with app.app_context():
            today = datetime.today().date()
            
            # Tutti i documenti con frequenza
            totali = Document.query.filter(
                Document.frequenza_revisione.isnot(None)
            ).count()
            
            # Documenti in revisione (scaduti)
            in_revisione = len(get_documenti_in_revisione())
            
            # Documenti aggiornati (non scaduti)
            aggiornati = 0
            documents = Document.query.filter(
                Document.frequenza_revisione.isnot(None)
            ).all()
            
            for doc in documents:
                next_due = doc.calcola_prossima_revisione()
                if next_due and next_due > today:
                    aggiornati += 1
            
            return {
                "totali": totali,
                "in_revisione": in_revisione,
                "aggiornati": aggiornati,
                "percentuale_scaduti": (in_revisione / totali * 100) if totali > 0 else 0
            }
            
    except Exception as e:
        logger.error(f"❌ Errore calcolo statistiche revisione: {e}")
        return {
            "totali": 0,
            "in_revisione": 0,
            "aggiornati": 0,
            "percentuale_scaduti": 0
        } 