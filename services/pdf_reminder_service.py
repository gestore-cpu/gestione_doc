"""
Servizio per gestire i reminder automatici dei PDF inviati.
Controlla documenti non letti o non firmati e invia email di promemoria.
"""

from datetime import datetime, timedelta
from flask import current_app
from flask_mail import Message
from models import LogInvioPDF, LetturaPDF, FirmaDocumento, User, Document
from extensions import db, mail
import logging

logger = logging.getLogger(__name__)


class PDFReminderService:
    """
    Servizio per gestire i reminder automatici dei PDF inviati.
    """
    
    # Configurazione giorni di attesa
    GIORNI_LETTURA = 3  # Reminder se non letto dopo 3 giorni
    GIORNI_FIRMA = 5     # Reminder se non firmato dopo 5 giorni
    
    @staticmethod
    def check_reminder_pdf():
        """
        Controlla i PDF inviati e invia reminder per documenti non letti o non firmati.
        Questa funzione viene eseguita automaticamente dal scheduler.
        """
        try:
            oggi = datetime.utcnow()
            logger.info(f"🔍 Inizio controllo reminder PDF - {oggi.strftime('%d/%m/%Y %H:%M')}")
            
            # Ottieni tutti gli invii PDF
            invii = LogInvioPDF.query.filter_by(tipo='user', esito='successo').all()
            logger.info(f"📊 Trovati {len(invii)} invii PDF da controllare")
            
            reminder_inviati = 0
            errori = 0
            
            for invio in invii:
                try:
                    # Ottieni i dati dell'utente
                    user = User.query.get(invio.id_utente_o_guest)
                    if not user:
                        logger.warning(f"⚠️  Utente non trovato per invio ID: {invio.id}")
                        continue
                    
                    # Cerca il documento associato
                    document = PDFReminderService._trova_documento_associato(user.id)
                    if not document:
                        logger.warning(f"⚠️  Documento non trovato per utente: {user.email}")
                        continue
                    
                    # Calcola giorni passati dall'invio
                    giorni_passati = (oggi - invio.timestamp).days
                    
                    # Ottieni letture per questo utente e documento
                    letture = LetturaPDF.query.filter_by(
                        user_id=user.id,
                        document_id=document.id
                    ).all()
                    
                    # Ottieni firma per questo utente e documento
                    firma = FirmaDocumento.query.filter_by(
                        user_id=user.id,
                        document_id=document.id
                    ).first()
                    
                    # 1. Controllo: Promemoria se non letto dopo X giorni
                    if not letture and giorni_passati >= PDFReminderService.GIORNI_LETTURA:
                        logger.info(f"📧 Invio reminder lettura per {user.email} - documento: {document.title}")
                        PDFReminderService._invia_email_reminder(
                            user.email, document, "lettura mancante", giorni_passati
                        )
                        reminder_inviati += 1
                    
                    # 2. Controllo: Promemoria se letto ma non firmato dopo Y giorni
                    elif letture and (not firma or firma.stato == "in_attesa") and giorni_passati >= PDFReminderService.GIORNI_FIRMA:
                        logger.info(f"📧 Invio reminder firma per {user.email} - documento: {document.title}")
                        PDFReminderService._invia_email_reminder(
                            user.email, document, "firma mancante", giorni_passati
                        )
                        reminder_inviati += 1
                    
                except Exception as e:
                    errori += 1
                    logger.error(f"❌ Errore nel controllo invio {invio.id}: {str(e)}")
                    continue
            
            logger.info(f"✅ Controllo reminder completato - {reminder_inviati} reminder inviati, {errori} errori")
            return {
                'success': True,
                'reminder_inviati': reminder_inviati,
                'errori': errori,
                'timestamp': oggi
            }
            
        except Exception as e:
            logger.error(f"❌ Errore generale nel controllo reminder PDF: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow()
            }
    
    @staticmethod
    def _trova_documento_associato(user_id):
        """
        Trova il documento associato a un utente tramite le letture.
        
        Args:
            user_id (int): ID dell'utente
            
        Returns:
            Document: Documento associato o None
        """
        try:
            # Cerca nelle letture per trovare il documento
            lettura = LetturaPDF.query.filter_by(user_id=user_id).first()
            if lettura:
                return Document.query.get(lettura.document_id)
            
            # Se non ci sono letture, cerca nei log invio
            invio = LogInvioPDF.query.filter_by(
                id_utente_o_guest=user_id,
                tipo='user'
            ).first()
            
            if invio:
                # Cerca il documento tramite il titolo nell'oggetto email
                # Questo è un fallback se non abbiamo il document_id diretto
                return None  # Per ora restituiamo None, da migliorare
            
            return None
            
        except Exception as e:
            logger.error(f"Errore nel trovare documento per utente {user_id}: {str(e)}")
            return None
    
    @staticmethod
    def _invia_email_reminder(email, document, motivo, giorni_passati):
        """
        Invia email di reminder per documento non letto o non firmato.
        
        Args:
            email (str): Email del destinatario
            document (Document): Documento per cui inviare il reminder
            motivo (str): Motivo del reminder ('lettura mancante' o 'firma mancante')
            giorni_passati (int): Giorni passati dall'invio
        """
        try:
            # Costruisci il link diretto
            base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
            link_firma = f"{base_url}/documenti/{document.id}/firma"
            link_visualizza = f"{base_url}/documenti/{document.id}/view/pdf"
            
            # Prepara il soggetto
            if motivo == "lettura mancante":
                subject = f"📄 Reminder: Documento da leggere - {document.title}"
                action_text = "leggere"
                link_principale = link_visualizza
            else:
                subject = f"🖋️ Reminder: Documento da firmare - {document.title}"
                action_text = "firmare"
                link_principale = link_firma
            
            # Prepara il corpo dell'email
            body = f"""
Ciao,

ti ricordiamo di {action_text} il seguente documento:

📄 **{document.title}**

📅 Inviatoti il: {document.created_at.strftime('%d/%m/%Y')}
⏰ Giorni trascorsi: {giorni_passati}

🔗 **Link diretto per {action_text}:**
{link_principale}

📋 **Dettagli documento:**
• Titolo: {document.title}
• Descrizione: {document.description or 'Nessuna descrizione'}
• Caricato da: {document.uploader_email}

💡 **Come procedere:**
1. Clicca sul link sopra
2. Leggi attentamente il documento
3. Conferma la presa visione con la firma digitale

⚠️ **Importante:** Questo documento è parte del processo di compliance aziendale.

Grazie per la tua attenzione,
Il team di gestione documentale

---
*Questo è un reminder automatico. Per assistenza, contatta l'amministratore.*
"""
            
            # Invia l'email
            msg = Message(
                subject=subject,
                recipients=[email],
                body=body,
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')
            )
            
            mail.send(msg)
            logger.info(f"✅ Email reminder inviata a {email} per documento {document.title}")
            
            # Log dell'azione
            PDFReminderService._log_reminder_inviato(email, document, motivo, giorni_passati)
            
        except Exception as e:
            logger.error(f"❌ Errore nell'invio email reminder a {email}: {str(e)}")
            raise
    
    @staticmethod
    def _log_reminder_inviato(email, document, motivo, giorni_passati):
        """
        Logga l'invio del reminder per audit.
        
        Args:
            email (str): Email del destinatario
            document (Document): Documento
            motivo (str): Motivo del reminder
            giorni_passati (int): Giorni passati dall'invio
        """
        try:
            # Qui potresti salvare il log in una tabella dedicata
            # Per ora usiamo solo il logger
            logger.info(f"📝 Log reminder: {email} - {document.title} - {motivo} - {giorni_passati} giorni")
            
        except Exception as e:
            logger.error(f"Errore nel logging reminder: {str(e)}")
    
    @staticmethod
    def get_statistiche_reminder():
        """
        Ottiene statistiche sui reminder inviati.
        
        Returns:
            dict: Statistiche sui reminder
        """
        try:
            oggi = datetime.utcnow()
            
            # Conta invii che potrebbero necessitare reminder
            invii_totali = LogInvioPDF.query.filter_by(tipo='user', esito='successo').count()
            
            # Conta invii non letti dopo X giorni
            data_limite_lettura = oggi - timedelta(days=PDFReminderService.GIORNI_LETTURA)
            invii_non_letti = 0
            
            # Conta invii non firmati dopo Y giorni
            data_limite_firma = oggi - timedelta(days=PDFReminderService.GIORNI_FIRMA)
            invii_non_firmati = 0
            
            # Logica per contare (semplificata per ora)
            # In una implementazione completa, faresti query più complesse
            
            return {
                'invii_totali': invii_totali,
                'potenziali_reminder_lettura': invii_non_letti,
                'potenziali_reminder_firma': invii_non_firmati,
                'giorni_lettura': PDFReminderService.GIORNI_LETTURA,
                'giorni_firma': PDFReminderService.GIORNI_FIRMA
            }
            
        except Exception as e:
            logger.error(f"Errore nel calcolo statistiche reminder: {str(e)}")
            return {
                'invii_totali': 0,
                'potenziali_reminder_lettura': 0,
                'potenziali_reminder_firma': 0,
                'giorni_lettura': PDFReminderService.GIORNI_LETTURA,
                'giorni_firma': PDFReminderService.GIORNI_FIRMA
            }
