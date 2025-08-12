"""
Service per il detection di download sospetti.
Implementa le regole R1, R2, R3 per rilevare comportamenti anomali.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import and_, func
from models import DownloadLog, DownloadAlert, User, db, DownloadAlertSeverity, DownloadAlertStatus
from extensions import mail
from flask_mail import Message
from flask import url_for

logger = logging.getLogger(__name__)

def run_download_detection(now: datetime) -> list[DownloadAlert]:
    """
    Esegue il detection di download sospetti.
    
    Args:
        now (datetime): Timestamp corrente
        
    Returns:
        list[DownloadAlert]: Lista degli alert creati
    """
    alerts_created = []
    
    try:
        logger.info("🔍 Avvio detection download sospetti...")
        
        # Regola R1: Burst per utente (> 10 download in 5 minuti)
        r1_alerts = detect_burst_downloads(now)
        alerts_created.extend(r1_alerts)
        
        # Regola R2: Orari insoliti (download tra 00:00-05:59 con count > 5 in 30 min)
        r2_alerts = detect_unusual_hours(now)
        alerts_created.extend(r2_alerts)
        
        # Regola R3: IP anomalo (nuovo IP non visto negli ultimi 14 giorni + ≥ 8 download in 1h)
        r3_alerts = detect_anomalous_ip(now)
        alerts_created.extend(r3_alerts)
        
        logger.info(f"✅ Detection completato: {len(alerts_created)} alert creati")
        
        # Invia email per alert critici
        for alert in alerts_created:
            if alert.is_critical:
                send_critical_alert_email(alert)
        
        return alerts_created
        
    except Exception as e:
        logger.error(f"❌ Errore durante detection: {str(e)}")
        return []

def detect_burst_downloads(now: datetime) -> list[DownloadAlert]:
    """
    Regola R1: Rileva burst di download per utente.
    > 10 download dello stesso utente in 5 minuti ⇒ warning
    
    Args:
        now (datetime): Timestamp corrente
        
    Returns:
        list[DownloadAlert]: Alert creati
    """
    alerts = []
    
    try:
        # Finestra temporale: ultimi 5 minuti
        window_start = now - timedelta(minutes=5)
        
        # Query per utenti con > 10 download in 5 minuti
        burst_users = db.session.query(
            DownloadLog.user_id,
            func.count(DownloadLog.id).label('download_count')
        ).filter(
            and_(
                DownloadLog.timestamp >= window_start,
                DownloadLog.timestamp <= now,
                DownloadLog.status == 'success'
            )
        ).group_by(DownloadLog.user_id).having(
            func.count(DownloadLog.id) > 10
        ).all()
        
        for user_id, count in burst_users:
            # Verifica se esiste già un alert per questa regola + utente nelle ultime 24h
            if not is_duplicate_alert('R1', user_id=user_id, hours=24):
                # Crea alert
                alert = create_download_alert(
                    rule='R1',
                    severity=DownloadAlertSeverity.WARNING,
                    user_id=user_id,
                    window_from=window_start,
                    window_to=now,
                    details={
                        'download_count': count,
                        'timeframe_minutes': 5,
                        'threshold': 10,
                        'description': f'Utente ha effettuato {count} download in 5 minuti'
                    }
                )
                alerts.append(alert)
                logger.warning(f"⚠️ R1 Alert: Utente {user_id} - {count} download in 5 minuti")
        
        return alerts
        
    except Exception as e:
        logger.error(f"❌ Errore R1 detection: {str(e)}")
        return []

def detect_unusual_hours(now: datetime) -> list[DownloadAlert]:
    """
    Regola R2: Rileva download in orari insoliti.
    Download tra 00:00-05:59 con count > 5 in 30 min ⇒ warning
    
    Args:
        now (datetime): Timestamp corrente
        
    Returns:
        list[DownloadAlert]: Alert creati
    """
    alerts = []
    
    try:
        # Verifica se siamo in orario notturno (00:00-05:59)
        current_hour = now.hour
        if not (0 <= current_hour <= 5):
            return alerts  # Non siamo in orario notturno
        
        # Finestra temporale: ultimi 30 minuti
        window_start = now - timedelta(minutes=30)
        
        # Query per utenti con > 5 download in 30 minuti in orario notturno
        night_users = db.session.query(
            DownloadLog.user_id,
            func.count(DownloadLog.id).label('download_count')
        ).filter(
            and_(
                DownloadLog.timestamp >= window_start,
                DownloadLog.timestamp <= now,
                DownloadLog.status == 'success'
            )
        ).group_by(DownloadLog.user_id).having(
            func.count(DownloadLog.id) > 5
        ).all()
        
        for user_id, count in night_users:
            # Verifica se esiste già un alert per questa regola + utente nelle ultime 24h
            if not is_duplicate_alert('R2', user_id=user_id, hours=24):
                # Crea alert
                alert = create_download_alert(
                    rule='R2',
                    severity=DownloadAlertSeverity.WARNING,
                    user_id=user_id,
                    window_from=window_start,
                    window_to=now,
                    details={
                        'download_count': count,
                        'timeframe_minutes': 30,
                        'threshold': 5,
                        'night_hours': '00:00-05:59',
                        'description': f'Utente ha effettuato {count} download in 30 minuti in orario notturno'
                    }
                )
                alerts.append(alert)
                logger.warning(f"⚠️ R2 Alert: Utente {user_id} - {count} download notturni in 30 minuti")
        
        return alerts
        
    except Exception as e:
        logger.error(f"❌ Errore R2 detection: {str(e)}")
        return []

def detect_anomalous_ip(now: datetime) -> list[DownloadAlert]:
    """
    Regola R3: Rileva IP anomali.
    Utente con nuovo IP non visto negli ultimi 14 giorni che effettua ≥ 8 download in 1h ⇒ critical
    
    Args:
        now (datetime): Timestamp corrente
        
    Returns:
        list[DownloadAlert]: Alert creati
    """
    alerts = []
    
    try:
        # Finestra temporale: ultimi 14 giorni per verificare IP storici
        historical_start = now - timedelta(days=14)
        
        # Finestra temporale: ultimi 60 minuti per download recenti
        recent_start = now - timedelta(minutes=60)
        
        # Trova utenti con download recenti
        recent_downloads = db.session.query(
            DownloadLog.user_id,
            DownloadLog.ip_address,
            func.count(DownloadLog.id).label('download_count')
        ).filter(
            and_(
                DownloadLog.timestamp >= recent_start,
                DownloadLog.timestamp <= now,
                DownloadLog.status == 'success',
                DownloadLog.ip_address.isnot(None)
            )
        ).group_by(DownloadLog.user_id, DownloadLog.ip_address).having(
            func.count(DownloadLog.id) >= 8
        ).all()
        
        for user_id, ip_address, count in recent_downloads:
            # Verifica se questo IP è nuovo per l'utente (non visto negli ultimi 14 giorni)
            if is_new_ip_for_user(user_id, ip_address, historical_start):
                # Verifica se esiste già un alert per questa regola + utente nelle ultime 24h
                if not is_duplicate_alert('R3', user_id=user_id, hours=24):
                    # Crea alert critico
                    alert = create_download_alert(
                        rule='R3',
                        severity=DownloadAlertSeverity.CRITICAL,
                        user_id=user_id,
                        ip_address=ip_address,
                        window_from=recent_start,
                        window_to=now,
                        details={
                            'download_count': count,
                            'timeframe_minutes': 60,
                            'threshold': 8,
                            'new_ip': ip_address,
                            'description': f'Utente con nuovo IP {ip_address} ha effettuato {count} download in 1 ora'
                        }
                    )
                    alerts.append(alert)
                    logger.error(f"🚨 R3 Alert: Utente {user_id} - Nuovo IP {ip_address} - {count} download in 1h")
        
        return alerts
        
    except Exception as e:
        logger.error(f"❌ Errore R3 detection: {str(e)}")
        return []

def is_duplicate_alert(rule: str, user_id: int = None, file_id: int = None, ip_address: str = None, hours: int = 24) -> bool:
    """
    Verifica se esiste già un alert per la stessa regola e chiave logica nelle ultime ore.
    
    Args:
        rule (str): Regola (R1, R2, R3)
        user_id (int): ID utente
        file_id (int): ID file
        ip_address (str): IP address
        hours (int): Ore per il controllo duplicati
        
    Returns:
        bool: True se esiste un alert duplicato
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = DownloadAlert.query.filter(
            and_(
                DownloadAlert.rule == rule,
                DownloadAlert.created_at >= cutoff_time
            )
        )
        
        if user_id:
            query = query.filter(DownloadAlert.user_id == user_id)
        if file_id:
            query = query.filter(DownloadAlert.file_id == file_id)
        if ip_address:
            query = query.filter(DownloadAlert.ip_address == ip_address)
        
        return query.first() is not None
        
    except Exception as e:
        logger.error(f"❌ Errore verifica duplicati: {str(e)}")
        return False

