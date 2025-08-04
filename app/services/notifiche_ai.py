from app.models.notifiche import NotificaAI
from sqlalchemy.orm import Session
import asyncio
from app.services.mail import send_email
# from app.services.whatsapp import send_whatsapp  # Da implementare o mock
from datetime import datetime

async def invia_email_ai(email, oggetto, messaggio):
    await asyncio.to_thread(send_email, to=email, subject=oggetto, body=messaggio)

async def invia_whatsapp_ai(telefono, messaggio):
    # await send_whatsapp(telefono, messaggio)
    print(f"[WHATSAPP] {telefono}: {messaggio}")

async def invia_notifica_ai(utente, messaggio: str, oggetto: str = "Notifica AI", tipo_evento: str = None, db: Session = None):
    preferenza = (getattr(utente, 'notifica_preferita', 'email') or 'email').lower()
    telefono = getattr(utente, 'telefono', None)
    email = getattr(utente, 'email', None)
    esito = "errore"
    canale_usato = None
    try:
        if preferenza == "none" or preferenza == "nessuno":
            esito = "nessuno"
            return
        if preferenza in ["email", "entrambi"] and email:
            try:
                await invia_email_ai(email, oggetto, messaggio)
                esito = "inviato"
                canale_usato = "email"
            except Exception as e:
                esito = f"errore_email:{e}"
                canale_usato = "email"
                # Retry su WhatsApp se preferenza = entrambi
                if preferenza == "entrambi" and telefono:
                    try:
                        await invia_whatsapp_ai(telefono, messaggio)
                        esito = "inviato_retry_wa"
                        canale_usato = "whatsapp"
                    except Exception as e2:
                        esito = f"errore_wa:{e2}"
        elif preferenza in ["whatsapp"] and telefono:
            try:
                await invia_whatsapp_ai(telefono, messaggio)
                esito = "inviato"
                canale_usato = "whatsapp"
            except Exception as e:
                esito = f"errore_wa:{e}"
        elif preferenza == "entrambi" and telefono:
            try:
                await invia_whatsapp_ai(telefono, messaggio)
                esito = "inviato"
                canale_usato = "whatsapp"
            except Exception as e:
                esito = f"errore_wa:{e}"
        # Log DB
        if db is not None:
            notifica = NotificaAI(
                utente_email=email,
                messaggio=messaggio,
                oggetto=oggetto,
                tipo_evento=tipo_evento,
                canale=canale_usato or preferenza,
                esito=esito,
                data_invio=datetime.utcnow()
            )
            db.add(notifica)
            db.commit()
    except Exception as e:
        print(f"[NOTIFICA][ERR] Log DB: {e}") 