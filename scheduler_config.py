"""
Configurazione APScheduler per i job di detection degli alert.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from jobs.access_request_detection_job import detect_access_request_anomalies, expire_old_access_requests, cleanup_old_alerts
from services.download_alert_service import run_download_detection
from services.ai.gpt_provider import GptProvider
from services.document_service import list_documents_for_autotag, get_document_text, save_tags
from services.manus_sync import sync_manuals, sync_courses, sync_completions_for_course
from models import ManusCourseLink
import logging
from datetime import datetime

log = logging.getLogger(__name__)
_gpt = GptProvider()

logger = logging.getLogger(__name__)

def create_scheduler():
    """
    Crea e configura il scheduler APScheduler.
    """
    # Configurazione jobstore (SQLite per persistenza)
    jobstores = {
        'default': SQLAlchemyJobStore(url='sqlite:///jobs.db')
    }
    
    # Configurazione executor
    executors = {
        'default': ThreadPoolExecutor(20),
        'processpool': ThreadPoolExecutor(5)
    }
    
    # Configurazione job defaults
    job_defaults = {
        'coalesce': False,
        'max_instances': 3
    }
    
    # Crea scheduler
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='UTC'
    )
    
    return scheduler

def setup_jobs(scheduler):
    """
    Configura i job nel scheduler.
    """
    try:
        # Job per detection anomalie ogni 10 minuti
        scheduler.add_job(
            func=detect_access_request_anomalies,
            trigger='interval',
            minutes=10,
            id='detect_access_request_anomalies',
            name='Detection Anomalie Richieste Accesso',
            replace_existing=True
        )
        
        # Job per scadenza richieste ogni ora
        scheduler.add_job(
            func=expire_old_access_requests,
            trigger='interval',
            hours=1,
            id='expire_old_access_requests',
            name='Scadenza Richieste Accesso',
            replace_existing=True
        )
        
        # Job per pulizia alert vecchi ogni giorno
        scheduler.add_job(
            func=cleanup_old_alerts,
            trigger='cron',
            hour=2,  # Alle 2:00 UTC
            id='cleanup_old_alerts',
            name='Pulizia Alert Vecchi',
            replace_existing=True
        )
        
        # Job per detection download sospetti ogni 10 minuti
        scheduler.add_job(
            func=detect_suspicious_downloads,
            trigger='interval',
            minutes=10,
            id='detect_suspicious_downloads',
            name='Detection Download Sospetti',
            replace_existing=True
        )
        
        # Job per autotagging notturno alle 2:30
        scheduler.add_job(
            func=job_ai_autotag_recent,
            trigger='cron',
            hour=2,
            minute=30,
            id='ai_autotag_recent',
            name='AI Autotagging Documenti',
            replace_existing=True
        )
        
        # Job per sync Manus notturno alle 2:10
        scheduler.add_job(
            func=job_manus_sync_nightly,
            trigger='cron',
            hour=2,
            minute=10,
            id='manus_sync_nightly',
            name='Sync Manus Notturno',
            replace_existing=True
        )
        
        # Job per sync completamenti Manus ogni ora (minuto 5)
        scheduler.add_job(
            func=job_manus_completions_hourly,
            trigger='cron',
            minute=5,
            id='manus_compl_hourly',
            name='Sync Completamenti Manus',
            replace_existing=True
        )
            minute=30,
            id='ai_autotag_recent',
            name='Autotagging AI Documenti Recenti',
            replace_existing=True
        )
        
        logger.info("✅ Job schedulati configurati correttamente")
        
    except Exception as e:
        logger.error(f"❌ Errore nella configurazione dei job: {str(e)}")
        raise

def job_ai_autotag_recent():
    """Job per autotagging notturno dei documenti recenti."""
    try:
        log.info("🤖 Avvio job autotagging AI documenti recenti...")
        docs = list_documents_for_autotag(limit=200)
        processed, errors = 0, 0
        
        for d in docs:
            try:
                text = get_document_text(d["id"])
                tags = _gpt.tag(text)
                save_tags(d["id"], tags)
                processed += 1
                log.info(f"✅ Tagged doc_id={d['id']} - {d['title']}")
            except Exception as e:
                errors += 1
                log.exception(f"❌ [AI-AUTOTAG] doc_id={d.get('id')} error={e}")
        
        log.info(f"✅ [AI-AUTOTAG] completato: processed={processed} errors={errors}")
    except Exception as e:
        log.exception(f"❌ Errore job autotagging: {e}")

def detect_suspicious_downloads():
    """
    Wrapper per il job di detection download sospetti.
    """
    try:
        logger.info("🔍 Avvio job detection download sospetti...")
        alerts_created = run_download_detection(datetime.utcnow())
        logger.info(f"✅ Job detection completato: {len(alerts_created)} alert creati")
    except Exception as e:
        logger.error(f"❌ Errore job detection: {str(e)}")

def job_manus_sync_nightly():
    """
    Job notturno per sync completo Manus.
    """
    try:
        # TODO: iterare sulle aziende configurate (id, ref)
        # Esempio statico per demo
        azienda_id = 1
        azienda_ref = "mercury"
        
        log.info(f"[MANUS-SYNC] Avvio sync notturno per azienda {azienda_id}")
        
        # Sync manuali
        sync_manuals(azienda_id, azienda_ref)
        
        # Sync corsi
        sync_courses(azienda_id, azienda_ref)
        
        log.info(f"[MANUS-SYNC] Sync notturno completato per azienda {azienda_id}")
        
    except Exception as e:
        log.exception(f"[MANUS-SYNC] job error: {e}")

def job_manus_completions_hourly():
    """
    Job orario per sync completamenti Manus.
    """
    try:
        course_links = ManusCourseLink.query.all()
        processed, errors = 0, 0
        
        for link in course_links:
            try:
                sync_completions_for_course(link)
                processed += 1
            except Exception as e:
                errors += 1
                log.exception(f"[MANUS-COMPL] link_id={link.id} error={e}")
        
        log.info(f"[MANUS-COMPL] done processed={processed} errors={errors}")
        
    except Exception as e:
        log.exception(f"[MANUS-COMPL] job error: {e}")

def start_scheduler():
    """
    Avvia il scheduler.
    """
    try:
        scheduler = create_scheduler()
        setup_jobs(scheduler)
        scheduler.start()
        logger.info("🚀 Scheduler APScheduler avviato")
        return scheduler
    except Exception as e:
        logger.error(f"❌ Errore nell'avvio del scheduler: {str(e)}")
        raise
