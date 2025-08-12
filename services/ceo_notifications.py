"""
Servizio per le notifiche automatiche al CEO per invii PDF sensibili.
Gestisce la creazione e l'invio di notifiche quando vengono inviati PDF sensibili.
"""

import os
from datetime import datetime, timedelta
from flask import current_app
from flask_mail import Message
from extensions import db, mail
from models import NotificaCEO, LogInvioPDF, User, AlertAI
from sqlalchemy import and_


def crea_notifica_ceo_invio_pdf(log_invio_id, email_mittente, email_destinatario, nome_utente_guest=None):
    """
    Crea una notifica al CEO per un invio PDF sensibile.
    
    Args:
        log_invio_id (int): ID del log invio PDF.
        email_mittente (str): Email di chi ha inviato.
        email_destinatario (str): Email destinatario.
        nome_utente_guest (str, optional): Nome utente/guest coinvolto.
    
    Returns:
        NotificaCEO: L'oggetto notifica creato.
    """
    try:
        # Verifica se il mittente è admin
        mittente = User.query.filter_by(email=email_mittente).first()
        if not mittente or mittente.role != 'admin':
            return None  # Solo admin generano notifiche
        
        # Determina il tipo di notifica
        tipo_notifica = 'invio_pdf_sensibile'
        titolo = f"Invio PDF attività – {nome_utente_guest or 'utente/guest'}"
        
        # Verifica se è destinatario esterno (non aziendale)
        is_esterno = not email_destinatario.endswith('@mercurysurgelati.org')
        
        # Crea la notifica
        notifica = NotificaCEO(
            titolo=titolo,
            descrizione=f"PDF inviato da {email_mittente} a {email_destinatario}",
            tipo=tipo_notifica,
            email_mittente=email_mittente,
            email_destinatario=email_destinatario,
            nome_utente_guest=nome_utente_guest,
            log_invio_id=log_invio_id
        )
        
        db.session.add(notifica)
        db.session.commit()
        
        current_app.logger.info(f"✅ Notifica CEO creata per invio PDF: {titolo}")
        return notifica
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore creazione notifica CEO: {e}")
        db.session.rollback()
        return None


def verifica_criteri_notifica_ceo(log_invio):
    """
    Verifica se un invio PDF deve generare una notifica al CEO.
    
    Args:
        log_invio (LogInvioPDF): Il log dell'invio PDF.
    
    Returns:
        bool: True se deve generare notifica.
    """
    try:
        # Verifica se il mittente è admin
        mittente = User.query.filter_by(email=log_invio.inviato_da).first()
        if not mittente or mittente.role != 'admin':
            return False
        
        # Criterio 1: Email destinatario esterna (non aziendale)
        is_esterno = not log_invio.inviato_a.endswith('@mercurysurgelati.org')
        
        # Criterio 2: Guest con scadenza < 3 giorni
        guest_scadenza = False
        if log_invio.tipo == 'guest':
            guest = User.query.get(log_invio.id_utente_o_guest)
            if guest and guest.access_expiration:
                giorni_alla_scadenza = (guest.access_expiration - datetime.now().date()).days
                guest_scadenza = giorni_alla_scadenza < 3
        
        # Criterio 3: Utente con alert AI livello alto o critico
        alert_ai_critico = False
        if log_invio.tipo == 'user':
            alert = AlertAI.query.filter(
                and_(
                    AlertAI.user_id == log_invio.id_utente_o_guest,
                    AlertAI.stato == 'nuovo',
                    AlertAI.livello.in_(['alto', 'critico'])
                )
            ).first()
            alert_ai_critico = alert is not None
        
        # Genera notifica se almeno un criterio è soddisfatto
        return is_esterno or guest_scadenza or alert_ai_critico
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore verifica criteri notifica CEO: {e}")
        return False


