from datetime import datetime
import logging

async def notify_missing_or_expired(result: dict):
    errors = []

    # 🔍 Controllo scadenza
    if "dates" in result:
        for date_str, label in result["dates"].items():
            try:
                doc_date = datetime.strptime(date_str, "%Y-%m-%d")
                if "scadenza" in label.lower() and doc_date < datetime.now():
                    errors.append(f"Documento scaduto: {date_str}")
            except Exception:
                errors.append(f"Data non valida: {date_str}")

    # ✍️ Controllo firma
    if not result.get("signatures"):
        errors.append("Firma assente nel documento")

    # (Facoltativo) Controllo mancanza documenti previsti (via DB o regole)
    # if result['classification'] == "Qualità" and not is_procedure_registered(result['filename']):
    #     errors.append("Documento previsto ma non registrato nel sistema")

    # 🔔 Notifica (per ora solo log, in futuro: email, Telegram, task AI)
    for err in errors:
        logging.warning(f"[DOC AI ALERT] {result['filename']}: {err}")

def invia_notifica_sblocco(user, richiesta, tipo_evento):
    messaggio = ""
    if tipo_evento == "creata":
        messaggio = (
            f"📄 Hai richiesto l’accesso al documento {richiesta.document_id}. "
            f"Riceverai una risposta appena possibile."
        )
    elif tipo_evento == "approvata":
        messaggio = f"✅ La tua richiesta per il documento {richiesta.document_id} è stata approvata."
    elif tipo_evento == "rifiutata":
        messaggio = (
            f"❌ La tua richiesta per il documento {richiesta.document_id} è stata rifiutata. "
            f"Motivo: {richiesta.risposta_admin}"
        )
    # Email
    if getattr(user, 'preferenza_notifica', 'email') in ("email", "entrambi"):
        from app.services.mail import send_email
        send_email(
            to=user.email,
            subject="Aggiornamento richiesta documenti",
            body=messaggio
        )
    # WhatsApp
    if getattr(user, 'preferenza_notifica', 'email') in ("whatsapp", "entrambi"):
        from app.services.whatsapp import send_whatsapp
        send_whatsapp(user.phone_number, messaggio) 