def is_new_ip_for_user(user_id: int, ip_address: str, since: datetime) -> bool:
    """
    Verifica se l'IP è nuovo per l'utente (non visto dal timestamp since).
    
    Args:
        user_id (int): ID utente
        ip_address (str): IP address
        since (datetime): Timestamp da cui controllare
        
    Returns:
        bool: True se l'IP è nuovo
    """
    try:
        # Cerca download dello stesso utente con IP diverso negli ultimi 14 giorni
        existing_ip = DownloadLog.query.filter(
            and_(
                DownloadLog.user_id == user_id,
                DownloadLog.ip_address != ip_address,
                DownloadLog.timestamp >= since,
                DownloadLog.ip_address.isnot(None)
            )
        ).first()
        
        # Se non trova IP diversi, questo è il primo IP dell'utente
        if not existing_ip:
            return True
        
        # Cerca se questo IP specifico è stato usato prima
        ip_used_before = DownloadLog.query.filter(
            and_(
                DownloadLog.user_id == user_id,
                DownloadLog.ip_address == ip_address,
                DownloadLog.timestamp < since
            )
        ).first()
        
        # Se l'IP non è mai stato usato prima, è nuovo
        return ip_used_before is None
        
    except Exception as e:
        logger.error(f"❌ Errore verifica IP nuovo: {str(e)}")
        return False

