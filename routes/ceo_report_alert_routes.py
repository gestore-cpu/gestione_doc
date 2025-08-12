"""
Route per la gestione degli alert dei report CEO.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from decorators import ceo_or_admin_required
from models import AlertReportCEO
from extensions import db
from datetime import datetime

# === Blueprint Alert Report CEO ===
ceo_report_alert_bp = Blueprint('ceo_report_alert', __name__, url_prefix='/ceo/report-alert')

@ceo_report_alert_bp.route('/')
@login_required
@ceo_or_admin_required
def alert_dashboard():
    """
    Dashboard per gli alert dei report CEO.
    """
    try:
        # Ottieni tutti gli alert
        alerts = AlertReportCEO.query.order_by(AlertReportCEO.data_trigger.desc()).all()
        
        # Statistiche
        total_alerts = len(alerts)
        active_alerts = len([a for a in alerts if a.is_attivo])
        unread_alerts = AlertReportCEO.count_alert_non_letti()
        
        # Alert per livello di criticità
        alerts_by_level = {}
        for alert in alerts:
            level = alert.livello_criticita
            if level not in alerts_by_level:
                alerts_by_level[level] = []
            alerts_by_level[level].append(alert)
        
        return render_template('ceo/report_alert_dashboard.html', 
                            alerts=alerts,
                            total_alerts=total_alerts,
                            active_alerts=active_alerts,
                            unread_alerts=unread_alerts,
                            alerts_by_level=alerts_by_level)
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore dashboard alert report: {e}")
        flash("❌ Errore caricamento dashboard alert", "danger")
        return redirect(url_for('ceo.dashboard'))


@ceo_report_alert_bp.route('/<int:alert_id>/dettagli')
@login_required
@ceo_or_admin_required
def alert_dettagli(alert_id):
    """
    Visualizza i dettagli di un alert specifico.
    """
    try:
        alert = AlertReportCEO.query.get_or_404(alert_id)
        
        return render_template('ceo/report_alert_dettagli.html', alert=alert)
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore dettagli alert: {e}")
        flash("❌ Errore caricamento dettagli alert", "danger")
        return redirect(url_for('ceo_report_alert.alert_dashboard'))


@ceo_report_alert_bp.route('/<int:alert_id>/marca_letto', methods=['POST'])
@login_required
@ceo_or_admin_required
def marca_alert_letto(alert_id):
    """
    Marca un alert come letto.
    """
    try:
        alert = AlertReportCEO.query.get_or_404(alert_id)
        
        if not alert.is_letto:
            alert.marca_letto()
            db.session.commit()
            
            flash(f"✅ Alert {alert.periodo_display} marcato come letto", "success")
        else:
            flash("ℹ️ Alert già letto", "info")
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore marcatura alert: {e}")
        flash("❌ Errore marcatura alert", "danger")
    
    return redirect(url_for('ceo_report_alert.alert_dashboard'))


@ceo_report_alert_bp.route('/<int:alert_id>/disattiva', methods=['POST'])
@login_required
@ceo_or_admin_required
def disattiva_alert(alert_id):
    """
    Disattiva un alert.
    """
    try:
        alert = AlertReportCEO.query.get_or_404(alert_id)
        
        if alert.trigger_attivo:
            alert.disattiva_alert()
            db.session.commit()
            
            flash(f"✅ Alert {alert.periodo_display} disattivato", "success")
        else:
            flash("ℹ️ Alert già disattivato", "info")
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore disattivazione alert: {e}")
        flash("❌ Errore disattivazione alert", "danger")
    
    return redirect(url_for('ceo_report_alert.alert_dashboard'))


@ceo_report_alert_bp.route('/marca_tutti_letti', methods=['POST'])
@login_required
@ceo_or_admin_required
def marca_tutti_letti():
    """
    Marca tutti gli alert come letti.
    """
    try:
        unread_alerts = AlertReportCEO.get_alert_non_letti()
        
        for alert in unread_alerts:
            alert.marca_letto()
        
        db.session.commit()
        
        flash(f"✅ {len(unread_alerts)} alert marcati come letti", "success")
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore marcatura multipla alert: {e}")
        flash("❌ Errore marcatura multipla alert", "danger")
    
    return redirect(url_for('ceo_report_alert.alert_dashboard'))


@ceo_report_alert_bp.route('/api/non_letti')
@login_required
@ceo_or_admin_required
def api_alert_non_letti():
    """
    API per ottenere il numero di alert non letti.
    """
    try:
        count = AlertReportCEO.count_alert_non_letti()
        
        return jsonify({
            'success': True,
            'count': count,
            'has_alerts': count > 0
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore API alert non letti: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ceo_report_alert_bp.route('/api/statistiche')
@login_required
@ceo_or_admin_required
def api_statistiche_alert():
    """
    API per statistiche sugli alert.
    """
    try:
        # Statistiche generali
        total_alerts = AlertReportCEO.query.count()
        active_alerts = AlertReportCEO.query.filter_by(trigger_attivo=True).count()
        unread_alerts = AlertReportCEO.count_alert_non_letti()
        
        # Statistiche per livello
        alerts_by_level = {}
        for alert in AlertReportCEO.query.all():
            level = alert.livello_criticita
            if level not in alerts_by_level:
                alerts_by_level[level] = {'total': 0, 'active': 0, 'unread': 0}
            
            alerts_by_level[level]['total'] += 1
            if alert.trigger_attivo:
                alerts_by_level[level]['active'] += 1
            if not alert.letto:
                alerts_by_level[level]['unread'] += 1
        
        # Statistiche per anno
        alerts_by_year = {}
        for alert in AlertReportCEO.query.all():
            year = alert.anno
            if year not in alerts_by_year:
                alerts_by_year[year] = {'total': 0, 'critical': 0}
            
            alerts_by_year[year]['total'] += 1
            if alert.numero_invii_critici >= 5:
                alerts_by_year[year]['critical'] += 1
        
        return jsonify({
            'success': True,
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'unread_alerts': unread_alerts,
            'alerts_by_level': alerts_by_level,
            'alerts_by_year': alerts_by_year
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore API statistiche alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ceo_report_alert_bp.route('/api/ultimi_alert')
@login_required
@ceo_or_admin_required
def api_ultimi_alert():
    """
    API per ottenere gli ultimi alert.
    """
    try:
        limit = request.args.get('limit', 5, type=int)
        
        alerts = AlertReportCEO.query.order_by(AlertReportCEO.data_trigger.desc()).limit(limit).all()
        
        alert_data = []
        for alert in alerts:
            alert_data.append({
                'id': alert.id,
                'periodo': alert.periodo_display,
                'num_critical': alert.numero_invii_critici,
                'level': alert.livello_criticita,
                'level_display': alert.livello_display,
                'is_active': alert.is_attivo,
                'is_read': alert.is_letto,
                'data_trigger': alert.data_trigger_formatted,
                'report_file': alert.id_report_ceo
            })
        
        return jsonify({
            'success': True,
            'alerts': alert_data
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore API ultimi alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
