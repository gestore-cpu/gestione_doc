#!/usr/bin/env python3
"""
Route per il monitoraggio AI post-migrazione.
Gestisce alert e attività AI per utenti/guest appena importati.
"""

from flask import Blueprint, request, jsonify, current_app, render_template
from flask_login import login_required, current_user
from functools import wraps
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
from models import User, GuestUser, AttivitaAI, AlertAI, db
from services.ai_monitoring import AIMonitoringService, genera_alert_ai_post_import
from services.realtime_ai_monitoring import analizza_attivita_realtime, RealtimeAIMonitoring
from utils.audit_logger import log_event

ai_monitoring_bp = Blueprint('ai_monitoring', __name__, url_prefix='/admin/ai')

def roles_required(*roles):
    """Decorator per verificare i ruoli richiesti."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Autenticazione richiesta'}), 401
            
            if current_user.role not in roles:
                return jsonify({'error': 'Permessi insufficienti'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@ai_monitoring_bp.route('/users/activity', methods=['GET'])
@login_required
@roles_required('admin', 'ceo')
def get_users_activity():
    """
    Recupera l'attività AI degli utenti post-migrazione.
    
    Query Parameters:
        - page: Numero pagina (default: 1)
        - per_page: Elementi per pagina (default: 20)
        - filter: Filtro ('nuovo_import', 'monitorato', 'stabile')
        - search: Ricerca per nome/email
        
    Returns:
        JSON con lista utenti e loro attività AI
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        filter_type = request.args.get('filter', 'all')
        search = request.args.get('search', '')
        
        # Query base
        query = db.session.query(User, AttivitaAI).outerjoin(
            AttivitaAI, User.id == AttivitaAI.user_id
        )
        
        # Applica filtri
        if filter_type == 'nuovo_import':
            query = query.filter(AttivitaAI.stato_iniziale == 'nuovo_import')
        elif filter_type == 'monitorato':
            query = query.filter(AttivitaAI.stato_iniziale == 'monitorato')
        elif filter_type == 'stabile':
            query = query.filter(AttivitaAI.stato_iniziale == 'stabile')
        
        # Applica ricerca
        if search:
            query = query.filter(
                or_(
                    User.first_name.ilike(f'%{search}%'),
                    User.last_name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                    User.username.ilike(f'%{search}%')
                )
            )
        
        # Ordina per data creazione attività AI (più recenti prima)
        query = query.order_by(AttivitaAI.created_at.desc().nullslast())
        
        # Paginazione
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        results = []
        for user, attivita in pagination.items:
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'nuovo_import': attivita.is_nuovo_import if attivita else False,
                'giorni_da_import': attivita.giorni_da_import if attivita else None,
                'stato_ai': attivita.stato_iniziale if attivita else None,
                'note_ai': attivita.note if attivita else None,
                'badge_class': attivita.badge_class if attivita else None,
                'display_text': attivita.display_text if attivita else None
            }
            
            # Conta alert AI per questo utente
            alert_count = db.session.query(AlertAI).filter(
                and_(
                    AlertAI.user_id == user.id,
                    AlertAI.stato == 'nuovo'
                )
            ).count()
            
            user_data['alert_count'] = alert_count
            user_data['has_alerts'] = alert_count > 0
            
            results.append(user_data)
        
        return jsonify({
            'success': True,
            'users': results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            },
            'filters': {
                'current_filter': filter_type,
                'search': search
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore recupero attività utenti AI: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante il recupero: {str(e)}'
        }), 500