def create_download_alert(rule: str, severity: DownloadAlertSeverity, user_id: int = None, 
                         ip_address: str = None, file_id: int = None, window_from: datetime = None,
                         window_to: datetime = None, details: dict = None) -> DownloadAlert:
    """
    Crea un nuovo alert di download.
    
    Args:
        rule (str): Regola che ha generato l'alert
        severity (DownloadAlertSeverity): Severità
        user_id (int): ID utente
        ip_address (str): IP address
        file_id (int): ID file
        window_from (datetime): Inizio finestra
        window_to (datetime): Fine finestra
        details (dict): Dettagli aggiuntivi
        
    Returns:
        DownloadAlert: Alert creato
    """
    try:
        alert = DownloadAlert(
            rule=rule,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            file_id=file_id,
            window_from=window_from or datetime.utcnow(),
            window_to=window_to or datetime.utcnow(),
            details=details or {},
            status=DownloadAlertStatus.NEW
        )
        
        db.session.add(alert)
        db.session.commit()
        
        logger.info(f"✅ Alert creato: {rule} - {severity.value} - Utente {user_id}")
        return alert
        
    except Exception as e:
        logger.error(f"❌ Errore creazione alert: {str(e)}")
        db.session.rollback()
        return None

def send_critical_alert_email(alert: DownloadAlert):
    """
    Invia email per alert critici.
    
    Args:
        alert (DownloadAlert): Alert critico
    """
    try:
        # Trova admin da notificare
        admins = User.query.filter_by(role='admin').all()
        recipients = [admin.email for admin in admins if admin.email]
        
        if not recipients:
            logger.warning("⚠️ Nessun admin trovato per notifica email")
            return
        
        # Prepara email
        subject = f"🚨 Alert Critico Download - {alert.rule}"
        
        body = f"""
        È stato rilevato un download sospetto critico!
        
        📋 Dettagli Alert:
        - Regola: {alert.rule}
        - Severità: {alert.severity_display}
        - Utente: {alert.user.username if alert.user else 'N/A'}
        - IP: {alert.ip_address or 'N/A'}
        - Finestra: {alert.window_from.strftime('%d/%m/%Y %H:%M')} - {alert.window_to.strftime('%d/%m/%Y %H:%M')}
        
        📊 Dettagli:
        {alert.details.get('description', 'N/A')}
        
        🔗 Gestisci Alert:
        /admin/download-alerts
        
        Questo è un alert automatico del sistema di sicurezza.
        """
        
        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body
        )
        
        mail.send(msg)
        logger.info(f"📧 Email critica inviata per alert {alert.id}")
        
    except Exception as e:
        logger.error(f"❌ Errore invio email critica: {str(e)}")

