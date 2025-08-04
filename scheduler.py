"""
Scheduler per reminder automatici SYNTHIA DOCS.
Gestisce l'invio automatico di notifiche per scadenze documentali, visite mediche e checklist.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import current_app
from flask_mail import Message
from datetime import datetime, timedelta
import logging

# Import per reminder visite mediche
from app.reminder.visite import check_visite_scadenza

# Import per reminder documentali
from tasks.reminder_tasks import invia_promemoria_documenti

# Import per pulizia token firma
from services.security import cleanup_expired_tokens

# Import per revisione ciclica
from tasks.revision_tasks import verifica_revisioni_programmate

# Import per alert documenti abbandonati
from tasks.alert_tasks import verifica_documenti_abbandonati

# Import per monitoraggio AI download sospetti
from services.ai_monitoring import analizza_download_sospetti, create_ai_alert

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def invia_reminder_email(reminder, user):
    """
    Invia email di reminder per un utente specifico.
    
    Args:
        reminder: Istanza del modello Reminder
        user: Istanza del modello User
    
    Returns:
        bool: True se l'invio è riuscito, False altrimenti
    """
    try:
        from app import mail, db
        from models import ReminderLog
        
        # Prepara il messaggio
        subject = f"[SYNTHIA DOCS] ⚠️ Scadenza: {reminder.tipo_display}"
        
        # Calcola giorni alla scadenza
        giorni_alla_scadenza = reminder.giorni_alla_scadenza
        
        # Personalizza il messaggio in base al tipo
        if reminder.tipo == 'documento':
            body = f"""
Ciao {user.first_name or user.username},

🔔 RICHIAMO IMPORTANTE

Il documento "{reminder.messaggio}" scade tra {giorni_alla_scadenza} giorni.

📅 Scadenza: {reminder.scadenza.strftime('%d/%m/%Y')}
👤 Ruolo: {reminder.destinatario_ruolo.upper()}

⚠️ Azione richiesta:
- Verifica la validità del documento
- Aggiorna se necessario
- Carica nuova versione se scaduto

🔗 Accedi a SYNTHIA DOCS per gestire: https://docs.mercurysurgelati.org

---
SYNTHIA DOCS - Sistema di Gestione Documentale
Questo messaggio è stato generato automaticamente.
            """
        elif reminder.tipo == 'visita_medica':
            body = f"""
Ciao {user.first_name or user.username},

🏥 RICHIAMO VISITA MEDICA

La visita medica per {reminder.messaggio} scade tra {giorni_alla_scadenza} giorni.

📅 Scadenza: {reminder.scadenza.strftime('%d/%m/%Y')}
👤 Ruolo: {reminder.destinatario_ruolo.upper()}

⚠️ Azione richiesta:
- Prenota visita medica
- Carica certificato aggiornato
- Verifica idoneità

🔗 Accedi a SYNTHIA DOCS per gestire: https://docs.mercurysurgelati.org

---
SYNTHIA DOCS - Sistema di Gestione Documentale
Questo messaggio è stato generato automaticamente.
            """
        elif reminder.tipo == 'checklist':
            body = f"""
Ciao {user.first_name or user.username},

📋 RICHIAMO CHECKLIST COMPLIANCE

La checklist "{reminder.messaggio}" richiede attenzione.

📅 Scadenza: {reminder.scadenza.strftime('%d/%m/%Y')}
👤 Ruolo: {reminder.destinatario_ruolo.upper()}

⚠️ Azione richiesta:
- Completa voci checklist mancanti
- Verifica conformità standard
- Aggiorna stato compliance

🔗 Accedi a SYNTHIA DOCS per gestire: https://docs.mercurysurgelati.org

---
SYNTHIA DOCS - Sistema di Gestione Documentale
Questo messaggio è stato generato automaticamente.
            """
        else:
            body = f"""
Ciao {user.first_name or user.username},

