"""
API KPI per approvazioni e statistiche.
Fornisce endpoint per dashboard e reporting.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from models import db, User
from security.decorators import log_audit, rate_limit
import logging

logger = logging.getLogger(__name__)

approvals_kpi_bp = Blueprint('approvals_kpi', __name__)

# Mock data per demo
class MockApprovalRequest:
    def __init__(self, id, user_id, risk_score, amount, status, created_at, approved_at=None):
        self.id = id
        self.user_id = user_id
        self.risk_score = risk_score
        self.amount = amount
        self.status = status
        self.created_at = created_at
        self.approved_at = approved_at

# Dati mock per demo
mock_approvals = [
    MockApprovalRequest(1, 1, 25, 150.0, 'approved', datetime.now() - timedelta(hours=2), datetime.now() - timedelta(hours=1)),
    MockApprovalRequest(2, 2, 45, 500.0, 'pending', datetime.now() - timedelta(hours=3)),
    MockApprovalRequest(3, 3, 75, 7500.0, 'approved', datetime.now() - timedelta(hours=6), datetime.now() - timedelta(hours=4)),
    MockApprovalRequest(4, 1, 30, 200.0, 'denied', datetime.now() - timedelta(hours=1)),
    MockApprovalRequest(5, 4, 60, 3000.0, 'pending', datetime.now() - timedelta(hours=5)),
    MockApprovalRequest(6, 2, 80, 10000.0, 'escalated', datetime.now() - timedelta(hours=8)),
    MockApprovalRequest(7, 3, 20, 100.0, 'approved', datetime.now() - timedelta(hours=1), datetime.now() - timedelta(minutes=30)),
    MockApprovalRequest(8, 1, 50, 2500.0, 'pending', datetime.now() - timedelta(hours=4)),
]

@approvals_kpi_bp.route('/api/approvals/stats/summary')
@login_required
@rate_limit(max_requests=100, window_seconds=60)
@log_audit('view_approvals_summary', 'approvals_kpi')
def approvals_summary():
    """Ottiene statistiche riassuntive delle approvazioni."""
    try:
        total_requests = len(mock_approvals)
        
        # Conteggio per status
        count_by_status = {}
        for approval in mock_approvals:
            status = approval.status
            count_by_status[status] = count_by_status.get(status, 0) + 1
        
        # Tempo medio di decisione
        approved_requests = [a for a in mock_approvals if a.status == 'approved' and a.approved_at]
        avg_time_to_decision_sec = 0
        if approved_requests:
            total_time = sum((a.approved_at - a.created_at).total_seconds() for a in approved_requests)
            avg_time_to_decision_sec = total_time / len(approved_requests)
        
        # Bucket di rischio
        risk_buckets = {"0-39": 0, "40-69": 0, "70-100": 0}
        for approval in mock_approvals:
            if approval.risk_score <= 39:
                risk_buckets["0-39"] += 1
            elif approval.risk_score <= 69:
                risk_buckets["40-69"] += 1
            else:
                risk_buckets["70-100"] += 1
        
        return jsonify({
            "count_by_status": count_by_status,
            "total_requests": total_requests,
            "avg_time_to_decision_sec": round(avg_time_to_decision_sec, 2),
            "risk_buckets": risk_buckets,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Errore statistiche approvazioni: {e}")
        return jsonify({"error": "Errore calcolo statistiche"}), 500

@approvals_kpi_bp.route('/api/approvals/stats/trends')
@login_required
@rate_limit(max_requests=50, window_seconds=60)
@log_audit('view_approvals_trends', 'approvals_kpi')
def approvals_trends():
    """
    Ottiene trend temporali delle approvazioni.
    
    Returns:
        JSON con trend approvazioni
    """
    try:
        # Raggruppa per giorno (ultimi 7 giorni)
        trends = {}
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).date()
            trends[date.isoformat()] = {
                "total": 0,
                "approved": 0,
                "denied": 0,
                "pending": 0
            }
        
        # Popola trend dai dati mock
        for approval in mock_approvals:
            approval_date = approval.created_at.date()
            if approval_date in trends:
                trends[approval_date.isoformat()]["total"] += 1
                trends[approval_date.isoformat()][approval.status] += 1
        
        return jsonify({
            "trends": trends,
            "period": "7_days",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Errore trend approvazioni: {e}")
        return jsonify({"error": "Errore calcolo trend"}), 500

@approvals_kpi_bp.route('/api/approvals/stats/performance')
@login_required
@rate_limit(max_requests=50, window_seconds=60)
@log_audit('view_approvals_performance', 'approvals_kpi')
def approvals_performance():
    """
    Ottiene metriche di performance delle approvazioni.
    
    Returns:
        JSON con metriche performance
    """
    try:
        # Calcola metriche di performance
        total_requests = len(mock_approvals)
        approved_requests = len([a for a in mock_approvals if a.status == 'approved'])
        denied_requests = len([a for a in mock_approvals if a.status == 'denied'])
        pending_requests = len([a for a in mock_approvals if a.status == 'pending'])
        
        # Tassi di approvazione
        approval_rate = (approved_requests / total_requests * 100) if total_requests > 0 else 0
        denial_rate = (denied_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Tempo medio per livello di rischio
        risk_performance = {}
        for risk_range in ["0-39", "40-69", "70-100"]:
            if risk_range == "0-39":
                risk_requests = [a for a in mock_approvals if a.risk_score <= 39 and a.status == 'approved' and a.approved_at]
            elif risk_range == "40-69":
                risk_requests = [a for a in mock_approvals if 40 <= a.risk_score <= 69 and a.status == 'approved' and a.approved_at]
            else:
                risk_requests = [a for a in mock_approvals if a.risk_score >= 70 and a.status == 'approved' and a.approved_at]
            
            avg_time = 0
            if risk_requests:
                total_time = sum((a.approved_at - a.created_at).total_seconds() for a in risk_requests)
                avg_time = total_time / len(risk_requests)
            
            risk_performance[risk_range] = round(avg_time / 60, 2)  # in minuti
        
        # SLA compliance (approvazioni entro 4 ore)
        sla_compliant = 0
        sla_total = 0
        for approval in mock_approvals:
            if approval.status == 'approved' and approval.approved_at:
                sla_total += 1
                if (approval.approved_at - approval.created_at) <= timedelta(hours=4):
                    sla_compliant += 1
        
        sla_compliance_rate = (sla_compliant / sla_total * 100) if sla_total > 0 else 0
        
        return jsonify({
            "total_requests": total_requests,
            "approval_rate": round(approval_rate, 2),
            "denial_rate": round(denial_rate, 2),
            "pending_count": pending_requests,
            "risk_performance": risk_performance,
            "sla_compliance_rate": round(sla_compliance_rate, 2),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Errore performance approvazioni: {e}")
        return jsonify({"error": "Errore calcolo performance"}), 500

@approvals_kpi_bp.route('/api/approvals/stats/realtime')
@login_required
@rate_limit(max_requests=200, window_seconds=60)
@log_audit('view_approvals_realtime', 'approvals_kpi')
def approvals_realtime():
    """Ottiene statistiche real-time delle approvazioni."""
    try:
        now = datetime.now()
        
        # Richieste ultime 24 ore
        last_24h = [a for a in mock_approvals if (now - a.created_at) <= timedelta(hours=24)]
        
        # Richieste ultima ora
        last_1h = [a for a in mock_approvals if (now - a.created_at) <= timedelta(hours=1)]
        
        # Richieste in escalation
        escalated = [a for a in mock_approvals if a.status == 'escalated']
        
        # Richieste che richiedono due approvazioni
        two_man_rule = [a for a in mock_approvals if a.risk_score >= 70 or a.amount >= 5000]
        
        return jsonify({
            "last_24h": {
                "total": len(last_24h),
                "approved": len([a for a in last_24h if a.status == 'approved']),
                "pending": len([a for a in last_24h if a.status == 'pending']),
                "denied": len([a for a in last_24h if a.status == 'denied'])
            },
            "last_1h": {
                "total": len(last_1h),
                "approved": len([a for a in last_1h if a.status == 'approved']),
                "pending": len([a for a in last_1h if a.status == 'pending'])
            },
            "escalated_count": len(escalated),
            "two_man_rule_count": len(two_man_rule),
            "timestamp": now.isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Errore statistiche real-time: {e}")
        return jsonify({"error": "Errore calcolo statistiche real-time"}), 500

@approvals_kpi_bp.route('/api/approvals/stats/export')
@login_required
@rate_limit(max_requests=20, window_seconds=60)
@log_audit('export_approvals_stats', 'approvals_kpi')
def approvals_export():
    """
    Esporta statistiche approvazioni in formato JSON.
    
    Returns:
        JSON con tutte le statistiche
    """
    try:
        # Raccogli tutte le statistiche
        summary = approvals_summary().get_json()
        trends = approvals_trends().get_json()
        performance = approvals_performance().get_json()
        realtime = approvals_realtime().get_json()
        
        export_data = {
            "summary": summary,
            "trends": trends,
            "performance": performance,
            "realtime": realtime,
            "exported_at": datetime.utcnow().isoformat(),
            "exported_by": current_user.email
        }
        
        return jsonify(export_data)
        
    except Exception as e:
        logger.error(f"❌ Errore export statistiche: {e}")
        return jsonify({"error": "Errore export statistiche"}), 500
