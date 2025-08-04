#!/usr/bin/env python3
"""
Task per reminder automatici documentali.
Gestisce l'invio di promemoria per documenti in scadenza.
"""

from datetime import datetime, timedelta
from flask import current_app
from flask_mail import Message
import logging

# Configurazione logging
logger = logging.getLogger(__name__)

def invia_promemoria_documenti():
    """
    Invia promemoria per documenti in scadenza entro 30 giorni.
    """
    try:
        from app import app, db, mail
        from models import Document, User
        
        with app.app_context():
            oggi = datetime.today().date()
            entro_30gg = oggi + timedelta(days=30)
            
            # Documenti in scadenza
            documenti = Document.query.filter(
                Document.expiry_date.isnot(None),
                Document.expiry_date <= entro_30gg,
                Document.expiry_date >= oggi
            ).all()
            
            logger.info(f"📄 Trovati {len(documenti)} documenti in scadenza")
            
            for doc in documenti:
                giorni = (doc.expiry_date.date() - oggi).days
                destinatari = get_responsabili_documento(doc)
                
                if not destinatari:
                    logger.warning(f"⚠️ Nessun destinatario trovato per documento {doc.id}")
                    continue
                
                # Prepara messaggio
                subject = f"📄 Documento in scadenza: {doc.title}"
                message = prepare_reminder_message(doc, giorni)
                
                # Invia a tutti i destinatari
                for user in destinatari:
                    try:
                        if user.reminder_email:
                            send_email_reminder(user.email, subject, message)
                            logger.info(f"✅ Email inviata a {user.email} per documento {doc.id}")
                        
                        if user.reminder_whatsapp and user.phone:
                            send_whatsapp_reminder(user.phone, message)
                            logger.info(f"✅ WhatsApp inviato a {user.phone} per documento {doc.id}")
                            
                    except Exception as e:
                        logger.error(f"❌ Errore invio reminder a {user.email}: {e}")
            
            # Controlla documenti scaduti
            check_documenti_scaduti()
            
            # Controlla documenti ignorati
            check_documenti_ignorati()
            
    except Exception as e:
        logger.error(f"❌ Errore generale reminder documenti: {e}")

def get_responsabili_documento(doc):
    """
    Ottiene i responsabili per un documento.
    
    Args:
        doc (Document): Documento da controllare
        
    Returns:
        list: Lista di utenti responsabili
    """
    from models import User
    
    responsabili = []
    
    # Responsabile diretto (uploader)
    if doc.user_id:
        uploader = User.query.get(doc.user_id)
        if uploader:
            responsabili.append(uploader)
    
    # Admin dell'azienda
    if doc.company_id:
        admin_azienda = User.query.filter_by(
            company_id=doc.company_id,
            role='admin'
        ).all()
        responsabili.extend(admin_azienda)
    
    # CEO (se presente)
    ceo_users = User.query.filter_by(role='ceo').all()
    responsabili.extend(ceo_users)
    
    # Rimuovi duplicati
    return list(set(responsabili))