def invia_email_notifica_ceo(notifica):
    """
    Invia email di notifica al CEO (opzionale).
    
    Args:
        notifica (NotificaCEO): La notifica da inviare.
    
    Returns:
        bool: True se inviata con successo.
    """
    try:
        # Ottieni email CEO da configurazione
        ceo_email = current_app.config.get('CEO_EMAIL') or os.getenv('CEO_EMAIL')
        if not ceo_email:
            current_app.logger.warning("⚠️ CEO_EMAIL non configurata, skip invio email")
            return False
        
        # Prepara il contenuto email
        subject = f"🔔 {notifica.titolo} - DOCS Mercury"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #007bff;">{notifica.titolo}</h2>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>📧 Mittente:</strong> {notifica.email_mittente}</p>
                    <p><strong>📧 Destinatario:</strong> {notifica.email_destinatario}</p>
                    <p><strong>👤 Utente/Guest:</strong> {notifica.nome_utente_guest or 'N/A'}</p>
                    <p><strong>📅 Data:</strong> {notifica.data_creazione_formatted}</p>
                </div>
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>ℹ️ Descrizione:</strong></p>
                    <p>{notifica.descrizione}</p>
                </div>
                
                <p style="margin-top: 30px; font-size: 12px; color: #666;">
                    Questa è una notifica automatica del sistema DOCS Mercury.<br>
                    Per visualizzare tutti i dettagli, accedi alla dashboard CEO.
                </p>
            </div>
        </body>
        </html>
        """
        
        # Invia email
        msg = Message(
            subject=subject,
            recipients=[ceo_email],
            html=html_body
        )
        
        mail.send(msg)
        current_app.logger.info(f"✅ Email notifica CEO inviata a {ceo_email}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore invio email notifica CEO: {e}")
        return False


def processa_invio_pdf_per_notifiche(log_invio_id):
    """
    Processa un invio PDF per verificare se generare notifiche CEO.
    
    Args:
        log_invio_id (int): ID del log invio PDF.
    
    Returns:
        NotificaCEO: La notifica creata (se applicabile).
    """
    try:
        # Ottieni il log invio
        log_invio = LogInvioPDF.query.get(log_invio_id)
        if not log_invio:
            return None
        
        # Verifica criteri per notifica
        if not verifica_criteri_notifica_ceo(log_invio):
            return None
        
        # Ottieni nome utente/guest
        nome_utente_guest = None
        if log_invio.tipo == 'user':
            user = User.query.get(log_invio.id_utente_o_guest)
            if user:
                nome_utente_guest = f"{user.nome or user.username} {user.cognome or ''}".strip()
        elif log_invio.tipo == 'guest':
            guest = User.query.get(log_invio.id_utente_o_guest)
            if guest:
                nome_utente_guest = f"{guest.nome or guest.username} {guest.cognome or ''}".strip()
        
        # Crea notifica
        notifica = crea_notifica_ceo_invio_pdf(
            log_invio_id=log_invio_id,
            email_mittente=log_invio.inviato_da,
            email_destinatario=log_invio.inviato_a,
            nome_utente_guest=nome_utente_guest
        )
        
        # Invia email (opzionale)
        if notifica:
            invia_email_notifica_ceo(notifica)
        
        return notifica
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore processamento notifica CEO: {e}")
        return None


def get_notifiche_ceo_non_lette():
    """
    Ottiene le notifiche CEO non lette.
    
    Returns:
        list: Lista delle notifiche non lette.
    """
    try:
        return NotificaCEO.query.filter_by(stato='nuovo').order_by(NotificaCEO.data_creazione.desc()).all()
    except Exception as e:
        current_app.logger.error(f"❌ Errore recupero notifiche CEO: {e}")
        return []


def marca_notifica_letta(notifica_id):
    """
    Marca una notifica come letta.
    
    Args:
        notifica_id (int): ID della notifica.
    
    Returns:
        bool: True se aggiornata con successo.
    """
    try:
        notifica = NotificaCEO.query.get(notifica_id)
        if notifica:
            notifica.marca_letta()
            db.session.commit()
            return True
        return False
    except Exception as e:
        current_app.logger.error(f"❌ Errore marcatura notifica come letta: {e}")
        db.session.rollback()
        return False