@ai_monitoring_bp.route('/guests/activity', methods=['GET'])
@login_required
@roles_required('admin', 'ceo')
def get_guests_activity():
    """
    Recupera l'attività AI dei guest post-migrazione.
    
    Query Parameters:
        - page: Numero pagina (default: 1)
        - per_page: Elementi per pagina (default: 20)
        - filter: Filtro ('nuovo_import', 'monitorato', 'stabile')
        - search: Ricerca per email
        
    Returns:
        JSON con lista guest e loro attività AI
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        filter_type = request.args.get('filter', 'all')
        search = request.args.get('search', '')
        
        # Query base
        query = db.session.query(GuestUser, AttivitaAI).outerjoin(
            AttivitaAI, GuestUser.id == AttivitaAI.guest_id
        )
        
        # Applica filtri
        if filter_type == 'nuovo_import':
            query = query.filter(AttivitaAI.stato_iniziale == 'nuovo_import')
        elif filter_type == 'monitorato':
            query = query.filter(AttivitaAI.stato_iniziale == 'monitorato')
        elif filter_type == 'stabile':
            query = query.filter(AttivitaAI.stato_iniziale == 'stabile')
        
        # Applica ricerca
        if search:
            query = query.filter(GuestUser.email.ilike(f'%{search}%'))
        
        # Ordina per data creazione attività AI (più recenti prima)
        query = query.order_by(AttivitaAI.created_at.desc().nullslast())
        
        # Paginazione
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        results = []
        for guest, attivita in pagination.items:
            guest_data = {
                'id': guest.id,
                'email': guest.email,
                'registered_at': guest.registered_at.isoformat() if guest.registered_at else None,
                'nuovo_import': attivita.is_nuovo_import if attivita else False,
                'giorni_da_import': attivita.giorni_da_import if attivita else None,
                'stato_ai': attivita.stato_iniziale if attivita else None,
                'note_ai': attivita.note if attivita else None,
                'badge_class': attivita.badge_class if attivita else None,
                'display_text': attivita.display_text if attivita else None
            }
            
            # Conta alert AI per questo guest
            alert_count = db.session.query(AlertAI).filter(
                and_(
                    AlertAI.guest_id == guest.id,
                    AlertAI.stato == 'nuovo'
                )
            ).count()
            
            guest_data['alert_count'] = alert_count
            guest_data['has_alerts'] = alert_count > 0
            
            results.append(guest_data)
        
        return jsonify({
            'success': True,
            'guests': results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            },
            'filters': {
                'current_filter': filter_type,
                'search': search
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore recupero attività guest AI: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante il recupero: {str(e)}'
        }), 500

@ai_monitoring_bp.route('/alerts', methods=['GET'])
@login_required
@roles_required('admin', 'ceo')
def get_ai_alerts():
    """
    Recupera tutti gli alert AI.
    
    Query Parameters:
        - page: Numero pagina (default: 1)
        - per_page: Elementi per pagina (default: 20)
        - stato: Filtro stato ('nuovo', 'in_revisione', 'chiuso')
        - tipo: Filtro tipo alert
        
    Returns:
        JSON con lista alert AI
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        stato = request.args.get('stato', 'all')
        tipo = request.args.get('tipo', 'all')
        
        # Query base
        query = db.session.query(AlertAI).outerjoin(
            User, AlertAI.user_id == User.id
        ).outerjoin(
            GuestUser, AlertAI.guest_id == GuestUser.id
        )
        
        # Applica filtri
        if stato != 'all':
            query = query.filter(AlertAI.stato == stato)
        
        if tipo != 'all':
            query = query.filter(AlertAI.tipo_alert == tipo)
        
        # Ordina per timestamp (più recenti prima)
        query = query.order_by(AlertAI.timestamp.desc())
        
        # Paginazione
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        results = []
        for alert in pagination.items:
            alert_data = {
                'id': alert.id,
                'tipo_alert': alert.tipo_alert,
                'tipo_alert_display': alert.tipo_alert_display,
                'descrizione': alert.descrizione,
                'stato': alert.stato,
                'stato_badge_class': alert.stato_badge_class,
                'timestamp': alert.timestamp.isoformat(),
                'ip_address': alert.ip_address,
                'user_agent': alert.user_agent,
                'created_at': alert.created_at.isoformat(),
                'utente_display': alert.utente_display,
                'user_id': alert.user_id,
                'guest_id': alert.guest_id
            }
            
            results.append(alert_data)
        
        return jsonify({
            'success': True,
            'alerts': results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            },
            'filters': {
                'current_stato': stato,
                'current_tipo': tipo
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore recupero alert AI: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante il recupero: {str(e)}'
        }), 500