def prepare_reminder_message(doc, giorni):
    """
    Prepara il messaggio di reminder per un documento.
    
    Args:
        doc (Document): Documento
        giorni (int): Giorni alla scadenza
        
    Returns:
        str: Messaggio formattato
    """
    status_icon = "⚠️"
    if giorni <= 7:
        status_icon = "🚨"
    elif giorni <= 14:
        status_icon = "⚠️"
    
    message = f"""
{status_icon} PROMEMORIA DOCUMENTO IN SCADENZA

📄 Titolo: {doc.title}
📅 Scadenza: {doc.expiry_date.strftime('%d/%m/%Y')}
⏰ Giorni rimanenti: {giorni}
🏢 Azienda: {doc.company.name if doc.company else 'N/A'}
🏭 Reparto: {doc.department.name if doc.department else 'N/A'}

🤖 Stato AI: {doc.ai_status or 'Non analizzato'}
📝 Note AI: {doc.ai_explain or 'Nessuna nota'}

🔗 Link: /admin/docs/{doc.id}

⚠️ Controlla e aggiorna il documento se necessario.
📧 Per assistenza contatta l'amministratore.

---
Mercury Document Intelligence
Generato automaticamente il {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
    return message.strip()

def send_email_reminder(email, subject, message):
    """
    Invia email di reminder.
    
    Args:
        email (str): Email destinatario
        subject (str): Oggetto email
        message (str): Messaggio
    """
    from app import mail
    
    try:
        msg = Message(
            subject=subject,
            recipients=[email],
            body=message,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@mercurysurgelati.org')
        )
        mail.send(msg)
        logger.info(f"✅ Email reminder inviata a {email}")
        
    except Exception as e:
        logger.error(f"❌ Errore invio email a {email}: {e}")

def send_whatsapp_reminder(phone, message):
    """
    Invia reminder WhatsApp (placeholder per integrazione futura).
    
    Args:
        phone (str): Numero di telefono
        message (str): Messaggio
    """
    # TODO: Integrare con API WhatsApp Business
    logger.info(f"📱 WhatsApp reminder per {phone}: {message[:50]}...")
    
    # Per ora solo log, in futuro integrare con API WhatsApp
    pass

def check_documenti_scaduti():
    """
    Controlla documenti già scaduti e invia alert.
    """
    from app import app
    from models import Document, User
    
    with app.app_context():
        oggi = datetime.today().date()
        
        # Documenti scaduti
        documenti_scaduti = Document.query.filter(
            Document.expiry_date.isnot(None),
            Document.expiry_date < oggi
        ).all()
        
        if documenti_scaduti:
            logger.warning(f"🚨 Trovati {len(documenti_scaduti)} documenti scaduti")
            
            # Invia alert agli admin
            admin_users = User.query.filter_by(role='admin').all()
            ceo_users = User.query.filter_by(role='ceo').all()
            
            alert_users = admin_users + ceo_users
            
            subject = f"🚨 ALERT: {len(documenti_scaduti)} documenti scaduti"
            message = f"""
🚨 ALERT DOCUMENTI SCADUTI

Sono stati rilevati {len(documenti_scaduti)} documenti scaduti:

"""
            
            for doc in documenti_scaduti:
                giorni_scaduti = (oggi - doc.expiry_date.date()).days
                message += f"• {doc.title} (scaduto da {giorni_scaduti} giorni)\n"
            
            message += f"""
🔗 Controlla: /admin/docs

---
Mercury Document Intelligence
{datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
            
            for user in alert_users:
                if user.reminder_email:
                    try:
                        send_email_reminder(user.email, subject, message)
                    except Exception as e:
                        logger.error(f"❌ Errore alert scaduti a {user.email}: {e}")

def check_documenti_ignorati():
    """
    Controlla documenti incompleti ignorati da tempo.
    """
    from app import app
    from models import Document, User
    
    with app.app_context():
        oggi = datetime.today()
        limite = oggi - timedelta(days=60)
        
        # Documenti incompleti non aggiornati da 60+ giorni
        documenti_ignorati = Document.query.filter(
            Document.ai_status.in_(['incompleto', 'scaduto', 'manca_firma']),
            Document.last_updated <= limite
        ).all()
        
        if documenti_ignorati:
            logger.warning(f"⚠️ Trovati {len(documenti_ignorati)} documenti ignorati")
            
            # Invia alert agli admin
            admin_users = User.query.filter_by(role='admin').all()
            ceo_users = User.query.filter_by(role='ceo').all()
            
            alert_users = admin_users + ceo_users
            
            subject = f"⚠️ ALERT: {len(documenti_ignorati)} documenti ignorati"
            message = f"""
⚠️ ALERT DOCUMENTI IGNORATI

Sono stati rilevati {len(documenti_ignorati)} documenti incompleti non aggiornati da 60+ giorni:

"""
            
            for doc in documenti_ignorati:
                giorni_ignorato = (oggi - doc.last_updated).days
                message += f"• {doc.title} (ignorato da {giorni_ignorato} giorni) - Stato: {doc.ai_status}\n"
            
            message += f"""
🔗 Controlla: /admin/docs

---
Mercury Document Intelligence
{datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
            
            for user in alert_users:
                if user.reminder_email:
                    try:
                        send_email_reminder(user.email, subject, message)
                    except Exception as e:
                        logger.error(f"❌ Errore alert ignorati a {user.email}: {e}")

def get_documenti_ignorati():
    """
    Ottiene documenti incompleti ignorati da tempo.
    
    Returns:
        list: Lista documenti ignorati
    """
    from app import app
    from models import Document
    
    with app.app_context():
        oggi = datetime.today()
        limite = oggi - timedelta(days=60)
        
        return Document.query.filter(
            Document.ai_status != "completo",
            Document.last_updated <= limite
        ).all() 