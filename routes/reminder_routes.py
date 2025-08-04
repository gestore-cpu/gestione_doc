"""
Routes per la gestione dei reminder automatici.
Dashboard per visualizzare scadenze e attività.
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from models import Reminder, User, ReminderLog
from decorators import roles_required
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

reminder_bp = Blueprint('reminder', __name__)

@reminder_bp.route('/dashboard/reminder', methods=['GET'])
@login_required
@roles_required(['admin', 'hr', 'auditor', 'ceo'])
def dashboard_reminder():
    """
    Dashboard per visualizzare tutti i reminder del sistema.
    Accessibile solo ad Admin, HR, Auditor e CEO.
    """
    try:
        from datetime import date
        
        oggi = date.today()
        
        # Ottieni tutti i reminder ordinati per scadenza
        reminders = Reminder.query.order_by(Reminder.scadenza.asc()).all()
        
        # Statistiche
        totali = len(reminders)
        attivi = len([r for r in reminders if r.stato == 'attivo'])
        inviati = len([r for r in reminders if r.stato == 'inviato'])
        scaduti = len([r for r in reminders if r.is_scaduto])
        urgenti = len([r for r in reminders if r.is_urgente])
        
        # Filtri
        tipo_filtro = request.args.get('tipo', '')
        stato_filtro = request.args.get('stato', '')
        utente_filtro = request.args.get('utente', '')
        
        # Applica filtri
        if tipo_filtro:
            reminders = [r for r in reminders if r.tipo == tipo_filtro]
        
        if stato_filtro:
            if stato_filtro == 'attivo':
                reminders = [r for r in reminders if r.stato == 'attivo']
            elif stato_filtro == 'inviato':
                reminders = [r for r in reminders if r.stato == 'inviato']
            elif stato_filtro == 'scaduto':
                reminders = [r for r in reminders if r.is_scaduto]
            elif stato_filtro == 'urgente':
                reminders = [r for r in reminders if r.is_urgente]
        
        if utente_filtro:
            reminders = [r for r in reminders if utente_filtro.lower() in r.destinatario_email.lower()]
        
        return render_template(
            "dashboard_reminder.html", 
            reminders=reminders, 
            oggi=oggi,
            totali=totali,
            attivi=attivi,
            inviati=inviati,
            scaduti=scaduti,
            urgenti=urgenti,
            tipo_filtro=tipo_filtro,
            stato_filtro=stato_filtro,
            utente_filtro=utente_filtro
        )
        
    except Exception as e:
        logger.error(f"Errore dashboard reminder: {str(e)}")
        flash("❌ Errore nel caricamento della dashboard reminder", "danger")
        return redirect(url_for('admin.dashboard'))

@reminder_bp.route('/api/reminder/<int:reminder_id>/toggle', methods=['POST'])
@login_required
@roles_required(['admin', 'hr', 'auditor'])
def toggle_reminder(reminder_id):
    """
    Attiva/disattiva un reminder specifico.
    """
    try:
        reminder = Reminder.query.get_or_404(reminder_id)
        
        if reminder.stato == 'attivo':
            reminder.stato = 'disabilitato'
            flash("✅ Reminder disabilitato", "success")
        else:
            reminder.stato = 'attivo'
            flash("✅ Reminder attivato", "success")
        
        from app import db
        db.session.commit()
        
        return jsonify({'success': True, 'stato': reminder.stato})
        
    except Exception as e:
        logger.error(f"Errore toggle reminder {reminder_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@reminder_bp.route('/api/reminder/<int:reminder_id>/delete', methods=['POST'])
@login_required
@roles_required(['admin'])
def delete_reminder(reminder_id):
    """
    Elimina un reminder (solo Admin).
    """
    try:
        reminder = Reminder.query.get_or_404(reminder_id)
        
        from app import db
        db.session.delete(reminder)
        db.session.commit()
        
        flash("✅ Reminder eliminato", "success")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Errore eliminazione reminder {reminder_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@reminder_bp.route('/api/reminder/stats', methods=['GET'])
@login_required
@roles_required(['admin', 'hr', 'auditor', 'ceo'])
def reminder_stats():
    """
    API per statistiche reminder (per grafici).
    """
    try:
        from datetime import date, timedelta
        
        oggi = date.today()
        
        # Statistiche per tipo
        stats_per_tipo = {}
        for reminder in Reminder.query.all():
            tipo = reminder.tipo
            if tipo not in stats_per_tipo:
                stats_per_tipo[tipo] = {'attivo': 0, 'inviato': 0, 'scaduto': 0}
            
            if reminder.stato == 'attivo':
                stats_per_tipo[tipo]['attivo'] += 1
            elif reminder.stato == 'inviato':
                stats_per_tipo[tipo]['inviato'] += 1
            elif reminder.is_scaduto:
                stats_per_tipo[tipo]['scaduto'] += 1
        
        # Statistiche per giorno (ultimi 30 giorni)
        stats_per_giorno = {}
        for i in range(30):
            data = oggi - timedelta(days=i)
            stats_per_giorno[data.strftime('%Y-%m-%d')] = {
                'scadenze': 0,
                'invii': 0
            }
        
        # Conta scadenze e invii per giorno
        for reminder in Reminder.query.all():
            data_scadenza = reminder.scadenza.date()
            data_str = data_scadenza.strftime('%Y-%m-%d')
            
            if data_str in stats_per_giorno:
                stats_per_giorno[data_str]['scadenze'] += 1
            
            if reminder.ultimo_invio:
                data_invio = reminder.ultimo_invio.date()
                data_invio_str = data_invio.strftime('%Y-%m-%d')
                if data_invio_str in stats_per_giorno:
                    stats_per_giorno[data_invio_str]['invii'] += 1
        
        return jsonify({
            'stats_per_tipo': stats_per_tipo,
            'stats_per_giorno': stats_per_giorno
        })
        
    except Exception as e:
        logger.error(f"Errore statistiche reminder: {str(e)}")
        return jsonify({'error': str(e)})

@reminder_bp.route('/dashboard/reminder/export/csv', methods=['GET'])
@login_required
@roles_required(['admin', 'hr', 'ceo'])
def export_reminder_csv():
    """
    Esporta reminder in formato CSV semplificato.
    """
    try:
        import csv
        from io import StringIO
        from flask import make_response
        
        reminders = Reminder.query.order_by(Reminder.scadenza.asc()).all()
        
        si = StringIO()
        writer = csv.writer(si)
        
        # Header semplificato
        writer.writerow(['ID', 'Tipo', 'Destinatario', 'Ruolo', 'Messaggio', 'Scadenza', 'Stato', 'Ultimo Invio'])
        
        # Dati
        for r in reminders:
            writer.writerow([
                r.id,
                r.tipo_display,
                r.destinatario_email,
                r.destinatario_ruolo,
                r.messaggio or '',
                r.scadenza.strftime("%d/%m/%Y") if r.scadenza else '',
                r.stato_display,
                r.ultimo_invio.strftime("%d/%m/%Y %H:%M") if r.ultimo_invio else 'Non inviato'
            ])
        
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=reminder_synthia.csv"
        output.headers["Content-type"] = "text/csv"
        return output
        
    except Exception as e:
        logger.error(f"Errore export CSV reminder: {str(e)}")
        flash("❌ Errore nell'esportazione CSV", "danger")
        return redirect(url_for('reminder.dashboard_reminder'))

@reminder_bp.route('/api/reminder/export/csv', methods=['GET'])
@login_required
@roles_required(['admin', 'hr', 'auditor', 'ceo'])
def export_reminder_csv():
    """
    Esporta reminder in formato CSV.
    """
    try:
        import csv
        from io import StringIO
        from flask import Response
        
        reminders = Reminder.query.order_by(Reminder.scadenza.asc()).all()
        
        si = StringIO()
        cw = csv.writer(si)
        
        # Header
        cw.writerow([
            'ID', 'Tipo', 'Entità ID', 'Entità Tipo', 'Destinatario Email',
            'Destinatario Ruolo', 'Scadenza', 'Giorni Anticipo', 'Stato',
            'Ultimo Invio', 'Prossimo Invio', 'Messaggio', 'Canale',
            'Creato il', 'Creato da'
        ])
        
        # Dati
        for reminder in reminders:
            cw.writerow([
                reminder.id,
                reminder.tipo,
                reminder.entita_id,
                reminder.entita_tipo,
                reminder.destinatario_email,
                reminder.destinatario_ruolo,
                reminder.scadenza.strftime('%Y-%m-%d %H:%M:%S') if reminder.scadenza else '',
                reminder.giorni_anticipo,
                reminder.stato,
                reminder.ultimo_invio.strftime('%Y-%m-%d %H:%M:%S') if reminder.ultimo_invio else '',
                reminder.prossimo_invio.strftime('%Y-%m-%d %H:%M:%S') if reminder.prossimo_invio else '',
                reminder.messaggio or '',
                reminder.canale,
                reminder.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                reminder.created_by
            ])
        
        output = si.getvalue()
        si.close()
        
        return Response(
            output,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=reminder_export.csv'}
        )
        
    except Exception as e:
        logger.error(f"Errore export CSV reminder: {str(e)}")
        flash("❌ Errore nell'esportazione CSV", "danger")
        return redirect(url_for('reminder.dashboard_reminder'))

@reminder_bp.route('/dashboard/reminder/export/pdf', methods=['GET'])
@login_required
@roles_required(['admin', 'hr', 'ceo'])
def export_reminder_pdf():
    """
    Esporta reminder in formato PDF.
    """
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from flask import send_file
        from datetime import datetime
        
        reminders = Reminder.query.order_by(Reminder.scadenza.asc()).all()
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 50
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, "SYNTHIA DOCS – Report Reminder")
        y -= 30
        
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        y -= 30
        
        c.drawString(50, y, f"Totale reminder: {len(reminders)}")
        y -= 40
        
        # Tabella header
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Scadenza")
        c.drawString(120, y, "Tipo")
        c.drawString(200, y, "Destinatario")
        c.drawString(300, y, "Stato")
        y -= 20
        
        c.setFont("Helvetica", 9)
        
        for r in reminders:
            if y < 80:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 9)
            
            # Scadenza
            scadenza = r.scadenza.strftime('%d/%m/%Y') if r.scadenza else 'N/A'
            c.drawString(50, y, scadenza)
            
            # Tipo
            tipo = r.tipo_display[:15] if len(r.tipo_display) > 15 else r.tipo_display
            c.drawString(120, y, tipo)
            
            # Destinatario
            destinatario = r.destinatario_email[:20] if len(r.destinatario_email) > 20 else r.destinatario_email
            c.drawString(200, y, destinatario)
            
            # Stato
            stato = "✅ Inviato" if r.stato == 'inviato' else "⏳ Attivo" if r.stato == 'attivo' else "❌ Scaduto"
            c.drawString(300, y, stato)
            
            y -= 15
            
            # Messaggio (se c'è spazio)
            if r.messaggio and y > 100:
                messaggio = r.messaggio[:50] + "..." if len(r.messaggio) > 50 else r.messaggio
                c.drawString(70, y, messaggio)
                y -= 15
        
        # Footer
        c.showPage()
        y = height - 50
        c.setFont("Helvetica", 10)
        c.drawString(50, y, "SYNTHIA DOCS - Sistema di Gestione Documentale")
        y -= 20
        c.drawString(50, y, "Report generato automaticamente")
        
        c.save()
        buffer.seek(0)
        
        return send_file(
            buffer, 
            mimetype='application/pdf', 
            as_attachment=True, 
            download_name="reminder_synthia.pdf"
        )
        
    except Exception as e:
        logger.error(f"Errore export PDF reminder: {str(e)}")
        flash("❌ Errore nell'esportazione PDF", "danger")
        return redirect(url_for('reminder.dashboard_reminder'))

@reminder_bp.route('/api/reminder/logs/<int:reminder_id>', methods=['GET'])
@login_required
@roles_required(['admin', 'hr', 'auditor'])
def reminder_logs(reminder_id):
    """
    Visualizza i log di invio per un reminder specifico.
    """
    try:
        reminder = Reminder.query.get_or_404(reminder_id)
        logs = ReminderLog.query.filter_by(reminder_id=reminder_id).order_by(ReminderLog.timestamp.desc()).all()
        
        return render_template(
            "reminder_logs.html",
            reminder=reminder,
            logs=logs
        )
        
    except Exception as e:
        logger.error(f"Errore visualizzazione log reminder {reminder_id}: {str(e)}")
        flash("❌ Errore nel caricamento dei log", "danger")
        return redirect(url_for('reminder.dashboard_reminder')) 