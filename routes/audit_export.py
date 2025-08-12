"""
API per export audit log in formato CSV/NDJSON.
"""

from flask import Blueprint, Response, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from security.decorators import log_audit, rate_limit
import json
import csv
import io
import logging

logger = logging.getLogger(__name__)

audit_export_bp = Blueprint('audit_export', __name__)

# Mock audit log per demo
class MockAuditLog:
    def __init__(self, ts, actor, action, resource, payload_hash):
        self.ts = ts
        self.actor = actor
        self.action = action
        self.resource = resource
        self.payload_hash = payload_hash
    
    def to_dict(self):
        return {
            "ts": self.ts.isoformat(),
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "payload_hash": self.payload_hash
        }

# Dati mock per demo
mock_audit_logs = [
    MockAuditLog(datetime.now() - timedelta(hours=1), "admin@example.com", "approval_decision", "approval_request_123", "abc123hash"),
    MockAuditLog(datetime.now() - timedelta(hours=2), "user@example.com", "create_request", "approval_request_124", "def456hash"),
    MockAuditLog(datetime.now() - timedelta(hours=3), "security@example.com", "escalation_trigger", "approval_request_125", "ghi789hash"),
]

@audit_export_bp.route('/agents/audit-log/export')
@login_required
@rate_limit(max_requests=10, window_seconds=60)
@log_audit('export_audit_log', 'audit_export')
def audit_export():
    """Esporta audit log in formato CSV o NDJSON."""
    try:
        fmt = request.args.get("fmt", "csv").lower()
        limit = min(int(request.args.get("limit", 5000)), 10000)
        
        logs = mock_audit_logs[:limit]
        
        if fmt == "ndjson":
            def generate_ndjson():
                for log in logs:
                    yield json.dumps(log.to_dict(), ensure_ascii=False) + "\n"
            
            return Response(
                generate_ndjson(),
                mimetype="application/x-ndjson",
                headers={"Content-Disposition": f"attachment; filename=audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ndjson"}
            )
        
        else:  # CSV
            def generate_csv():
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["timestamp", "actor", "action", "resource", "payload_hash"])
                for log in logs:
                    writer.writerow([log.ts.isoformat(), log.actor, log.action, log.resource, log.payload_hash])
                return output.getvalue()
            
            csv_content = generate_csv()
            return Response(
                csv_content,
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment; filename=audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
        
    except Exception as e:
        logger.error(f"❌ Errore export audit log: {e}")
        return jsonify({"error": "Errore export audit log"}), 500

@audit_export_bp.route('/agents/audit-log/stats')
@login_required
@rate_limit(max_requests=50, window_seconds=60)
@log_audit('view_audit_stats', 'audit_export')
def audit_stats():
    """
    Ottiene statistiche dell'audit log.
    
    Returns:
        JSON con statistiche audit log
    """
    try:
        now = datetime.now()
        
        # Statistiche generali
        total_logs = len(mock_audit_logs)
        
        # Log ultime 24 ore
        last_24h = [log for log in mock_audit_logs if (now - log.ts) <= timedelta(hours=24)]
        
        # Log ultima ora
        last_1h = [log for log in mock_audit_logs if (now - log.ts) <= timedelta(hours=1)]
        
        # Conteggio per azione
        action_counts = {}
        for log in mock_audit_logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1
        
        # Conteggio per attore
        actor_counts = {}
        for log in mock_audit_logs:
            actor_counts[log.actor] = actor_counts.get(log.actor, 0) + 1
        
        # Top risorse
        resource_counts = {}
        for log in mock_audit_logs:
            resource_counts[log.resource] = resource_counts.get(log.resource, 0) + 1
        
        return jsonify({
            "total_logs": total_logs,
            "last_24h": len(last_24h),
            "last_1h": len(last_1h),
            "action_counts": action_counts,
            "actor_counts": actor_counts,
            "top_resources": dict(sorted(resource_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "timestamp": now.isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Errore statistiche audit log: {e}")
        return jsonify({"error": "Errore calcolo statistiche audit log"}), 500

@audit_export_bp.route('/agents/audit-log/search')
@login_required
@rate_limit(max_requests=100, window_seconds=60)
@log_audit('search_audit_log', 'audit_export')
def audit_search():
    """
    Cerca nell'audit log.
    
    Query Parameters:
        q: Query di ricerca
        actor: Filtro per attore
        action: Filtro per azione
        resource: Filtro per risorsa
        limit: Numero massimo di risultati
        
    Returns:
        JSON con risultati ricerca
    """
    try:
        # Parametri
        query = request.args.get("q", "").lower()
        actor = request.args.get("actor", "").lower()
        action = request.args.get("action", "").lower()
        resource = request.args.get("resource", "").lower()
        limit = min(int(request.args.get("limit", 100)), 1000)
        
        # Filtra log
        results = []
        for log in mock_audit_logs:
            # Filtri
            if actor and actor not in log.actor.lower():
                continue
            if action and action not in log.action.lower():
                continue
            if resource and resource not in log.resource.lower():
                continue
            
            # Query generale
            if query:
                searchable = f"{log.actor} {log.action} {log.resource}".lower()
                if query not in searchable:
                    continue
            
            results.append(log.to_dict())
            
            if len(results) >= limit:
                break
        
        return jsonify({
            "results": results,
            "total_found": len(results),
            "query": {
                "q": query,
                "actor": actor,
                "action": action,
                "resource": resource,
                "limit": limit
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Errore ricerca audit log: {e}")
        return jsonify({"error": "Errore ricerca audit log"}), 500
