"""
Route admin per la gestione Manus Core.
Endpoint protetti per sync manuale e monitoraggio.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from services.manus_sync import sync_manuals, sync_courses, sync_completions_for_course, sync_all_for_company
from models import ManusCourseLink, ManusManualLink, TrainingCompletionManus
import logging

logger = logging.getLogger(__name__)

manus_admin_bp = Blueprint("manus_admin", __name__)

def admin_required(f):
    """Decorator per verificare che l'utente sia admin."""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "authentication required"}), 401
        if not (current_user.role in ['admin', 'superadmin']):
            return jsonify({"error": "admin access required"}), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@manus_admin_bp.post("/manus/sync/manuals")
@login_required
@admin_required
def sync_manuals_route():
    """
    Endpoint per sync manuale dei manuali.
    
    Body:
        azienda_id (int): ID azienda locale
        azienda_ref (str): Riferimento azienda in Manus
    """
    try:
        data = request.get_json() or {}
        azienda_id = data.get("azienda_id")
        azienda_ref = data.get("azienda_ref")
        
        if not azienda_id or not azienda_ref:
            return jsonify({"error": "azienda_id and azienda_ref required"}), 400
        
        logger.info(f"🔄 Sync manuale manuali avviato da {current_user.email}")
        sync_manuals(azienda_id, azienda_ref)
        
        return jsonify({
            "status": "synced",
            "message": f"Sync manuali completato per azienda {azienda_id}",
            "user": current_user.email
        })
        
    except Exception as e:
        logger.error(f"❌ Errore sync manuale manuali: {e}")
        return jsonify({"error": str(e)}), 500

@manus_admin_bp.post("/manus/sync/courses")
@login_required
@admin_required
def sync_courses_route():
    """
    Endpoint per sync manuale dei corsi.
    
    Body:
        azienda_id (int): ID azienda locale
        azienda_ref (str): Riferimento azienda in Manus
    """
    try:
        data = request.get_json() or {}
        azienda_id = data.get("azienda_id")
        azienda_ref = data.get("azienda_ref")
        
        if not azienda_id or not azienda_ref:
            return jsonify({"error": "azienda_id and azienda_ref required"}), 400
        
        logger.info(f"🔄 Sync manuale corsi avviato da {current_user.email}")
        sync_courses(azienda_id, azienda_ref)
        
        return jsonify({
            "status": "synced",
            "message": f"Sync corsi completato per azienda {azienda_id}",
            "user": current_user.email
        })
        
    except Exception as e:
        logger.error(f"❌ Errore sync manuale corsi: {e}")
        return jsonify({"error": str(e)}), 500

@manus_admin_bp.post("/manus/sync/course/<int:link_id>/completions")
@login_required
@admin_required
def sync_compl_route(link_id: int):
    """
    Endpoint per sync manuale completamenti di un corso specifico.
    
    Args:
        link_id (int): ID del link corso
    """
    try:
        link = ManusCourseLink.query.get_or_404(link_id)
        
        logger.info(f"🔄 Sync manuale completamenti corso {link.manus_course_id} avviato da {current_user.email}")
        sync_completions_for_course(link)
        
        return jsonify({
            "status": "synced",
            "message": f"Sync completamenti completato per corso {link.manus_course_id}",
            "user": current_user.email
        })
        
    except Exception as e:
        logger.error(f"❌ Errore sync manuale completamenti: {e}")
        return jsonify({"error": str(e)}), 500

@manus_admin_bp.post("/manus/sync/all")
@login_required
@admin_required
def sync_all_route():
    """
    Endpoint per sync completo (manuali + corsi + completamenti).
    
    Body:
        azienda_id (int): ID azienda locale
        azienda_ref (str): Riferimento azienda in Manus
    """
    try:
        data = request.get_json() or {}
        azienda_id = data.get("azienda_id")
        azienda_ref = data.get("azienda_ref")
        
        if not azienda_id or not azienda_ref:
            return jsonify({"error": "azienda_id and azienda_ref required"}), 400
        
        logger.info(f"🔄 Sync completo avviato da {current_user.email}")
        sync_all_for_company(azienda_id, azienda_ref)
        
        return jsonify({
            "status": "synced",
            "message": f"Sync completo completato per azienda {azienda_id}",
            "user": current_user.email
        })
        
    except Exception as e:
        logger.error(f"❌ Errore sync completo: {e}")
        return jsonify({"error": str(e)}), 500

@manus_admin_bp.get("/manus/status")
@login_required
@admin_required
def manus_status():
    """
    Endpoint per lo status del sistema Manus.
    """
    try:
        # Statistiche
        manual_links = ManusManualLink.query.count()
        course_links = ManusCourseLink.query.count()
        completions = TrainingCompletionManus.query.count()
        
        # Ultimi sync
        latest_manual_sync = ManusManualLink.query.order_by(ManusManualLink.last_sync_at.desc()).first()
        latest_course_sync = ManusCourseLink.query.order_by(ManusCourseLink.last_sync_at.desc()).first()
        
        return jsonify({
            "status": "ok",
            "stats": {
                "manual_links": manual_links,
                "course_links": course_links,
                "completions": completions
            },
            "latest_sync": {
                "manuals": latest_manual_sync.last_sync_at.isoformat() if latest_manual_sync else None,
                "courses": latest_course_sync.last_sync_at.isoformat() if latest_course_sync else None
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Errore status Manus: {e}")
        return jsonify({"error": str(e)}), 500

@manus_admin_bp.get("/manus/links")
@login_required
@admin_required
def manus_links():
    """
    Endpoint per listare i link Manus.
    """
    try:
        # Manuali
        manual_links = ManusManualLink.query.all()
        manuals = []
        for link in manual_links:
            manuals.append({
                "id": link.id,
                "azienda_id": link.azienda_id,
                "documento_id": link.documento_id,
                "manus_manual_id": link.manus_manual_id,
                "manus_version": link.manus_version,
                "last_sync_at": link.last_sync_at.isoformat(),
                "documento_title": link.documento.title if link.documento else None
            })
        
        # Corsi
        course_links = ManusCourseLink.query.all()
        courses = []
        for link in course_links:
            courses.append({
                "id": link.id,
                "azienda_id": link.azienda_id,
                "requisito_id": link.requisito_id,
                "manus_course_id": link.manus_course_id,
                "last_sync_at": link.last_sync_at.isoformat(),
                "requisito_title": link.requisito.title if link.requisito else None
            })
        
        return jsonify({
            "status": "ok",
            "manuals": manuals,
            "courses": courses
        })
        
    except Exception as e:
        logger.error(f"❌ Errore list links Manus: {e}")
        return jsonify({"error": str(e)}), 500
