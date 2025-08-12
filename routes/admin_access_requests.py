"""
Route admin per la gestione delle richieste di accesso ai documenti.
"""

from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from models import AccessRequest, DocumentShare, Document, User, db
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from extensions import mail
from flask_mail import Message
from decorators import admin_required
from routes.access_requests import send_approval_notification

admin_access_requests_bp = Blueprint('admin_access_requests', __name__, url_prefix='/admin/access-requests')

# === DASHBOARD ADMIN ===
@admin_access_requests_bp.route('/', methods=['GET'])
@login_required
@admin_required
def access_requests_dashboard():
    """
    Dashboard per la gestione delle richieste di accesso.
    """
    # Filtri
    status_filter = request.args.get('status', '')
    file_id_filter = request.args.get('file_id', '')
    requested_by_filter = request.args.get('requested_by', '')
    owner_id_filter = request.args.get('owner_id', '')
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')
    
    # Query base
    query = AccessRequest.query.join(Document).join(User, AccessRequest.requested_by_user)
    
    # Applica filtri
    if status_filter:
        query = query.filter(AccessRequest.status == status_filter)
    
    if file_id_filter:
        query = query.filter(AccessRequest.file_id == file_id_filter)
    
    if requested_by_filter:
        query = query.filter(User.username.ilike(f'%{requested_by_filter}%'))
    
    if owner_id_filter:
        query = query.filter(AccessRequest.owner_id == owner_id_filter)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AccessRequest.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AccessRequest.created_at < to_date)
        except ValueError:
            pass
    
    # Paginazione
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = query.order_by(AccessRequest.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Statistiche
    stats = {
        'pending': AccessRequest.query.filter_by(status='pending').count(),
        'approved': AccessRequest.query.filter_by(status='approved').count(),
        'denied': AccessRequest.query.filter_by(status='denied').count(),
        'expired': AccessRequest.query.filter_by(status='expired').count(),
        'today': AccessRequest.query.filter(
            AccessRequest.created_at >= datetime.utcnow().date()
        ).count(),
        'last_7_days': AccessRequest.query.filter(
            AccessRequest.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
    }
    
    return render_template('admin/access_requests_dashboard.html',
                         requests=pagination.items,
                         pagination=pagination,
                         stats=stats,
                         filters={
                             'status': status_filter,
                             'file_id': file_id_filter,
                             'requested_by': requested_by_filter,
                             'owner_id': owner_id_filter,
                             'from': date_from,
                             'to': date_to
                         })

# === APPROVAZIONE RICHIESTA ===
@admin_access_requests_bp.route('/<int:request_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_access_request(request_id):
    """
    Approva una richiesta di accesso.
    
    Input:
        expires_in_hours (int): Ore di validità (default 72)
        decision_reason (str, opzionale): Motivo della decisione
    """
    try:
        access_request = AccessRequest.query.get_or_404(request_id)
        
        if access_request.status != 'pending':
            flash("Richiesta già gestita", "warning")
            return redirect(url_for('admin_access_requests.access_requests_dashboard'))
        
        # Parametri
        expires_in_hours = int(request.form.get('expires_in_hours', 72))
        decision_reason = request.form.get('decision_reason', '').strip()
        
        # Validazione
        if expires_in_hours < 1 or expires_in_hours > 720:  # Max 30 giorni
            flash("Durata non valida (1-720 ore)", "danger")
            return redirect(url_for('admin_access_requests.access_requests_dashboard'))
        
        # Calcola scadenza
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        # Aggiorna richiesta
        access_request.status = 'approved'
        access_request.approver_id = current_user.id
        access_request.decided_at = datetime.utcnow()
        access_request.expires_at = expires_at
        access_request.decision_reason = decision_reason
        
        # Crea DocumentShare
        document_share = DocumentShare(
            file_id=access_request.file_id,
            user_id=access_request.requested_by,
            granted_by=current_user.id,
            granted_at=datetime.utcnow(),
            expires_at=expires_at,
            scope='download',
            notes=f"Approvata da {current_user.username} - {decision_reason}"
        )
        
        db.session.add(document_share)
        db.session.commit()
        
        # Invia email di notifica
        send_approval_notification(access_request, approved=True, expires_at=expires_at)
        
        flash(f"Richiesta approvata per {expires_in_hours} ore", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Errore durante l'approvazione: {str(e)}", "danger")
    
    return redirect(url_for('admin_access_requests.access_requests_dashboard'))

# === NEGAZIONE RICHIESTA ===
@admin_access_requests_bp.route('/<int:request_id>/deny', methods=['POST'])
@login_required
@admin_required
def deny_access_request(request_id):
    """
    Nega una richiesta di accesso.
    
    Input:
        decision_reason (str, opzionale): Motivo della negazione
    """
    try:
        access_request = AccessRequest.query.get_or_404(request_id)
        
        if access_request.status != 'pending':
            flash("Richiesta già gestita", "warning")
            return redirect(url_for('admin_access_requests.access_requests_dashboard'))
        
        # Parametri
        decision_reason = request.form.get('decision_reason', '').strip()
        
        # Aggiorna richiesta
        access_request.status = 'denied'
        access_request.approver_id = current_user.id
        access_request.decided_at = datetime.utcnow()
        access_request.decision_reason = decision_reason
        
        db.session.commit()
        
        # Invia email di notifica
        send_approval_notification(access_request, approved=False)
        
        flash("Richiesta negata", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Errore durante la negazione: {str(e)}", "danger")
    
    return redirect(url_for('admin_access_requests.access_requests_dashboard'))

# === API PER STATISTICHE ===
@admin_access_requests_bp.route('/stats', methods=['GET'])
@login_required
@admin_required
def access_requests_stats():
    """
    API per statistiche delle richieste di accesso.
    """
    try:
        # Statistiche generali
        total_requests = AccessRequest.query.count()
        pending_requests = AccessRequest.query.filter_by(status='pending').count()
        approved_requests = AccessRequest.query.filter_by(status='approved').count()
        denied_requests = AccessRequest.query.filter_by(status='denied').count()
        
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
        
        # Richieste per stato (ultimi 30 giorni)
        last_month = datetime.utcnow() - timedelta(days=30)
        monthly_stats = db.session.query(
            AccessRequest.status,
            db.func.count(AccessRequest.id)
        ).filter(
            AccessRequest.created_at >= last_month
        ).group_by(AccessRequest.status).all()
        
        return jsonify({
            'total': total_requests,
            'pending': pending_requests,
            'approved': approved_requests,
            'denied': denied_requests,
            'today': today_requests,
            'last_week': week_requests,
            'monthly_stats': dict(monthly_stats)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === EXPORT CSV ===
@admin_access_requests_bp.route('/export', methods=['GET'])
@login_required
@admin_required
def export_access_requests():
    """
    Export CSV delle richieste di accesso.
    """
    try:
        # Filtri dalla query string
        status_filter = request.args.get('status', '')
        date_from = request.args.get('from', '')
        date_to = request.args.get('to', '')
        
        # Query base
        query = AccessRequest.query.join(Document).join(User, AccessRequest.requested_by_user)
        
        # Applica filtri
        if status_filter:
            query = query.filter(AccessRequest.status == status_filter)
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(AccessRequest.created_at >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(AccessRequest.created_at < to_date)
            except ValueError:
                pass
        
        # Ottieni tutti i risultati
        requests = query.order_by(AccessRequest.created_at.desc()).all()
        
        # Genera CSV
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'ID', 'Documento', 'Richiedente', 'Proprietario', 'Motivo', 
            'Stato', 'Data Richiesta', 'Data Decisione', 'Approvatore', 
            'Scadenza', 'Motivo Decisione'
        ])
        
        # Dati
        for req in requests:
            writer.writerow([
                req.id,
                req.file.title if req.file else 'N/A',
                req.requested_by_user.username if req.requested_by_user else 'N/A',
                req.owner.username if req.owner else 'N/A',
                req.reason or '',
                req.status_display,
                req.created_at.strftime('%d/%m/%Y %H:%M') if req.created_at else '',
                req.decided_at.strftime('%d/%m/%Y %H:%M') if req.decided_at else '',
                req.approver.username if req.approver else 'N/A',
                req.expires_at.strftime('%d/%m/%Y %H:%M') if req.expires_at else '',
                req.decision_reason or ''
            ])
        
        output.seek(0)
        
        # Genera nome file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"access_requests_{timestamp}.csv"
        
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        
    except Exception as e:
        flash(f"Errore durante l'export: {str(e)}", "danger")
        return redirect(url_for('admin_access_requests.access_requests_dashboard'))

# === JOB AUTOMATICI ===
@admin_access_requests_bp.route('/jobs/expire-requests', methods=['POST'])
@login_required
@admin_required
def manual_expire_requests():
    """
    Esegue manualmente il job di scadenza richieste.
    """
    try:
        from routes.access_requests import expire_access_requests, cleanup_expired_shares
        
        # Esegui job
        expire_access_requests()
        cleanup_expired_shares()
        
        flash("Job di scadenza eseguito con successo", "success")
        
    except Exception as e:
        flash(f"Errore durante l'esecuzione del job: {str(e)}", "danger")
    
    return redirect(url_for('admin_access_requests.access_requests_dashboard'))
