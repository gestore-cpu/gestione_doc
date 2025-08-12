"""
API per approvazioni con idempotency e policy granulari.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from security.decorators import require_idempotency, require_json_content_type, validate_required_fields, log_audit
from security.policies import ApprovalRequest, approval_workflow
from app_socket import emit_approval_event, emit_escalation_alert
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

approvals_api_bp = Blueprint('approvals_api', __name__)

# Mock storage per demo
approval_requests = {}
request_counter = 1

@approvals_api_bp.route('/api/approvals/create', methods=['POST'])
@login_required
@require_json_content_type()
@validate_required_fields('risk_score', 'amount', 'request_type', 'description')
@require_idempotency()
@log_audit('create_approval_request', 'approval')
def create_approval_request():
    """Crea una nuova richiesta di approvazione."""
    try:
        global request_counter
        
        data = request.get_json()
        
        # Crea richiesta
        approval_req = ApprovalRequest(
            id=request_counter,
            user_id=current_user.id,
            user_email=current_user.email,
            user_role=current_user.role,
            risk_score=data['risk_score'],
            amount=data['amount'],
            request_type=data['request_type'],
            description=data['description'],
            created_at=datetime.utcnow()
        )
        
        # Processa richiesta
        result = approval_workflow.process_approval_request(approval_req)
        
        # Salva richiesta
        approval_requests[request_counter] = approval_req
        request_counter += 1
        
        # Emetti evento WebSocket
        emit_approval_event({
            'type': 'request_created',
            'request_id': approval_req.id,
            'user_email': approval_req.user_email,
            'risk_score': approval_req.risk_score,
            'amount': approval_req.amount,
            'status': approval_req.status.value
        })
        
        return jsonify({
            'status': 'success',
            'request_id': approval_req.id,
            'workflow_result': result,
            'message': 'Richiesta di approvazione creata'
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Errore creazione richiesta approvazione: {e}")
        return jsonify({'error': 'Errore creazione richiesta'}), 500

@approvals_api_bp.route('/api/approvals/<int:request_id>/approve', methods=['POST'])
@login_required
@require_json_content_type()
@validate_required_fields('decision')
@require_idempotency()
@log_audit('approval_decision', 'approval')
def approve_request(request_id):
    """Approva o nega una richiesta di approvazione."""
    try:
        if request_id not in approval_requests:
            return jsonify({'error': 'Richiesta non trovata'}), 404
        
        approval_req = approval_requests[request_id]
        data = request.get_json()
        
        # Registra decisione
        result = approval_workflow.record_decision(
            approval_req,
            current_user.id,
            current_user.role,
            data['decision'],
            data.get('comment')
        )
        
        # Emetti evento WebSocket
        emit_approval_event({
            'type': 'decision_made',
            'request_id': approval_req.id,
            'approver_email': current_user.email,
            'decision': data['decision'],
            'status': approval_req.status.value
        })
        
        # Controlla escalation
        escalation_result = approval_workflow.check_escalation(approval_req)
        if escalation_result['status'] == 'escalated':
            emit_escalation_alert({
                'type': 'request_escalated',
                'request_id': approval_req.id,
                'reason': escalation_result['escalation_reason']
            })
        
        return jsonify({
            'status': 'success',
            'decision_result': result,
            'escalation_result': escalation_result,
            'message': 'Decisione registrata'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Errore decisione approvazione: {e}")
        return jsonify({'error': 'Errore registrazione decisione'}), 500

@approvals_api_bp.route('/api/approvals/bulk-decision', methods=['POST'])
@login_required
@require_json_content_type()
@validate_required_fields('ids', 'decision')
@require_idempotency()
@log_audit('bulk_approval_decision', 'approval')
def bulk_approval_decision():
    """Decisione bulk su multiple richieste."""
    try:
        data = request.get_json()
        request_ids = data['ids']
        decision = data['decision']
        
        results = []
        for req_id in request_ids:
            if req_id in approval_requests:
                approval_req = approval_requests[req_id]
                
                result = approval_workflow.record_decision(
                    approval_req,
                    current_user.id,
                    current_user.role,
                    decision,
                    data.get('comment')
                )
                
                results.append({
                    'request_id': req_id,
                    'result': result
                })
                
                # Emetti evento per ogni richiesta
                emit_approval_event({
                    'type': 'bulk_decision',
                    'request_id': req_id,
                    'approver_email': current_user.email,
                    'decision': decision,
                    'status': approval_req.status.value
                })
            else:
                results.append({
                    'request_id': req_id,
                    'result': {'status': 'error', 'message': 'Richiesta non trovata'}
                })
        
        return jsonify({
            'status': 'success',
            'results': results,
            'message': f'Decisione bulk applicata a {len(request_ids)} richieste'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Errore decisione bulk: {e}")
        return jsonify({'error': 'Errore decisione bulk'}), 500

@approvals_api_bp.route('/api/approvals/list')
@login_required
@log_audit('list_approvals', 'approval')
def list_approvals():
    """Lista richieste di approvazione."""
    try:
        status_filter = request.args.get('status')
        limit = min(int(request.args.get('limit', 50)), 100)
        
        filtered_requests = []
        for req in approval_requests.values():
            if status_filter and req.status.value != status_filter:
                continue
            
            filtered_requests.append({
                'id': req.id,
                'user_email': req.user_email,
                'risk_score': req.risk_score,
                'amount': req.amount,
                'request_type': req.request_type,
                'status': req.status.value,
                'created_at': req.created_at.isoformat(),
                'first_approver_id': req.first_approver_id,
                'second_approver_id': req.second_approver_id
            })
        
        # Ordina per data creazione (più recenti prima)
        filtered_requests.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'requests': filtered_requests[:limit],
            'total': len(filtered_requests),
            'limit': limit
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Errore lista approvazioni: {e}")
        return jsonify({'error': 'Errore recupero lista'}), 500
