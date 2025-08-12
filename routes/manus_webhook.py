"""
Route per i webhook di Manus Core.
Gestisce la verifica HMAC e il routing degli eventi.
"""

import hmac
import hashlib
from flask import Blueprint, request, jsonify, current_app
from services.manus_sync import sync_manuals, sync_courses, sync_completions_for_course
from models import ManusCourseLink
import logging

logger = logging.getLogger(__name__)

manus_webhook_bp = Blueprint("manus_webhook", __name__)

def _verify_signature(body: bytes, sig: str, secret: str) -> bool:
    """
    Verifica la firma HMAC del webhook.
    
    Args:
        body (bytes): Body della richiesta
        sig (str): Firma ricevuta nell'header
        secret (str): Secret per la verifica
        
    Returns:
        bool: True se la firma è valida
    """
    if not secret or not sig:
        return False
    
    # Calcola HMAC SHA256
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    
    # Confronto sicuro
    return hmac.compare_digest(mac, sig)

@manus_webhook_bp.post("/manus/hooks")
def manus_hooks():
    """
    Endpoint per ricevere webhook da Manus.
    
    Gestisce gli eventi:
    - MANUAL_UPDATED: Aggiorna manuali
    - COURSE_COMPLETED: Sincronizza completamenti
    - COURSE_UPDATED: Aggiorna corsi
    """
    try:
        # Verifica firma HMAC
        secret = current_app.config.get("MANUS_WEBHOOK_SECRET", "")
        sig = request.headers.get("X-Manus-Signature")
        raw = request.get_data()
        
        if not _verify_signature(raw, sig, secret):
            logger.warning("❌ Webhook con firma non valida")
            return jsonify({"error": "invalid signature"}), 401
        
        # Estrai dati
        event = request.headers.get("X-Manus-Event")
        data = request.get_json() or {}
        
        logger.info(f"📨 Webhook ricevuto: {event}")
        
        # Route eventi
        if event == "MANUAL_UPDATED":
            azienda_id = data.get("azienda_id")
            azienda_ref = data.get("azienda_ref")
            if azienda_id and azienda_ref:
                sync_manuals(azienda_id, azienda_ref)
                logger.info(f"✅ Sync manuali completato per webhook")
            else:
                logger.error("❌ Dati mancanti per MANUAL_UPDATED")
                return jsonify({"error": "missing data"}), 400
                
        elif event == "COURSE_COMPLETED":
            course_id = data.get("course_id")
            if course_id:
                link = ManusCourseLink.query.filter_by(manus_course_id=course_id).first()
                if link:
                    since_iso = data.get("since")
                    sync_completions_for_course(link, since_iso)
                    logger.info(f"✅ Sync completamenti completato per corso {course_id}")
                else:
                    logger.warning(f"⚠️ Link corso non trovato per {course_id}")
            else:
                logger.error("❌ Course ID mancante per COURSE_COMPLETED")
                return jsonify({"error": "missing course_id"}), 400
                
        elif event == "COURSE_UPDATED":
            azienda_id = data.get("azienda_id")
            azienda_ref = data.get("azienda_ref")
            if azienda_id and azienda_ref:
                sync_courses(azienda_id, azienda_ref)
                logger.info(f"✅ Sync corsi completato per webhook")
            else:
                logger.error("❌ Dati mancanti per COURSE_UPDATED")
                return jsonify({"error": "missing data"}), 400
                
        else:
            logger.warning(f"⚠️ Evento non gestito: {event}")
            return jsonify({"error": "unsupported event"}), 400
        
        return jsonify({"status": "ok"})
        
    except Exception as e:
        logger.error(f"❌ Errore webhook: {e}")
        return jsonify({"error": "internal error"}), 500

@manus_webhook_bp.route("/manus/hooks/health", methods=["GET", "HEAD"])
def manus_webhook_health():
    """
    Endpoint di health check per i webhook.
    Supporta GET e HEAD per health check.
    """
    return jsonify({
        "status": "ok",
        "service": "manus_webhook",
        "timestamp": "2024-01-01T00:00:00Z"
    })
