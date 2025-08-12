"""
Route per la gestione delle notifiche CEO.
Gestisce la visualizzazione e gestione delle notifiche automatiche al CEO.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from extensions import db
from models import NotificaCEO
from services.ceo_notifications import get_notifiche_ceo_non_lette, marca_notifica_letta
from datetime import datetime

# === Blueprint Notifiche CEO ===
ceo_notifications_bp = Blueprint('ceo_notifications', __name__, url_prefix='/ceo/notifiche')


@ceo_notifications_bp.route('/')
@login_required
def notifiche_list():
    """
    Visualizza la lista delle notifiche CEO.
    """
    if not current_user.is_ceo:
        flash("❌ Accesso negato. Solo il CEO può visualizzare le notifiche.", "danger")
        return redirect(url_for('auth.login'))
    
    try:
        # Ottieni tutte le notifiche, ordinate per data creazione (più recenti prima)
        notifiche = NotificaCEO.query.order_by(NotificaCEO.data_creazione.desc()).all()
        
        # Conta notifiche non lette
        notifiche_non_lette = len([n for n in notifiche if n.is_nuovo])
        
        return render_template(
            'ceo/notifiche_list.html',
            notifiche=notifiche,
            notifiche_non_lette=notifiche_non_lette
        )
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore caricamento notifiche CEO: {e}")
        flash("❌ Errore nel caricamento delle notifiche.", "danger")
        return redirect(url_for('ceo.dashboard'))


@ceo_notifications_bp.route('/<int:notifica_id>/marca_letta', methods=['POST'])
@login_required
def marca_notifica_letta_route(notifica_id):
    """
    Marca una notifica come letta.
    """
    if not current_user.is_ceo:
        return jsonify({'success': False, 'message': 'Accesso negato'}), 403
    
    try:
        success = marca_notifica_letta(notifica_id)
        if success:
            return jsonify({'success': True, 'message': 'Notifica marcata come letta'})
        else:
            return jsonify({'success': False, 'message': 'Notifica non trovata'}), 404
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore marcatura notifica: {e}")
        return jsonify({'success': False, 'message': 'Errore interno'}), 500


@ceo_notifications_bp.route('/<int:notifica_id>/dettagli')
@login_required
def notifica_dettagli(notifica_id):
    """
    Visualizza i dettagli di una notifica specifica.
    """
    if not current_user.is_ceo:
        flash("❌ Accesso negato. Solo il CEO può visualizzare le notifiche.", "danger")
        return redirect(url_for('auth.login'))
    
    try:
        notifica = NotificaCEO.query.get_or_404(notifica_id)
        
        # Marca automaticamente come letta se è nuova
        if notifica.is_nuovo:
            notifica.marca_letta()
            db.session.commit()
        
        return render_template(
            'ceo/notifica_dettagli.html',
            notifica=notifica
        )
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore caricamento dettagli notifica: {e}")
        flash("❌ Errore nel caricamento dei dettagli.", "danger")
        return redirect(url_for('ceo_notifications.notifiche_list'))


@ceo_notifications_bp.route('/api/non_lette')
@login_required
def api_notifiche_non_lette():
    """
    API per ottenere le notifiche non lette (per badge/contatori).
    """
    if not current_user.is_ceo:
        return jsonify({'count': 0}), 403
    
    try:
        notifiche_non_lette = get_notifiche_ceo_non_lette()
        return jsonify({
            'count': len(notifiche_non_lette),
            'notifiche': [
                {
                    'id': n.id,
                    'titolo': n.titolo,
                    'tipo': n.tipo_display,
                    'data': n.data_creazione_formatted
                } for n in notifiche_non_lette[:5]  # Solo le prime 5
            ]
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore API notifiche non lette: {e}")
        return jsonify({'count': 0, 'error': 'Errore interno'}), 500


@ceo_notifications_bp.route('/api/marca_tutte_lette', methods=['POST'])
@login_required
def api_marca_tutte_lette():
    """
    API per marcare tutte le notifiche come lette.
    """
    if not current_user.is_ceo:
        return jsonify({'success': False, 'message': 'Accesso negato'}), 403
    
    try:
        notifiche_non_lette = NotificaCEO.query.filter_by(stato='nuovo').all()
        for notifica in notifiche_non_lette:
            notifica.marca_letta()
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Marcate {len(notifiche_non_lette)} notifiche come lette'})
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore marcatura tutte notifiche: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Errore interno'}), 500


@ceo_notifications_bp.route('/statistiche')
@login_required
def notifiche_statistiche():
    """
    Visualizza statistiche delle notifiche CEO.
    """
    if not current_user.is_ceo:
        flash("❌ Accesso negato. Solo il CEO può visualizzare le statistiche.", "danger")
        return redirect(url_for('auth.login'))
    
    try:
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        # Statistiche generali
        totale_notifiche = NotificaCEO.query.count()
        notifiche_lette = NotificaCEO.query.filter_by(stato='letto').count()
        notifiche_non_lette = NotificaCEO.query.filter_by(stato='nuovo').count()
        
        # Statistiche per tipo
        stats_per_tipo = db.session.query(
            NotificaCEO.tipo,
            func.count(NotificaCEO.id).label('count')
        ).group_by(NotificaCEO.tipo).all()
        
        # Statistiche per periodo (ultimi 30 giorni)
        trenta_giorni_fa = datetime.utcnow() - timedelta(days=30)
        notifiche_ultimo_mese = NotificaCEO.query.filter(
            NotificaCEO.data_creazione >= trenta_giorni_fa
        ).count()
        
        # Notifiche per giorno (ultimi 7 giorni)
        sette_giorni_fa = datetime.utcnow() - timedelta(days=7)
        notifiche_per_giorno = db.session.query(
            func.date(NotificaCEO.data_creazione).label('data'),
            func.count(NotificaCEO.id).label('count')
        ).filter(
            NotificaCEO.data_creazione >= sette_giorni_fa
        ).group_by(func.date(NotificaCEO.data_creazione)).all()
        
        return render_template(
            'ceo/notifiche_statistiche.html',
            totale_notifiche=totale_notifiche,
            notifiche_lette=notifiche_lette,
            notifiche_non_lette=notifiche_non_lette,
            stats_per_tipo=stats_per_tipo,
            notifiche_ultimo_mese=notifiche_ultimo_mese,
            notifiche_per_giorno=notifiche_per_giorno
        )
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore caricamento statistiche notifiche: {e}")
        flash("❌ Errore nel caricamento delle statistiche.", "danger")
        return redirect(url_for('ceo_notifications.notifiche_list'))
