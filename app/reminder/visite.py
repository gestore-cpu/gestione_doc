"""
Modulo per la gestione dei reminder automatici delle visite mediche.
Contiene la logica per controllare scadenze e inviare notifiche.
"""

from flask_mail import Message
from datetime import date, timedelta
from app import db, mail
from app.models import VisitaMedicaEffettuata, LogReminderVisita
import logging

logger = logging.getLogger(__name__)

def check_visite_scadenza():
    """
    Controlla le visite mediche in scadenza e invia reminder automatici.
    
    Funzionalità:
    - Controlla visite scadute o in scadenza (entro 30 giorni)
    - Invia email al dipendente, HR e Qualità
    - Salva log per evitare notifiche duplicate
    - Gestisce escalation per visite già scadute
    """
    try:
        oggi = date.today()
        limite = oggi + timedelta(days=30)

        # Query visite con scadenza e senza certificato finale
        visite = VisitaMedicaEffettuata.query.filter(
            VisitaMedicaEffettuata.scadenza != None,
            VisitaMedicaEffettuata.certificato_finale == False
        ).all()

        logger.info(f"🔍 Controllo {len(visite)} visite mediche per scadenze...")

        for visita in visite:
            if not visita.utente:
                logger.warning(f"⚠️ Visita {visita.id} senza utente associato")
                continue

            # Determina tipo di notifica
            tipo_notifica = None
            if visita.scadenza < oggi:
                tipo_notifica = "scaduta"
            elif visita.scadenza <= limite:
                tipo_notifica = "in_scadenza"

            if not tipo_notifica:
                continue

            # Verifica se già notificata oggi
            già_inviata = LogReminderVisita.query.filter_by(
                visita_id=visita.id,
                tipo=tipo_notifica,
                data_invio=oggi
            ).first()
            
            if già_inviata:
                logger.info(f"✅ Visita {visita.id} già notificata oggi per {tipo_notifica}")
                continue

            # Costruzione messaggio
            corpo = (
                f"⚠️ Visita medica '{visita.tipo_visita}' per {visita.utente.full_name} "
                f"({visita.utente.email})\n\n"
                f"Data scadenza: {visita.scadenza.strftime('%d/%m/%Y')}\n"
                f"Stato: {'SCADUTA' if tipo_notifica == 'scaduta' else 'In scadenza'}\n\n"
                "Ti invitiamo a programmare o verificare l'esito."
            )

            # Prepara destinatari
            destinatari = [visita.utente.email]
            
            # Aggiungi HR e Qualità per escalation se scaduta
            if tipo_notifica == "scaduta":
                destinatari.extend(["hr@azienda.it", "qualita@azienda.it"])

            try:
                # Invia email
                msg = Message(
                    subject=f"[Visita {tipo_notifica.upper()}] {visita.tipo_visita} – {visita.utente.full_name}",
                    recipients=destinatari,
                    body=corpo
                )
                mail.send(msg)

                # Salva log
                log = LogReminderVisita(
                    visita_id=visita.id,
                    tipo=tipo_notifica,
                    data_invio=oggi
                )
                db.session.add(log)
                
                logger.info(f"✅ Reminder {tipo_notifica} inviato per visita {visita.id} a {len(destinatari)} destinatari")
                
            except Exception as e:
                logger.error(f"❌ Errore invio reminder visita {visita.id}: {e}")
                continue

        db.session.commit()
        logger.info("✅ Controllo visite mediche completato")
        
    except Exception as e:
        logger.error(f"❌ Errore generale check_visite_scadenza: {e}") 