🔔 RICHIAMO GENERICO

{reminder.messaggio}

📅 Scadenza: {reminder.scadenza.strftime('%d/%m/%Y')}
👤 Ruolo: {reminder.destinatario_ruolo.upper()}

⚠️ Azione richiesta:
- Verifica e aggiorna se necessario

🔗 Accedi a SYNTHIA DOCS per gestire: https://docs.mercurysurgelati.org

---
SYNTHIA DOCS - Sistema di Gestione Documentale
Questo messaggio è stato generato automaticamente.
            """
        
        # Crea e invia il messaggio
        msg = Message(
            subject=subject,
            recipients=[user.email],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@mercurysurgelati.org')
        )
        
        mail.send(msg)
        
        # Aggiorna stato reminder
        reminder.ultimo_invio = datetime.utcnow()
        reminder.stato = 'inviato'
        reminder.calcola_prossimo_invio()
        
        # Log invio riuscito
        log = ReminderLog(
            reminder_id=reminder.id,
            inviato_a=user.email,
            canale='email',
            messaggio=body,
            esito='success'
        )
        
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"Reminder inviato con successo a {user.email} per {reminder.tipo}")
        return True
        
    except Exception as e:
        # Log errore
        try:
            log = ReminderLog(
                reminder_id=reminder.id,
                inviato_a=user.email,
                canale='email',
                messaggio=str(e),
                esito='error',
                errore=str(e)
            )
            db.session.add(log)
            db.session.commit()
        except:
            pass
        
        logger.error(f"Errore invio reminder a {user.email}: {str(e)}")
        return False

def invia_reminder_interno(reminder, user):
    """
    Crea notifica interna nella dashboard (per implementazione futura).
    
    Args:
        reminder: Istanza del modello Reminder
        user: Istanza del modello User
    
    Returns:
        bool: True se la notifica è stata creata, False altrimenti
    """
    try:
        from models import Notification  # Da implementare
        
        # Per ora ritorna True (implementazione futura)
        logger.info(f"Notifica interna creata per {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Errore creazione notifica interna: {str(e)}")
        return False

def processa_reminder():
    """
    Funzione principale per processare tutti i reminder attivi.
    Viene eseguita dal scheduler ogni giorno alle 7:00.
    """
    try:
        from app import db
        from models import Reminder, User
        
        logger.info("Avvio processamento reminder automatici...")
        
        # Trova tutti i reminder attivi che devono essere inviati oggi
        oggi = datetime.utcnow().date()
        reminder_da_inviare = Reminder.query.filter(
            Reminder.stato == 'attivo',
            Reminder.prossimo_invio <= datetime.utcnow()
        ).all()
        
        logger.info(f"Trovati {len(reminder_da_inviare)} reminder da processare")
        
        for reminder in reminder_da_inviare:
            try:
                # Trova l'utente destinatario
                user = User.query.filter_by(email=reminder.destinatario_email).first()
                
                if not user:
                    logger.warning(f"Utente non trovato per email: {reminder.destinatario_email}")
                    continue
                
                # Invia reminder in base al canale
                success = False
                
                if reminder.canale in ['email', 'entrambi']:
                    success = invia_reminder_email(reminder, user)
                
                if reminder.canale in ['interno', 'entrambi']:
                    success_interno = invia_reminder_interno(reminder, user)
                    success = success or success_interno
                
                if success:
                    logger.info(f"Reminder {reminder.id} processato con successo")
                else:
                    logger.error(f"Errore nel processare reminder {reminder.id}")
                    
            except Exception as e:
                logger.error(f"Errore processando reminder {reminder.id}: {str(e)}")
                continue
        
        logger.info("Processamento reminder completato")
        
    except Exception as e:
        logger.error(f"Errore generale nel processamento reminder: {str(e)}")

def genera_reminder():
    """Genera automaticamente i reminder per scadenze."""
    from models import VisitaMedica, Document, ChecklistCompliance, Reminder, User, ProvaEvacuazione
    from datetime import date, timedelta
    
    oggi = date.today()
    in_30_giorni = oggi + timedelta(days=30)
    
    # 🩺 Visite Mediche in scadenza tra oggi e 30 giorni
    visite = VisitaMedica.query.filter(
        VisitaMedica.scadenza <= in_30_giorni
    ).all()
    
    for visita in visite:
        # Evita duplicati
        già_esiste = Reminder.query.filter_by(
            user_id=visita.user_id,
            tipo='Visita Medica',
            entita_id=visita.id,
            scadenza=visita.scadenza
        ).first()
        
        if già_esiste:
            continue
            
        nuovo = Reminder(
            user_id=visita.user_id,
            tipo='Visita Medica',
            entita_id=visita.id,
            entita_tipo='visita_medica',
            destinatario_email=visita.user.email,
            destinatario_ruolo=visita.user.role,
            scadenza=visita.scadenza,
            giorni_anticipo=30,
            messaggio=f"La tua visita medica ({visita.tipo_visita}) scadrà il {visita.scadenza}.",
            canale='email',
            created_by=1  # Sistema
        )
        db.session.add(nuovo)
    
    # 📄 Documenti con scadenza (campo 'scadenza')
    documenti = Document.query.filter(Document.scadenza <= in_30_giorni).all()
    for doc in documenti:
        for user in User.query.filter_by(role='hr').all():  # invia a HR
            già_esiste = Reminder.query.filter_by(
                user_id=user.id,
                tipo='Scadenza Documento',
                entita_id=doc.id,
                scadenza=doc.scadenza
            ).first()
            
            if già_esiste:
                continue
                
            nuovo = Reminder(
                user_id=user.id,
                tipo='Scadenza Documento',
                entita_id=doc.id,
                entita_tipo='documento',
                destinatario_email=user.email,
                destinatario_ruolo=user.role,
                scadenza=doc.scadenza,
                giorni_anticipo=30,
                messaggio=f"Il documento '{doc.nome}' scadrà il {doc.scadenza}.",
                canale='email',
                created_by=1  # Sistema
            )
            db.session.add(nuovo)
    
    # 📋 Checklist incomplete da più di 7 giorni
    cutoff = oggi - timedelta(days=7)
    checklist = ChecklistCompliance.query.filter_by(is_completa=False).all()
    for voce in checklist:
        if voce.completata_il or voce.created_at.date() > cutoff:
            continue
            
        doc = Document.query.get(voce.documento_id)
        for user in User.query.filter_by(role='auditor').all():
            già_esiste = Reminder.query.filter_by(
                user_id=user.id,
                tipo='Checklist Incompleta',
                entita_id=voce.id
            ).first()
            
            if già_esiste:
                continue
                
            nuovo = Reminder(
                user_id=user.id,
                tipo='Checklist Incompleta',
                entita_id=voce.id,
                entita_tipo='checklist',
                destinatario_email=user.email,
                destinatario_ruolo=user.role,
                scadenza=oggi,
                giorni_anticipo=7,
                messaggio=f"La voce '{voce.voce}' del documento '{doc.nome}' è incompleta da oltre 7 giorni.",
                canale='email',
                created_by=1  # Sistema
            )
            db.session.add(nuovo)
    
    # 🧯 Prove di Evacuazione in scadenza (annuali)
    for user in User.query.filter_by(role='quality').all():
        # Trova l'ultima prova per ogni luogo
        luoghi_prove = {}
        for prova in ProvaEvacuazione.query.all():
            if prova.luogo not in luoghi_prove or prova.data > luoghi_prove[prova.luogo].data:
                luoghi_prove[prova.luogo] = prova
        
        for luogo, ultima_prova in luoghi_prove.items():
            # Calcola quando dovrebbe essere la prossima prova (annuale)
            prossima_prova = ultima_prova.data + timedelta(days=365)
            
            if prossima_prova <= in_30_giorni:
                già_esiste = Reminder.query.filter_by(
                    user_id=user.id,
                    tipo='Prova Evacuazione',
                    entita_id=ultima_prova.id
                ).first()
                
                if già_esiste:
                    continue
                    
                nuovo = Reminder(
                    user_id=user.id,
                    tipo='Prova Evacuazione',
                    entita_id=ultima_prova.id,
                    entita_tipo='prova_evacuazione',
                    destinatario_email=user.email,
                    destinatario_ruolo=user.role,
                    scadenza=prossima_prova,
                    giorni_anticipo=30,
                    messaggio=f"La prova di evacuazione per '{luogo}' dovrebbe essere programmata entro il {prossima_prova}.",
                    canale='email',
                    created_by=1  # Sistema
                )
                db.session.add(nuovo)
    
    db.session.commit()

def crea_reminder_automatico(tipo, entita_id, entita_tipo, destinatario_email, 
                            destinatario_ruolo, scadenza, giorni_anticipo=30, 
                            messaggio=None, canale='email', created_by=None):
    """
    Crea automaticamente un nuovo reminder.
    
    Args:
        tipo: Tipo di reminder ('documento', 'visita_medica', 'checklist')
        entita_id: ID dell'entità
        entita_tipo: Tipo di entità ('Document', 'VisitaMedica', 'ChecklistCompliance')
        destinatario_email: Email del destinatario
        destinatario_ruolo: Ruolo del destinatario
        scadenza: Data di scadenza
        giorni_anticipo: Giorni di anticipo per il reminder
        messaggio: Messaggio personalizzato
        canale: Canale di invio ('email', 'interno', 'entrambi')
        created_by: ID utente che crea il reminder
    
    Returns:
        Reminder: Istanza del reminder creato
    """
    try:
        from app import db
        from models import Reminder
        
        # Calcola prossimo invio
        prossimo_invio = scadenza - timedelta(days=giorni_anticipo)
        
        reminder = Reminder(
            tipo=tipo,
            entita_id=entita_id,
            entita_tipo=entita_tipo,
            destinatario_email=destinatario_email,
            destinatario_ruolo=destinatario_ruolo,
            scadenza=scadenza,
            giorni_anticipo=giorni_anticipo,
            messaggio=messaggio,
            canale=canale,
            created_by=created_by,
            prossimo_invio=prossimo_invio
        )
        
        db.session.add(reminder)
        db.session.commit()
        
        logger.info(f"Reminder automatico creato: {tipo} per {destinatario_email}")
        return reminder
        
    except Exception as e:
        logger.error(f"Errore creazione reminder automatico: {str(e)}")
        return None

def monitora_download_sospetti():
    """
    Esegue il monitoraggio AI dei download sospetti ogni 10 minuti.
    """
    try:
        logger.info("Avvio monitoraggio AI download sospetti...")
        
        # Esegue analisi
        alerts = analizza_download_sospetti()
        
        # Crea alert nel database
        created_count = 0
        for alert_data in alerts:
            alert = create_ai_alert(alert_data)
            if alert:
                created_count += 1
                logger.info(f"Alert AI creato: {alert.alert_type} per utente {alert.user_id}")
        
        if created_count > 0:
            logger.info(f"Monitoraggio completato: {created_count} alert generati")
        else:
            logger.info("Monitoraggio completato: nessun alert generato")
            
    except Exception as e:
        logger.error(f"Errore durante monitoraggio AI download sospetti: {e}")


def avvia_scheduler(app):
    """
    Avvia il scheduler APScheduler per i reminder automatici.
    
    Args:
        app: Istanza dell'applicazione Flask
    """
    try:
        scheduler = BackgroundScheduler()
        
        # Aggiungi job per generare reminder ogni giorno alle 6:00
        scheduler.add_job(
            func=genera_reminder,
            trigger=CronTrigger(hour=6, minute=0),
            id='genera_reminder',
            name='Generazione Reminder Automatici',
            replace_existing=True
        )
        
        # Aggiungi job per processare reminder ogni giorno alle 7:00
        scheduler.add_job(
            func=processa_reminder,
            trigger=CronTrigger(hour=7, minute=0),
            id='processa_reminder',
            name='Processamento Reminder Automatici',
            replace_existing=True
        )
        
        # Aggiungi job per pulizia log vecchi (ogni domenica alle 2:00)
        scheduler.add_job(
            func=pulisci_log_vecchi,
            trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),
            id='pulisci_log',
            name='Pulizia Log Vecchi',
            replace_existing=True
        )
        
        # Aggiungi job per controllo visite mediche in scadenza (ogni giorno alle 6:30)
        scheduler.add_job(
            func=check_visite_scadenza,
            trigger=CronTrigger(hour=6, minute=30),
            id='check_visite_mediche',
            name='Controllo Visite Mediche in Scadenza',
            replace_existing=True
        )
        
        # Aggiungi job per reminder documentali (ogni giorno alle 8:00)
        scheduler.add_job(
            func=invia_promemoria_documenti,
            trigger=CronTrigger(hour=8, minute=0),
            id='reminder_documenti',
            name='Reminder Documenti in Scadenza',
            replace_existing=True
        )
        
        # Aggiungi job per pulizia token scaduti (ogni ora)
        scheduler.add_job(
            func=cleanup_expired_tokens,
            trigger=CronTrigger(minute=0),
            id='cleanup_tokens',
            name='Pulizia Token Scaduti',
            replace_existing=True
        )
        
        # Aggiungi job per verifica revisioni programmate (ogni lunedì alle 9:00)
        scheduler.add_job(
            func=verifica_revisioni_programmate,
            trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
            id='verifica_revisioni',
            name='Verifica Revisioni Programmate',
            replace_existing=True
        )
        
        # Aggiungi job per verifica documenti abbandonati (ogni venerdì alle 10:00)
        scheduler.add_job(
            func=verifica_documenti_abbandonati,
            trigger=CronTrigger(day_of_week='fri', hour=10, minute=0),
            id='verifica_abbandonati',
            name='Verifica Documenti Abbandonati',
            replace_existing=True
        )
        
        # Aggiungi job per monitoraggio AI download sospetti (ogni 10 minuti)
        scheduler.add_job(
            func=monitora_download_sospetti,
            trigger=CronTrigger(minute='*/10'),
            id='monitora_download_sospetti',
            name='Monitoraggio AI Download Sospetti',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("Scheduler APScheduler avviato con successo")
        
        # Salva il riferimento al scheduler nell'app
        app.scheduler = scheduler
        
    except Exception as e:
        logger.error(f"Errore avvio scheduler: {str(e)}")

def pulisci_log_vecchi():
    """
    Pulisce i log vecchi (più di 90 giorni).
    """
    try:
        from app import db
        from models import ReminderLog
        from datetime import datetime, timedelta
        
        data_limite = datetime.utcnow() - timedelta(days=90)
        
        # Elimina log vecchi
        log_eliminati = ReminderLog.query.filter(
            ReminderLog.timestamp < data_limite
        ).delete()
        
        db.session.commit()
        
        logger.info(f"Eliminati {log_eliminati} log vecchi")
        
    except Exception as e:
        logger.error(f"Errore pulizia log: {str(e)}")

def ferma_scheduler(app):
    """
    Ferma il scheduler APScheduler.
    
    Args:
        app: Istanza dell'applicazione Flask
    """
    try:
        if hasattr(app, 'scheduler'):
            app.scheduler.shutdown()
            logger.info("Scheduler APScheduler fermato")
    except Exception as e:
        logger.error(f"Errore fermata scheduler: {str(e)}") 

 