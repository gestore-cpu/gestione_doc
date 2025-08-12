"""
Route per il risk scoring delle richieste di accesso.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import AccessRequest, User, Document
from extensions import db
from decorators import admin_required
from utils.risk_scoring import get_risk_statistics, get_high_risk_requests, apply_risk_score_to_request

risk_bp = Blueprint('risk', __name__, url_prefix='/admin')

@risk_bp.route("/access_requests/risk_scoring", methods=["GET"])
@login_required
@admin_required
def risk_scoring_dashboard():
    """
    Dashboard per la gestione del risk scoring delle richieste di accesso.
    """
    # Statistiche generali
    stats = get_risk_statistics()
    
    # Richieste ad alto rischio
    high_risk_requests = get_high_risk_requests(limit=20)
    
    # Filtri
    risk_filter = request.args.get("risk_level", "")
    status_filter = request.args.get("status", "")
    
    # Query base
    query = AccessRequest.query.join(User).join(Document)
    
    # Applica filtri
    if risk_filter:
        if risk_filter == "high":
            query = query.filter(AccessRequest.risk_score >= 70)
        elif risk_filter == "medium":
            query = query.filter(AccessRequest.risk_score.between(40, 69))
        elif risk_filter == "low":
            query = query.filter(AccessRequest.risk_score < 40)
    
    if status_filter:
        query = query.filter(AccessRequest.status == status_filter)
    
    # Ordina per risk score decrescente
    requests = query.order_by(AccessRequest.risk_score.desc().nullslast()).limit(50).all()
    
    return render_template(
        "admin/risk_scoring_dashboard.html",
        stats=stats,
        high_risk_requests=high_risk_requests,
        requests=requests,
        risk_filter=risk_filter,
        status_filter=status_filter
    )


@risk_bp.route("/access_requests/<int:request_id>/calculate_risk", methods=["POST"])
@login_required
@admin_required
def calculate_request_risk(request_id):
    """
    Calcola manualmente il risk score per una richiesta specifica.
    """
    try:
        success = apply_risk_score_to_request(request_id)
        
        if success:
            flash("✅ Risk score calcolato con successo.", "success")
        else:
            flash("❌ Errore nel calcolo del risk score.", "danger")
            
    except Exception as e:
        flash(f"❌ Errore: {str(e)}", "danger")
    
    return redirect(request.referrer or url_for("risk.risk_scoring_dashboard"))


@risk_bp.route("/access_requests/bulk_risk_calculation", methods=["POST"])
@login_required
@admin_required
def bulk_risk_calculation():
    """
    Calcola il risk score per tutte le richieste pendenti senza risk score.
    """
    try:
        # Trova richieste senza risk score
        requests_without_risk = AccessRequest.query.filter(
            AccessRequest.risk_score.is_(None),
            AccessRequest.status == "pending"
        ).all()
        
        processed = 0
        errors = 0
        
        for req in requests_without_risk:
            try:
                if apply_risk_score_to_request(req.id):
                    processed += 1
                else:
                    errors += 1
            except Exception:
                errors += 1
        
        flash(f"✅ Processate {processed} richieste, {errors} errori.", "info")
        
    except Exception as e:
        flash(f"❌ Errore nel calcolo bulk: {str(e)}", "danger")
    
    return redirect(url_for("risk.risk_scoring_dashboard"))


@risk_bp.route("/access_requests/risk_analysis/<int:request_id>", methods=["GET"])
@login_required
@admin_required
def view_risk_analysis(request_id):
    """
    Visualizza l'analisi dettagliata del rischio per una richiesta.
    """
    request_obj = AccessRequest.query.get_or_404(request_id)
    
    if not request_obj.has_risk_analysis:
        flash("❌ Nessuna analisi del rischio disponibile per questa richiesta.", "warning")
        return redirect(request.referrer or url_for("risk.risk_scoring_dashboard"))
    
    return render_template(
        "admin/risk_analysis_detail.html",
        request_obj=request_obj
    )
