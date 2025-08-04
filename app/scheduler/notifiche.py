from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.mail import send_email
from app.models.notifiche import NotificaCritica
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

async def invia_report_settimanale(db: Session):
    da = datetime.utcnow() - timedelta(days=7)
    notifiche = db.query(NotificaCritica).filter(NotificaCritica.data_creazione >= da).all()

    errori = [n for n in notifiche if n.tipo == "errore_ai"]
    sync = [n for n in notifiche if n.tipo == "sync_fail"]
    lean = [n for n in notifiche if n.tipo == "violazione_lean"]

    contenuto = f"""
    🔔 Report Settimanale AI – Documenti
    - Errori AI: {len(errori)}
    - Sync falliti: {len(sync)}
    - Violazioni Lean: {len(lean)}

    🔍 Dashboard dettagliata: https://docs.mercurysurgelati.org/ceo/dashboard
    """

    send_email(to="ceo@azienda.it", subject="📊 Report Settimanale AI", body=contenuto) 