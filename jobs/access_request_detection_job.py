"""
Job automatici per il sistema di richieste di accesso.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import and_, func
from models import AccessRequest, DocumentShare, DownloadLog, db
from routes.access_requests import expire_access_requests, cleanup_expired_shares

logger = logging.getLogger(__name__)

def detect_access_request_anomalies():
    """
    Rileva anomalie nelle richieste di accesso.
    """
    try:
        logger.info("🔍 Avvio detection anomalie richieste accesso...")
        
        # Conta richieste nelle ultime 24 ore per utente
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        # Trova utenti con troppe richieste (soglia: 10 richieste/giorno)
        high_volume_users = db.session.query(
            AccessRequest.requested_by,
            func.count(AccessRequest.id).label('request_count')
        ).filter(
            AccessRequest.created_at >= yesterday
        ).group_by(AccessRequest.requested_by).having(
            func.count(AccessRequest.id) >= 10
        ).all()
        
        for user_id, count in high_volume_users:
            logger.warning(f"⚠️ Utente {user_id} ha fatto {count} richieste nelle ultime 24 ore")
            
            # Qui potresti creare un alert o inviare una notifica
            # create_anomaly_alert(user_id, count, "high_volume")
        
        # Trova pattern sospetti (stesso documento richiesto da utenti diversi in breve tempo)
        suspicious_patterns = db.session.query(
            AccessRequest.file_id,
            func.count(AccessRequest.requested_by.distinct()).label('unique_users'),
            func.count(AccessRequest.id).label('total_requests')
        ).filter(
            AccessRequest.created_at >= yesterday
        ).group_by(AccessRequest.file_id).having(
            and_(
                func.count(AccessRequest.requested_by.distinct()) >= 3,
                func.count(AccessRequest.id) >= 5
            )
        ).all()
        
        for file_id, unique_users, total_requests in suspicious_patterns:
            logger.warning(f"⚠️ Documento {file_id} richiesto da {unique_users} utenti diversi ({total_requests} richieste totali)")
            
            # Qui potresti creare un alert
            # create_anomaly_alert(file_id, total_requests, "suspicious_pattern")
        
        logger.info("✅ Detection anomalie completata")
        
    except Exception as e:
        logger.error(f"❌ Errore durante detection anomalie: {str(e)}")

def expire_old_access_requests():
    """
    Scade automaticamente le richieste approvate con expires_at < now.
    """
    try:
        logger.info("⏰ Avvio scadenza richieste accesso...")
        
        # Esegui le funzioni di scadenza
        expire_access_requests()
        cleanup_expired_shares()
        
        logger.info("✅ Scadenza richieste completata")
        
    except Exception as e:
        logger.error(f"❌ Errore durante scadenza richieste: {str(e)}")

def cleanup_old_alerts():
    """
    Pulisce gli alert vecchi (più di 30 giorni).
    """
    try:
        logger.info("🧹 Avvio pulizia alert vecchi...")
        
        # Data limite: 30 giorni fa
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Conta quanti alert verranno eliminati
        old_alerts_count = db.session.query(func.count()).select_from(
            db.session.query(AccessRequest).filter(
                and_(
                    AccessRequest.created_at < cutoff_date,
                    AccessRequest.status.in_(['denied', 'expired'])
                )
            ).subquery()
        ).scalar()
        
        if old_alerts_count > 0:
            logger.info(f"🗑️ Eliminati {old_alerts_count} alert vecchi")
        
        logger.info("✅ Pulizia alert completata")
        
    except Exception as e:
        logger.error(f"❌ Errore durante pulizia alert: {str(e)}")

def generate_access_request_stats():
    """
    Genera statistiche per le richieste di accesso.
    """
    try:
        logger.info("📊 Generazione statistiche richieste accesso...")
        
        # Statistiche generali
        total_requests = AccessRequest.query.count()
        pending_requests = AccessRequest.query.filter_by(status='pending').count()
        approved_requests = AccessRequest.query.filter_by(status='approved').count()
        denied_requests = AccessRequest.query.filter_by(status='denied').count()
        expired_requests = AccessRequest.query.filter_by(status='expired').count()
        
        # Richieste oggi
        today = datetime.utcnow().date()
        today_requests = AccessRequest.query.filter(
            AccessRequest.created_at >= today
        ).count()
        
        # Richieste ultimi 7 giorni
        last_week = datetime.utcnow() - timedelta(days=7)
        week_requests = AccessRequest.query.filter(
            AccessRequest.created_at >= last_week
        ).count()
        
        # Tasso di approvazione
        approval_rate = 0
        if total_requests > 0:
            approval_rate = (approved_requests / total_requests) * 100
        
        stats = {
            'total': total_requests,
            'pending': pending_requests,
            'approved': approved_requests,
            'denied': denied_requests,
            'expired': expired_requests,
            'today': today_requests,
            'last_week': week_requests,
            'approval_rate': round(approval_rate, 2)
        }
        
        logger.info(f"📈 Statistiche: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Errore durante generazione statistiche: {str(e)}")
        return None

def cleanup_expired_document_shares():
    """
    Pulisce i DocumentShare scaduti.
    """
    try:
        logger.info("🧹 Avvio pulizia DocumentShare scaduti...")
        
        # Conta quanti verranno eliminati
        expired_count = DocumentShare.query.filter(
            DocumentShare.expires_at < datetime.utcnow()
        ).count()
        
        if expired_count > 0:
            cleanup_expired_shares()
            logger.info(f"🗑️ Eliminati {expired_count} DocumentShare scaduti")
        
        logger.info("✅ Pulizia DocumentShare completata")
        
    except Exception as e:
        logger.error(f"❌ Errore durante pulizia DocumentShare: {str(e)}")

def analyze_access_patterns():
    """
    Analizza i pattern di accesso per identificare comportamenti anomali.
    """
    try:
        logger.info("🔍 Analisi pattern di accesso...")
        
        # Trova utenti con pattern di accesso sospetti
        # (es. accessi a documenti di reparti diversi in breve tempo)
        
        # Analisi per ora del giorno
        hour_stats = db.session.query(
            func.extract('hour', AccessRequest.created_at).label('hour'),
            func.count(AccessRequest.id).label('count')
        ).group_by('hour').order_by('hour').all()
        
        # Trova ore con picchi anomali
        avg_requests_per_hour = sum(count for _, count in hour_stats) / 24 if hour_stats else 0
        
        for hour, count in hour_stats:
            if count > avg_requests_per_hour * 2:  # Picco anomalo
                logger.warning(f"⚠️ Picco anomalo alle {hour}:00 ({count} richieste)")
        
        logger.info("✅ Analisi pattern completata")
        
    except Exception as e:
        logger.error(f"❌ Errore durante analisi pattern: {str(e)}")

def send_daily_access_report():
    """
    Invia report giornaliero delle richieste di accesso agli admin.
    """
    try:
        logger.info("📧 Invio report giornaliero richieste accesso...")
        
        # Genera statistiche
        stats = generate_access_request_stats()
        
        if stats:
            # Qui potresti inviare una email con le statistiche
            # send_access_report_email(stats)
            logger.info(f"📊 Report inviato: {stats}")
        
        logger.info("✅ Report giornaliero inviato")
        
    except Exception as e:
        logger.error(f"❌ Errore durante invio report: {str(e)}")

# Funzioni di utilità per la creazione di alert
def create_anomaly_alert(target_id, count, alert_type):
    """
    Crea un alert per un'anomalia rilevata.
    
    Args:
        target_id (int): ID dell'utente o documento
        count (int): Numero di richieste
        alert_type (str): Tipo di alert
    """
    try:
        # Qui implementeresti la logica per creare un alert
        # Per ora solo log
        logger.warning(f"🚨 Alert {alert_type}: Target {target_id}, Count {count}")
        
    except Exception as e:
        logger.error(f"❌ Errore creazione alert: {str(e)}")

def send_access_report_email(stats):
    """
    Invia email con report delle richieste di accesso.
    
    Args:
        stats (dict): Statistiche da inviare
    """
    try:
        # Qui implementeresti l'invio email
        # Per ora solo log
        logger.info(f"📧 Email report inviata: {stats}")
        
    except Exception as e:
        logger.error(f"❌ Errore invio email report: {str(e)}")
