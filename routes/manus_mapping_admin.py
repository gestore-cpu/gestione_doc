"""
Route admin per gestione mapping utenti Manus e coverage formazione.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from services.manus_user_mapping import upsert_mapping, rebuild_coverage_for_user
from models import ManusUserMapping
import logging

logger = logging.getLogger(__name__)

manus_map_bp = Blueprint("manus_map_admin", __name__)

@manus_map_bp.get("/admin/manus/mapping/list")
@login_required
def mapping_list():
    """
    Lista tutti i mapping utenti Manus.
    """
    try:
        q = ManusUserMapping.query.order_by(ManusUserMapping.updated_at.desc()).limit(200).all()
        return jsonify([{
            "id": m.id,
            "manus_user_id": m.manus_user_id,
            "email": m.email,
            "syn_user_id": m.syn_user_id,
            "active": m.active
        } for m in q])
        
    except Exception as e:
        logger.error(f"❌ Errore list mappings: {e}")
        return jsonify({"error": str(e)}), 500

@manus_map_bp.post("/admin/manus/mapping/create")
@login_required
def mapping_create():
    """
    Crea un nuovo mapping utente Manus.
    """
    try:
        data = request.get_json() or {}
        m = upsert_mapping(
            data["manus_user_id"], 
            data["syn_user_id"], 
            data.get("email")
        )
        return jsonify({"ok": True, "id": m.id})
        
    except Exception as e:
        logger.error(f"❌ Errore create mapping: {e}")
        return jsonify({"error": str(e)}), 500

@manus_map_bp.post("/admin/manus/coverage/rebuild/<int:user_id>")
@login_required
def coverage_rebuild(user_id: int):
    """
    Ricostruisce i report di copertura formazione per un utente.
    """
    try:
        n = rebuild_coverage_for_user(user_id)
        return jsonify({"ok": True, "updated": n})
        
    except Exception as e:
        logger.error(f"❌ Errore rebuild coverage: {e}")
        return jsonify({"error": str(e)}), 500
