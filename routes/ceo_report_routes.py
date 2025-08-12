"""
Route per la gestione dei report CEO mensili.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, jsonify
from flask_login import login_required, current_user
from decorators import ceo_or_admin_required
from services.ceo_monthly_report import CEOMonthlyReportGenerator, genera_report_ceo_mensile, test_report_generation
from datetime import datetime
import os
import glob

# === Blueprint Report CEO ===
ceo_report_bp = Blueprint('ceo_report', __name__, url_prefix='/ceo/report')

@ceo_report_bp.route('/')
@login_required
@ceo_or_admin_required
def report_dashboard():
    """
    Dashboard per i report CEO mensili.
    """
    try:
        # Lista dei report esistenti
        reports_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reports')
        if os.path.exists(reports_dir):
            report_files = glob.glob(os.path.join(reports_dir, 'report_ceo_*.pdf'))
            report_files.sort(reverse=True)  # Più recenti prima
            
            reports = []
            for file_path in report_files:
                filename = os.path.basename(file_path)
                stat = os.stat(file_path)
                
                # Estrai mese e anno dal filename
                try:
                    parts = filename.replace('.pdf', '').split('_')
                    year = int(parts[-2])
                    month = int(parts[-1])
                    
                    reports.append({
                        'filename': filename,
                        'file_path': file_path,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2),
                        'created_at': datetime.fromtimestamp(stat.st_mtime),
                        'year': year,
                        'month': month,
                        'month_name': CEOMonthlyReportGenerator.month_names.get(month, f'Mese {month}')
                    })
                except (ValueError, IndexError):
                    continue
        else:
            reports = []
        
        return render_template('ceo/report_dashboard.html', reports=reports)
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore dashboard report: {e}")
        flash("❌ Errore caricamento dashboard report", "danger")
        return redirect(url_for('ceo.dashboard'))


@ceo_report_bp.route('/genera', methods=['GET', 'POST'])
@login_required
@ceo_or_admin_required
def genera_report_manuale():
    """
    Genera un report CEO mensile manualmente.
    """
    if request.method == 'POST':
        try:
            # Ottieni parametri dal form
            month = int(request.form.get('month', datetime.now().month))
            year = int(request.form.get('year', datetime.now().year))
            send_email = request.form.get('send_email') == 'on'
            
            # Genera il report
            result = genera_report_ceo_mensile(
                month=month,
                year=year,
                send_email=send_email
            )
            
            if result['success']:
                flash(f"✅ Report generato con successo: {os.path.basename(result['file_path'])}", "success")
                if result.get('email_sent'):
                    flash("✅ Report inviato via email al CEO", "success")
                else:
                    flash("ℹ️ Report salvato su file (email disabilitata)", "info")
            else:
                flash(f"❌ Errore generazione report: {result.get('error', 'Errore sconosciuto')}", "danger")
                
        except Exception as e:
            current_app.logger.error(f"❌ Errore generazione report manuale: {e}")
            flash("❌ Errore generazione report", "danger")
    
    # Prepara i dati per il form
    current_year = datetime.now().year
    years = list(range(current_year - 2, current_year + 1))
    months = [
        (1, 'Gennaio'), (2, 'Febbraio'), (3, 'Marzo'), (4, 'Aprile'),
        (5, 'Maggio'), (6, 'Giugno'), (7, 'Luglio'), (8, 'Agosto'),
        (9, 'Settembre'), (10, 'Ottobre'), (11, 'Novembre'), (12, 'Dicembre')
    ]
    
    return render_template('ceo/genera_report.html', years=years, months=months)


@ceo_report_bp.route('/download/<filename>')
@login_required
@ceo_or_admin_required
def download_report(filename):
    """
    Scarica un report PDF.
    """
    try:
        reports_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reports')
        file_path = os.path.join(reports_dir, filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            flash("❌ File non trovato", "danger")
            return redirect(url_for('ceo_report.report_dashboard'))
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore download report: {e}")
        flash("❌ Errore download report", "danger")
        return redirect(url_for('ceo_report.report_dashboard'))


@ceo_report_bp.route('/visualizza/<filename>')
@login_required
@ceo_or_admin_required
def visualizza_report(filename):
    """
    Visualizza un report PDF nel browser.
    """
    try:
        reports_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reports')
        file_path = os.path.join(reports_dir, filename)
        
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='application/pdf')
        else:
            flash("❌ File non trovato", "danger")
            return redirect(url_for('ceo_report.report_dashboard'))
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore visualizzazione report: {e}")
        flash("❌ Errore visualizzazione report", "danger")
        return redirect(url_for('ceo_report.report_dashboard'))


@ceo_report_bp.route('/elimina/<filename>', methods=['POST'])
@login_required
@ceo_or_admin_required
def elimina_report(filename):
    """
    Elimina un report PDF.
    """
    try:
        reports_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reports')
        file_path = os.path.join(reports_dir, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            flash(f"✅ Report {filename} eliminato", "success")
        else:
            flash("❌ File non trovato", "danger")
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore eliminazione report: {e}")
        flash("❌ Errore eliminazione report", "danger")
    
    return redirect(url_for('ceo_report.report_dashboard'))


@ceo_report_bp.route('/test')
@login_required
@ceo_or_admin_required
def test_generazione():
    """
    Test della generazione report.
    """
    try:
        result = test_report_generation()
        
        if result:
            flash("✅ Test generazione report completato con successo", "success")
        else:
            flash("❌ Test generazione report fallito", "danger")
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore test generazione: {e}")
        flash("❌ Errore test generazione", "danger")
    
    return redirect(url_for('ceo_report.report_dashboard'))


@ceo_report_bp.route('/api/statistiche')
@login_required
@ceo_or_admin_required
def api_statistiche_report():
    """
    API per statistiche sui report.
    """
    try:
        reports_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'reports')
        
        if os.path.exists(reports_dir):
            report_files = glob.glob(os.path.join(reports_dir, 'report_ceo_*.pdf'))
            
            total_reports = len(report_files)
            total_size_mb = sum(os.path.getsize(f) / (1024 * 1024) for f in report_files)
            
            # Statistiche per anno
            stats_by_year = {}
            for file_path in report_files:
                try:
                    filename = os.path.basename(file_path)
                    parts = filename.replace('.pdf', '').split('_')
                    year = int(parts[-2])
                    
                    if year not in stats_by_year:
                        stats_by_year[year] = {'count': 0, 'size_mb': 0}
                    
                    stats_by_year[year]['count'] += 1
                    stats_by_year[year]['size_mb'] += os.path.getsize(file_path) / (1024 * 1024)
                except (ValueError, IndexError):
                    continue
            
            return jsonify({
                'success': True,
                'total_reports': total_reports,
                'total_size_mb': round(total_size_mb, 2),
                'stats_by_year': stats_by_year
            })
        else:
            return jsonify({
                'success': True,
                'total_reports': 0,
                'total_size_mb': 0,
                'stats_by_year': {}
            })
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore API statistiche report: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