@ai_monitoring_bp.route('/alerts/<int:alert_id>/update', methods=['POST'])
@login_required
@roles_required('admin', 'ceo')
def update_alert_status(alert_id):
    """
    Aggiorna lo stato di un alert AI.
    
    Args:
        alert_id: ID dell'alert
        
    Body:
        - stato: Nuovo stato ('nuovo', 'in_revisione', 'chiuso')
        - note: Note aggiuntive (opzionale)
        
    Returns:
        JSON con risultato aggiornamento
    """
    try:
        data = request.get_json() or {}
        nuovo_stato = data.get('stato')
        note = data.get('note')
        
        if not nuovo_stato:
            return jsonify({
                'success': False,
                'error': 'Stato richiesto'
            }), 400
        
        # Recupera alert
        alert = db.session.query(AlertAI).filter(AlertAI.id == alert_id).first()
        if not alert:
            return jsonify({
                'success': False,
                'error': 'Alert non trovato'
            }), 404
        
        # Aggiorna stato
        vecchio_stato = alert.stato
        alert.stato = nuovo_stato
        
        # Log dell'aggiornamento
        log_event(
            'alert_ai_status_updated',
            user_id=current_user.id,
            details={
                'alert_id': alert_id,
                'old_status': vecchio_stato,
                'new_status': nuovo_stato,
                'note': note
            }
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Alert aggiornato da {vecchio_stato} a {nuovo_stato}',
            'alert': {
                'id': alert.id,
                'stato': alert.stato,
                'stato_badge_class': alert.stato_badge_class
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore aggiornamento alert {alert_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante l\'aggiornamento: {str(e)}'
        }), 500

@ai_monitoring_bp.route('/check/<int:user_id>', methods=['POST'])
@login_required
@roles_required('admin', 'ceo')
def check_user_ai(user_id):
    """
    Esegue controlli AI per un utente specifico.
    
    Args:
        user_id: ID dell'utente
        
    Body:
        - current_ip: IP corrente dell'utente (opzionale)
        
    Returns:
        JSON con alert generati
    """
    try:
        data = request.get_json() or {}
        current_ip = data.get('current_ip')
        
        # Esegue controlli AI
        alerts = genera_alert_ai_post_import(user_id=user_id, current_ip=current_ip)
        
        return jsonify({
            'success': True,
            'alerts_generated': len(alerts),
            'alerts': alerts
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore controlli AI utente {user_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante i controlli: {str(e)}'
        }), 500

@ai_monitoring_bp.route('/check/guest/<int:guest_id>', methods=['POST'])
@login_required
@roles_required('admin', 'ceo')
def check_guest_ai(guest_id):
    """
    Esegue controlli AI per un guest specifico.
    
    Args:
        guest_id: ID del guest
        
    Body:
        - current_ip: IP corrente del guest (opzionale)
        
    Returns:
        JSON con alert generati
    """
    try:
        data = request.get_json() or {}
        current_ip = data.get('current_ip')
        
        # Esegue controlli AI
        alerts = genera_alert_ai_post_import(guest_id=guest_id, current_ip=current_ip)
        
        return jsonify({
            'success': True,
            'alerts_generated': len(alerts),
            'alerts': alerts
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore controlli AI guest {guest_id}: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante i controlli: {str(e)}'
        }), 500

@ai_monitoring_bp.route('/stats', methods=['GET'])
@login_required
@roles_required('admin', 'ceo')
def get_ai_stats():
    """
    Recupera statistiche del monitoraggio AI.
    
    Returns:
        JSON con statistiche AI
    """
    try:
        # Statistiche attività AI
        total_attivita = db.session.query(AttivitaAI).count()
        nuovo_import = db.session.query(AttivitaAI).filter(
            AttivitaAI.stato_iniziale == 'nuovo_import'
        ).count()
        monitorato = db.session.query(AttivitaAI).filter(
            AttivitaAI.stato_iniziale == 'monitorato'
        ).count()
        stabile = db.session.query(AttivitaAI).filter(
            AttivitaAI.stato_iniziale == 'stabile'
        ).count()
        
        # Statistiche alert AI
        total_alerts = db.session.query(AlertAI).count()
        nuovi_alerts = db.session.query(AlertAI).filter(
            AlertAI.stato == 'nuovo'
        ).count()
        in_revisione = db.session.query(AlertAI).filter(
            AlertAI.stato == 'in_revisione'
        ).count()
        chiusi = db.session.query(AlertAI).filter(
            AlertAI.stato == 'chiuso'
        ).count()
        
        # Alert per tipo
        alert_types = db.session.query(
            AlertAI.tipo_alert,
            func.count(AlertAI.id).label('count')
        ).group_by(AlertAI.tipo_alert).all()
        
        return jsonify({
            'success': True,
            'statistics': {
                'attivita_ai': {
                    'total': total_attivita,
                    'nuovo_import': nuovo_import,
                    'monitorato': monitorato,
                    'stabile': stabile
                },
                'alert_ai': {
                    'total': total_alerts,
                    'nuovi': nuovi_alerts,
                    'in_revisione': in_revisione,
                    'chiusi': chiusi
                },
                'alert_types': [
                    {'tipo': tipo, 'count': count} 
                    for tipo, count in alert_types
                ]
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore statistiche AI: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante il recupero statistiche: {str(e)}'
        }), 500

@ai_monitoring_bp.route('/realtime/analyze', methods=['POST'])
@login_required
@roles_required('admin', 'ceo')
def analyze_realtime():
    """
    Esegue analisi AI in tempo reale.
    
    Returns:
        JSON con alert generati
    """
    try:
        alerts = analizza_attivita_realtime()
        
        return jsonify({
            'success': True,
            'alerts_generated': len(alerts),
            'alerts': alerts
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore analisi tempo reale: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante l\'analisi: {str(e)}'
        }), 500

@ai_monitoring_bp.route('/alerts/realtime', methods=['GET'])
@login_required
@roles_required('admin', 'ceo')
def get_realtime_alerts():
    """
    Recupera alert in tempo reale con filtri avanzati.
    
    Query Parameters:
        - livello: Filtro livello ('basso', 'medio', 'alto', 'critico')
        - stato: Filtro stato ('nuovo', 'in_revisione', 'chiuso')
        - periodo: Periodo ('1h', '24h', '7d', '30d')
        - tipo: Filtro tipo alert
        
    Returns:
        JSON con lista alert in tempo reale
    """
    try:
        livello = request.args.get('livello', 'all')
        stato = request.args.get('stato', 'all')
        periodo = request.args.get('periodo', '24h')
        tipo = request.args.get('tipo', 'all')
        
        # Calcola periodo
        now = datetime.utcnow()
        if periodo == '1h':
            start_time = now - timedelta(hours=1)
        elif periodo == '24h':
            start_time = now - timedelta(days=1)
        elif periodo == '7d':
            start_time = now - timedelta(days=7)
        elif periodo == '30d':
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=1)
        
        # Query base
        query = db.session.query(AlertAI).filter(
            AlertAI.timestamp >= start_time
        )
        
        # Applica filtri
        if livello != 'all':
            query = query.filter(AlertAI.livello == livello)
        
        if stato != 'all':
            query = query.filter(AlertAI.stato == stato)
        
        if tipo != 'all':
            query = query.filter(AlertAI.tipo_alert == tipo)
        
        # Ordina per timestamp (più recenti prima)
        query = query.order_by(AlertAI.timestamp.desc())
        
        alerts = query.all()
        
        results = []
        for alert in alerts:
            alert_data = {
                'id': alert.id,
                'tipo_alert': alert.tipo_alert,
                'tipo_alert_display': alert.tipo_alert_display,
                'livello': alert.livello,
                'livello_badge_class': alert.livello_badge_class,
                'livello_display': alert.livello_display,
                'descrizione': alert.descrizione,
                'stato': alert.stato,
                'stato_badge_class': alert.stato_badge_class,
                'timestamp': alert.timestamp.isoformat(),
                'ip_address': alert.ip_address,
                'user_agent': alert.user_agent,
                'created_at': alert.created_at.isoformat(),
                'utente_display': alert.utente_display
            }
            results.append(alert_data)
        
        return jsonify({
            'success': True,
            'alerts': results,
            'total': len(results),
            'filters': {
                'livello': livello,
                'stato': stato,
                'periodo': periodo,
                'tipo': tipo
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore recupero alert tempo reale: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante il recupero: {str(e)}'
        }), 500

@ai_monitoring_bp.route('/alerts/bulk-update', methods=['POST'])
@login_required
@roles_required('admin', 'ceo')
def bulk_update_alerts():
    """
    Aggiorna stato di multiple alert.
    
    Body:
        - alert_ids: Lista ID alert da aggiornare
        - nuovo_stato: Nuovo stato per tutti gli alert
        
    Returns:
        JSON con risultato aggiornamento
    """
    try:
        data = request.get_json() or {}
        alert_ids = data.get('alert_ids', [])
        nuovo_stato = data.get('nuovo_stato')
        
        if not alert_ids or not nuovo_stato:
            return jsonify({
                'success': False,
                'error': 'alert_ids e nuovo_stato richiesti'
            }), 400
        
        # Aggiorna tutti gli alert
        updated_count = db.session.query(AlertAI).filter(
            AlertAI.id.in_(alert_ids)
        ).update({
            'stato': nuovo_stato
        }, synchronize_session=False)
        
        db.session.commit()
        
        # Log dell'aggiornamento
        log_event(
            'alert_ai_bulk_update',
            user_id=current_user.id,
            details={
                'alert_ids': alert_ids,
                'new_status': nuovo_stato,
                'updated_count': updated_count
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Aggiornati {updated_count} alert a stato "{nuovo_stato}"',
            'updated_count': updated_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore aggiornamento bulk alert: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante l\'aggiornamento: {str(e)}'
        }), 500

@ai_monitoring_bp.route('/dashboard/overview', methods=['GET'])
@login_required
@roles_required('admin', 'ceo')
def get_dashboard_overview():
    """
    Recupera overview per dashboard admin/CEO.
    
    Returns:
        JSON con statistiche e alert recenti
    """
    try:
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        # Statistiche alert ultime 24h
        total_alerts_24h = db.session.query(AlertAI).filter(
            AlertAI.created_at >= last_24h
        ).count()
        
        nuovi_alert_24h = db.session.query(AlertAI).filter(
            and_(
                AlertAI.created_at >= last_24h,
                AlertAI.stato == 'nuovo'
            )
        ).count()
        
        # Alert per livello
        alert_per_livello = db.session.query(
            AlertAI.livello,
            func.count(AlertAI.id).label('count')
        ).filter(
            AlertAI.created_at >= last_24h
        ).group_by(AlertAI.livello).all()
        
        # Alert per tipo
        alert_per_tipo = db.session.query(
            AlertAI.tipo_alert,
            func.count(AlertAI.id).label('count')
        ).filter(
            AlertAI.created_at >= last_24h
        ).group_by(AlertAI.tipo_alert).all()
        
        # Ultimi 10 alert
        ultimi_alert = db.session.query(AlertAI).filter(
            AlertAI.created_at >= last_24h
        ).order_by(AlertAI.created_at.desc()).limit(10).all()
        
        results = []
        for alert in ultimi_alert:
            alert_data = {
                'id': alert.id,
                'tipo_alert': alert.tipo_alert,
                'tipo_alert_display': alert.tipo_alert_display,
                'livello': alert.livello,
                'livello_badge_class': alert.livello_badge_class,
                'descrizione': alert.descrizione,
                'stato': alert.stato,
                'stato_badge_class': alert.stato_badge_class,
                'timestamp': alert.timestamp.isoformat(),
                'utente_display': alert.utente_display
            }
            results.append(alert_data)
        
        return jsonify({
            'success': True,
            'overview': {
                'total_alerts_24h': total_alerts_24h,
                'nuovi_alert_24h': nuovi_alert_24h,
                'alert_per_livello': [
                    {'livello': livello, 'count': count} 
                    for livello, count in alert_per_livello
                ],
                'alert_per_tipo': [
                    {'tipo': tipo, 'count': count} 
                    for tipo, count in alert_per_tipo
                ],
                'ultimi_alert': results
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore recupero overview dashboard: {e}")
        return jsonify({
            'success': False,
            'error': f'Errore durante il recupero: {str(e)}'
        }), 500 

@ai_monitoring_bp.route('/realtime-alerts')
@login_required
@roles_required('admin', 'ceo')
def realtime_alerts():
    """
    Dashboard per gli alert AI in tempo reale.
    
    Returns:
        Template HTML della dashboard
    """
    return render_template('admin/realtime_alerts.html') 