# === FUNZIONI HELPER PER GESTIONE ALERT ===

def mark_download_alert_seen(alert_id: int, user: User) -> bool:
    """
    Segna un alert come visto.
    
    Args:
        alert_id (int): ID dell'alert
        user (User): Utente che marca come visto
        
    Returns:
        bool: True se operazione riuscita
    """
    try:
        alert = DownloadAlert.query.get(alert_id)
        if not alert:
            logger.error(f"❌ Alert {alert_id} non trovato")
            return False
        
        alert.status = DownloadAlertStatus.SEEN
        db.session.commit()
        
        logger.info(f"✅ Alert {alert_id} marcato come visto da {user.username}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Errore marcatura alert visto: {str(e)}")
        db.session.rollback()
        return False

def resolve_download_alert(alert_id: int, user: User, note: str = None) -> bool:
    """
    Risolve un alert.
    
    Args:
        alert_id (int): ID dell'alert
        user (User): Utente che risolve
        note (str): Nota aggiuntiva
        
    Returns:
        bool: True se operazione riuscita
    """
    try:
        alert = DownloadAlert.query.get(alert_id)
        if not alert:
            logger.error(f"❌ Alert {alert_id} non trovato")
            return False
        
        alert.status = DownloadAlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = user.id
        
        if note:
            if not alert.details:
                alert.details = {}
            alert.details['resolution_note'] = note
        
        db.session.commit()
        
        logger.info(f"✅ Alert {alert_id} risolto da {user.username}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Errore risoluzione alert: {str(e)}")
        db.session.rollback()
        return False

def build_alert_context(alert) -> str:
    """
    Crea un contesto sintetico per l'analisi AI dell'alert.
    
    Args:
        alert: Oggetto DownloadAlert
        
    Returns:
        str: Contesto formattato per l'AI
    """
    try:
        # Informazioni base dell'alert
        lines = [
            f"ALERT: {alert.rule} | severity={alert.severity} | status={alert.status}",
            f"Utente: {alert.user_id} | IP: {alert.ip_address or 'n/d'}",
            f"Finestra: {alert.window_from} – {alert.window_to}",
            f"Creato: {alert.created_at}"
        ]
        
        # Dettagli specifici per regola
        if alert.details:
            if alert.rule == 'R1':
                lines.append(f"Download count: {alert.details.get('download_count', 'n/d')} in {alert.details.get('timeframe_minutes', 'n/d')} minuti")
            elif alert.rule == 'R2':
                lines.append(f"Download count: {alert.details.get('download_count', 'n/d')} in orari insoliti")
            elif alert.rule == 'R3':
                lines.append(f"Nuovo IP: {alert.details.get('new_ip', 'n/d')} con {alert.details.get('download_count', 'n/d')} download")
        
        # File coinvolti (se disponibili)
        if alert.file_id:
            try:
                from models import Document
                doc = Document.query.get(alert.file_id)
                if doc:
                    lines.append(f"File coinvolto: {doc.title or doc.original_filename}")
            except:
                lines.append("File coinvolto: ID non trovato")
        
        # Baseline utente (semplificato)
        try:
            user_downloads = DownloadLog.query.filter(
                DownloadLog.user_id == alert.user_id,
                DownloadLog.timestamp >= datetime.utcnow() - timedelta(days=7)
            ).count()
            lines.append(f"Baseline utente (download ultimi 7 giorni): {user_downloads}")
        except:
            lines.append("Baseline utente: non disponibile")
        
        # Note precedenti
        if alert.note:
            lines.append(f"Note precedenti: {alert.note}")
        else:
            lines.append("Note precedenti: —")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Errore nella costruzione contesto alert: {e}")
        return f"Errore nel contesto: {str(e)}"
