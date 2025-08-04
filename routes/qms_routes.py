from flask import Blueprint, render_template, jsonify, request, current_app, send_file
from flask_login import login_required, current_user
from models import db, AdminLog, InsightQMSAI, EventoFormazione, PartecipazioneFormazione
from ai.qms_ai import analizza_documenti_qms, trasforma_qms_insight_in_task
from datetime import datetime
from decorators import admin_required
import csv
from io import StringIO
from utils_extra import generate_pdf_copertura_eventi
import os
from flask import Response
from models import User

qms_bp = Blueprint('qms', __name__)

@qms_bp.route("/admin/qms_ai_insights")
@login_required
def qms_ai_insights():
    """Pagina per visualizzare gli insight AI QMS"""
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    insights = InsightQMSAI.query.filter_by(stato="attivo").order_by(InsightQMSAI.data_creazione.desc()).all()
    
    # Statistiche
    totali = {
        'totali': InsightQMSAI.query.count(),
        'critici': InsightQMSAI.query.filter_by(severity='critico', stato='attivo').count(),
        'attenzione': InsightQMSAI.query.filter_by(severity='attenzione', stato='attivo').count(),
        'risolti': InsightQMSAI.query.filter_by(stato='risolto').count()
    }
    
    return render_template('admin/qms_ai_insights.html', insights=insights, totali=totali)

@qms_bp.route("/admin/api/qms_ai/genera", methods=["POST"])
@login_required
def genera_insight_qms():
    """Genera nuovi insight AI per i documenti QMS"""
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        insights = analizza_documenti_qms(db.session)
        
        # Evita duplicati - controlla se esistono già insight simili
        for insight in insights:
            existing = InsightQMSAI.query.filter_by(
                documento_id=insight.documento_id,
                insight_type=insight.insight_type,
                stato='attivo'
            ).first()
            
            if not existing:
                db.session.add(insight)
        
        db.session.commit()
        
        # Log dell'azione
        admin_log = AdminLog(
            action="generazione_insight_qms_ai",
            performed_by=current_user.email,
            extra_info=f"Generati {len(insights)} insight QMS"
        )
        db.session.add(admin_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'generati': len(insights),
            'message': f'Generati {len(insights)} nuovi insight QMS'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore generazione insight QMS: {e}")
        return jsonify({'error': 'Errore durante la generazione degli insight'}), 500

@qms_bp.route("/admin/api/qms_ai/<int:insight_id>/task", methods=["POST"])
@login_required
def trasforma_qms_insight_in_task_api(insight_id):
    """Trasforma un insight QMS in task"""
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    task_id = trasforma_qms_insight_in_task(insight_id)
    if task_id:
        return jsonify({
            'success': True, 
            'task_id': task_id, 
            'message': f'Insight QMS trasformato in task ID: {task_id}'
        })
    else:
        return jsonify({'success': False, 'error': 'Errore nella trasformazione dell\'insight in task'}), 400

@qms_bp.route("/admin/api/qms_ai/<int:insight_id>/resolve", methods=["POST"])
@login_required
def resolve_qms_insight(insight_id):
    """Marca un insight QMS come risolto"""
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        insight = InsightQMSAI.query.get(insight_id)
        if insight:
            insight.stato = "risolto"
            insight.resolved_at = datetime.utcnow()
            insight.resolved_by = current_user.email
            
            admin_log = AdminLog(
                action="risoluzione_insight_qms",
                performed_by=current_user.email,
                extra_info=f"Insight QMS ID: {insight_id} risolto"
            )
            db.session.add(admin_log)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Insight risolto con successo'})
        else:
            return jsonify({'error': 'Insight non trovato'}), 404
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante la risoluzione'}), 500

@qms_bp.route("/admin/api/qms_ai/<int:insight_id>/ignore", methods=["POST"])
@login_required
def ignore_qms_insight(insight_id):
    """Marca un insight QMS come ignorato"""
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        insight = InsightQMSAI.query.get(insight_id)
        if insight:
            insight.stato = "ignorato"
            insight.resolved_at = datetime.utcnow()
            insight.resolved_by = current_user.email
            
            admin_log = AdminLog(
                action="ignoramento_insight_qms",
                performed_by=current_user.email,
                extra_info=f"Insight QMS ID: {insight_id} ignorato"
            )
            db.session.add(admin_log)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Insight ignorato con successo'})
        else:
            return jsonify({'error': 'Insight non trovato'}), 404
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante l\'ignoramento'}), 500 

@qms_bp.route("/admin/eventi/copertura")
@login_required
@admin_required
def dashboard_copertura_eventi():
    """
    Dashboard per monitorare la copertura attestati per ogni evento di formazione.
    
    Returns:
        Template con dati dashboard copertura eventi
    """
    eventi = EventoFormazione.query.all()
    dati_dashboard = []
    alert_ai = []

    for evento in eventi:
        partecipazioni = evento.partecipazioni
        tot = len(partecipazioni)
        firmati = sum(1 for p in partecipazioni if p.firma_presenza_path)
        completati = sum(1 for p in partecipazioni if p.attestato_path and p.completato)

        percentuale = round((completati / tot) * 100, 1) if tot > 0 else 0

        # Determina stato basato su percentuale
        if percentuale == 100:
            stato = "completato"
            badge_class = "success"
        elif percentuale >= 60:
            stato = "parziale"
            badge_class = "warning"
        else:
            stato = "incompleto"
            badge_class = "danger"

        # Genera alert AI per anomalie
        if tot > 0:
            if firmati > completati:
                alert_ai.append({
                    "tipo": "firma_senza_attestato",
                    "evento": evento.titolo,
                    "conteggio": firmati - completati,
                    "severity": "warning",
                    "messaggio": f"{firmati - completati} partecipanti hanno firmato ma non hanno attestato"
                })
            elif completati > firmati:
                alert_ai.append({
                    "tipo": "attestato_senza_firma",
                    "evento": evento.titolo,
                    "conteggio": completati - firmati,
                    "severity": "danger",
                    "messaggio": f"{completati - firmati} attestati generati senza firma presenza"
                })
            
            # Alert per scadenza prossima
            if evento.data_evento:
                giorni_dalla_data = (datetime.now() - evento.data_evento).days
                if giorni_dalla_data > 7 and percentuale < 100:
                    alert_ai.append({
                        "tipo": "scadenza_prossima",
                        "evento": evento.titolo,
                        "conteggio": tot - completati,
                        "severity": "danger",
                        "messaggio": f"Evento di {giorni_dalla_data} giorni fa: {tot - completati} attestati mancanti"
                    })

        dati_dashboard.append({
            "evento": evento,
            "tot": tot,
            "firmati": firmati,
            "completati": completati,
            "percentuale": percentuale,
            "stato": stato,
            "badge_class": badge_class
        })

    return render_template("admin/copertura_eventi.html", 
                         dashboard=dati_dashboard, 
                         alert_ai=alert_ai)

@qms_bp.route("/admin/eventi/copertura/export")
@login_required
@admin_required
def export_copertura_csv():
    """
    Esporta i dati di copertura attestati in formato CSV.
    
    Returns:
        File CSV con dati copertura eventi
    """
    eventi = EventoFormazione.query.all()
    
    # Crea buffer per CSV
    si = StringIO()
    cw = csv.writer(si)
    
    # Header CSV
    cw.writerow([
        'Titolo Evento', 'Data', 'Totale Partecipanti', 
        'Firmati Presenza', 'Attestati Completati', 
        'Percentuale Copertura', 'Stato'
    ])
    
    for evento in eventi:
        partecipazioni = evento.partecipazioni
        tot = len(partecipazioni)
        firmati = sum(1 for p in partecipazioni if p.firma_presenza_path)
        completati = sum(1 for p in partecipazioni if p.attestato_path and p.completato)
        percentuale = round((completati / tot) * 100, 1) if tot > 0 else 0
        
        if percentuale == 100:
            stato = "completato"
        elif percentuale >= 60:
            stato = "parziale"
        else:
            stato = "incompleto"
        
        cw.writerow([
            evento.titolo,
            evento.data_evento.strftime('%d/%m/%Y') if evento.data_evento else 'N/A',
            tot,
            firmati,
            completati,
            f"{percentuale}%",
            stato
        ])
    
    output = si.getvalue()
    si.close()
    
    return send_file(
        StringIO(output),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'copertura_attestati_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    ) 

@qms_bp.route("/admin/eventi/copertura/pdf")
@login_required
@admin_required
def export_copertura_pdf():
    """
    Genera e scarica un PDF della dashboard copertura attestati.
    
    Returns:
        File PDF con report copertura attestati
    """
    eventi = EventoFormazione.query.all()
    dati_dashboard = []
    alert_ai = []
    
    # Calcola statistiche generali
    stats = {
        'total_eventi': len(eventi),
        'total_partecipanti': 0,
        'total_attestati': 0,
        'media_copertura': 0
    }

    for evento in eventi:
        partecipazioni = evento.partecipazioni
        tot = len(partecipazioni)
        firmati = sum(1 for p in partecipazioni if p.firma_presenza_path)
        completati = sum(1 for p in partecipazioni if p.attestato_path and p.completato)

        percentuale = round((completati / tot) * 100, 1) if tot > 0 else 0

        if percentuale == 100:
            stato = "completato"
        elif percentuale >= 60:
            stato = "parziale"
        else:
            stato = "incompleto"

        # Aggiorna statistiche generali
        stats['total_partecipanti'] += tot
        stats['total_attestati'] += completati

        # Genera alert AI
        if tot > 0:
            if firmati > completati:
                alert_ai.append(f"{firmati - completati} partecipanti hanno firmato ma non hanno attestato - {evento.titolo}")
            elif completati > firmati:
                alert_ai.append(f"{completati - firmati} attestati generati senza firma presenza - {evento.titolo}")
            
            if evento.data_evento:
                giorni_dalla_data = (datetime.now() - evento.data_evento).days
                if giorni_dalla_data > 7 and percentuale < 100:
                    alert_ai.append(f"Evento di {giorni_dalla_data} giorni fa: {tot - completati} attestati mancanti - {evento.titolo}")

        dati_dashboard.append({
            "titolo": evento.titolo,
            "data": evento.data_evento.strftime('%d/%m/%Y') if evento.data_evento else 'N/A',
            "totale": tot,
            "firme": firmati,
            "attestati": completati,
            "percentuale": percentuale,
            "stato": stato
        })

    # Calcola media copertura
    if stats['total_partecipanti'] > 0:
        stats['media_copertura'] = round(
            (stats['total_attestati'] / stats['total_partecipanti']) * 100, 1
        )

    try:
        # Genera il PDF
        file_path = generate_pdf_copertura_eventi(
            eventi=dati_dashboard,
            alert_ai=alert_ai,
            user_email=current_user.email,
            stats=stats
        )
        
        # Log dell'azione
        admin_log = AdminLog(
            action="export_pdf_copertura_attestati",
            performed_by=current_user.email,
            extra_info=f"Generato PDF copertura attestati con {len(dati_dashboard)} eventi"
        )
        db.session.add(admin_log)
        db.session.commit()
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f'copertura_attestati_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore generazione PDF copertura: {e}")
        return jsonify({'error': 'Errore durante la generazione del PDF'}), 500 

@qms_bp.route("/eventi/<int:evento_id>/verifica_audit", methods=["GET"])
@login_required
@admin_required
def verifica_audit_attestati(evento_id):
    """
    Verifica audit-ready degli attestati per un evento formativo.
    
    Args:
        evento_id (int): ID dell'evento da verificare
        
    Returns:
        JSON con stato e problemi rilevati
    """
    try:
        from models import EventoFormazione, PartecipazioneFormazione, AuditVerificaLog
        
        evento = EventoFormazione.query.get_or_404(evento_id)
        partecipazioni = PartecipazioneFormazione.query.filter_by(evento_id=evento_id).all()
        
        problemi = []
        for partecipazione in partecipazioni:
            user = partecipazione.user
            
            # Verifica firma presenza
            firma_ok = partecipazione.firma_presenza_path is not None and os.path.exists(partecipazione.firma_presenza_path)
            
            # Verifica attestato
            attestato_ok = partecipazione.attestato_path is not None and os.path.exists(partecipazione.attestato_path)
            
            if not firma_ok or not attestato_ok:
                problemi.append({
                    "nome": user.nome_completo() if hasattr(user, 'nome_completo') else f"{user.first_name} {user.last_name}",
                    "email": user.email,
                    "firma": "✅" if firma_ok else "❌",
                    "attestato": "✅" if attestato_ok else "❌",
                    "partecipazione_id": partecipazione.id
                })
        
        stato = "completo" if len(problemi) == 0 else "incompleto"
        
        # Salva log audit con dettagli
        import json
        log = AuditVerificaLog(
            evento_id=evento_id,
            esito=stato,
            data=datetime.utcnow(),
            anomalie=len(problemi),
            dettagli_problemi=json.dumps(problemi) if problemi else None
        )
        db.session.add(log)
        db.session.commit()
        
        # Invia notifica AI se ci sono problemi
        if len(problemi) > 0:
            invia_notifica_audit(evento, problemi)
        
        return jsonify({
            "stato": stato, 
            "problemi": problemi,
            "evento_titolo": evento.titolo,
            "totale_partecipanti": len(partecipazioni),
            "problemi_count": len(problemi),
            "evento_id": evento_id
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore verifica audit evento {evento_id}: {e}")
        return jsonify({'error': str(e)}), 500

@qms_bp.route("/eventi/<int:evento_id>/verifica_audit/export", methods=["GET"])
@login_required
@admin_required
def export_verifica_audit(evento_id):
    """
    Esporta i risultati della verifica audit in CSV.
    
    Args:
        evento_id (int): ID dell'evento
        
    Returns:
        CSV file con i risultati
    """
    try:
        from models import EventoFormazione, PartecipazioneFormazione
        
        evento = EventoFormazione.query.get_or_404(evento_id)
        partecipazioni = PartecipazioneFormazione.query.filter_by(evento_id=evento_id).all()
        
        # Crea CSV in memoria
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Nome', 'Email', 'Firma Presenza', 'Attestato', 'Stato Partecipazione', 'Data Completamento'])
        
        # Dati
        for partecipazione in partecipazioni:
            user = partecipazione.user
            
            # Verifica file
            firma_ok = partecipazione.firma_presenza_path is not None and os.path.exists(partecipazione.firma_presenza_path)
            attestato_ok = partecipazione.attestato_path is not None and os.path.exists(partecipazione.attestato_path)
            
            writer.writerow([
                user.nome_completo() if hasattr(user, 'nome_completo') else f"{user.first_name} {user.last_name}",
                user.email,
                "✅ Presente" if firma_ok else "❌ Mancante",
                "✅ Presente" if attestato_ok else "❌ Mancante",
                partecipazione.stato_partecipazione,
                partecipazione.data_completamento.strftime('%d/%m/%Y %H:%M') if partecipazione.data_completamento else "N/A"
            ])
        
        # Prepara response
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=audit_evento_{evento_id}_{datetime.now().strftime("%Y%m%d")}.csv'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore export audit evento {evento_id}: {e}")
        return jsonify({'error': str(e)}), 500 

@qms_bp.route("/eventi/<int:evento_id>/verifica_audit/export_csv", methods=["GET"])
@login_required
@admin_required
def export_audit_csv(evento_id):
    """
    Esporta i risultati della verifica audit in CSV con dettagli completi.
    
    Args:
        evento_id (int): ID dell'evento
        
    Returns:
        CSV file con risultati audit dettagliati
    """
    try:
        from models import EventoFormazione, PartecipazioneFormazione, AuditVerificaLog
        
        evento = EventoFormazione.query.get_or_404(evento_id)
        partecipazioni = PartecipazioneFormazione.query.filter_by(evento_id=evento_id).all()
        
        # Crea CSV in memoria
        output = StringIO()
        writer = csv.writer(output)
        
        # Header con informazioni evento
        writer.writerow(['AUDIT VERIFICA EVENTO FORMATIVO'])
        writer.writerow([])
        writer.writerow(['Evento:', evento.titolo])
        writer.writerow(['Data Evento:', evento.data_evento.strftime('%d/%m/%Y') if evento.data_evento else 'N/A'])
        writer.writerow(['Durata Ore:', evento.durata_ore])
        writer.writerow(['Stato Evento:', evento.stato])
        writer.writerow(['Data Verifica Audit:', datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
        writer.writerow([])
        
        # Header tabella
        writer.writerow(['Nome', 'Email', 'Firma', 'Attestato'])
        
        # Dati partecipanti
        problemi = []
        for partecipazione in partecipazioni:
            user = partecipazione.user
            firma_ok = partecipazione.firma_presenza_path is not None and os.path.exists(partecipazione.firma_presenza_path)
            attestato_ok = partecipazione.attestato_path is not None and os.path.exists(partecipazione.attestato_path)
            
            if not firma_ok or not attestato_ok:
                problemi.append({
                    "nome": user.nome_completo() if hasattr(user, 'nome_completo') else f"{user.first_name} {user.last_name}",
                    "email": user.email,
                    "firma": "✅" if firma_ok else "❌",
                    "attestato": "✅" if attestato_ok else "❌"
                })
            
            writer.writerow([
                user.nome_completo() if hasattr(user, 'nome_completo') else f"{user.first_name} {user.last_name}",
                user.email,
                "✅" if firma_ok else "❌",
                "✅" if attestato_ok else "❌"
            ])
        
        # Footer con statistiche
        writer.writerow([])
        writer.writerow(['STATISTICHE AUDIT'])
        writer.writerow(['Totale Partecipanti:', len(partecipazioni)])
        writer.writerow(['Problemi Rilevati:', len(problemi)])
        firme_mancanti = sum(1 for p in problemi if p.get('firma') == '❌')
        attestati_mancanti = sum(1 for p in problemi if p.get('attestato') == '❌')
        writer.writerow(['Firme Mancanti:', firme_mancanti])
        writer.writerow(['Attestati Mancanti:', attestati_mancanti])
        writer.writerow(['Percentuale Problemi:', f"{(len(problemi) / max(len(partecipazioni), 1) * 100):.1f}%" if partecipazioni else "0%"])
        
        # Prepara response
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=audit_evento_{evento_id}_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore export CSV audit evento {evento_id}: {e}")
        return jsonify({'error': str(e)}), 500

@qms_bp.route("/eventi/<int:evento_id>/verifica_audit/export_pdf", methods=["GET"])
@login_required
@admin_required
def export_audit_pdf(evento_id):
    """
    Esporta i risultati della verifica audit in PDF con logo e firma.
    
    Args:
        evento_id (int): ID dell'evento
        
    Returns:
        PDF file con risultati audit e firma finale
    """
    try:
        from models import EventoFormazione, PartecipazioneFormazione
        from io import BytesIO
        from flask import send_file
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.units import inch
        
        evento = EventoFormazione.query.get_or_404(evento_id)
        partecipazioni = PartecipazioneFormazione.query.filter_by(evento_id=evento_id).all()
        
        # Crea buffer per PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Stili
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Centrato
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=20
        )
        normal_style = styles['Normal']
        
        # === Titolo principale ===
        story.append(Paragraph("📋 REPORT VERIFICA AUDIT EVENTO FORMATIVO", title_style))
        story.append(Spacer(1, 20))
        
        # === Informazioni evento ===
        story.append(Paragraph(f"<b>Evento:</b> {evento.titolo}", subtitle_style))
        story.append(Paragraph(f"<b>Data Evento:</b> {evento.data_evento.strftime('%d/%m/%Y') if evento.data_evento else 'N/A'}", normal_style))
        story.append(Paragraph(f"<b>Durata Ore:</b> {evento.durata_ore}", normal_style))
        story.append(Paragraph(f"<b>Stato Evento:</b> {evento.stato}", normal_style))
        story.append(Paragraph(f"<b>Data Generazione Report:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_style))
        story.append(Spacer(1, 20))
        
        # === Tabella partecipanti ===
        story.append(Paragraph("<b>DETTAGLIO PARTECIPANTI</b>", subtitle_style))
        
        # Prepara dati tabella
        table_data = [['Nome', 'Email', 'Firma', 'Attestato']]
        problemi = []
        
        for partecipazione in partecipazioni:
            user = partecipazione.user
            firma_ok = partecipazione.firma_presenza_path is not None and os.path.exists(partecipazione.firma_presenza_path)
            attestato_ok = partecipazione.attestato_path is not None and os.path.exists(partecipazione.attestato_path)
            
            if not firma_ok or not attestato_ok:
                problemi.append({
                    "nome": user.nome_completo() if hasattr(user, 'nome_completo') else f"{user.first_name} {user.last_name}",
                    "email": user.email,
                    "firma": "✅" if firma_ok else "❌",
                    "attestato": "✅" if attestato_ok else "❌"
                })
            
            table_data.append([
                user.nome_completo() if hasattr(user, 'nome_completo') else f"{user.first_name} {user.last_name}",
                user.email,
                "✅" if firma_ok else "❌",
                "✅" if attestato_ok else "❌"
            ])
        
        # Crea tabella
        table = Table(table_data, colWidths=[2*inch, 2.5*inch, 0.8*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (3, -1), 'CENTER'),  # Centra le colonne firma e attestato
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        # === Statistiche ===
        story.append(Paragraph("<b>STATISTICHE AUDIT</b>", subtitle_style))
        story.append(Paragraph(f"• Totale Partecipanti: {len(partecipazioni)}", normal_style))
        story.append(Paragraph(f"• Problemi Rilevati: {len(problemi)}", normal_style))
        firme_mancanti = sum(1 for p in problemi if p.get('firma') == '❌')
        attestati_mancanti = sum(1 for p in problemi if p.get('attestato') == '❌')
        story.append(Paragraph(f"• Firme Mancanti: {firme_mancanti}", normal_style))
        story.append(Paragraph(f"• Attestati Mancanti: {attestati_mancanti}", normal_style))
        percentuale = (len(problemi) / max(len(partecipazioni), 1) * 100) if partecipazioni else 0
        story.append(Paragraph(f"• Percentuale Problemi: {percentuale:.1f}%", normal_style))
        story.append(Spacer(1, 30))
        
        # === Firma finale ===
        story.append(Paragraph("______________________________", normal_style))
        story.append(Paragraph("<b>Firma RSPP / CEO</b>", subtitle_style))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Documento generato da SYNTHIA-QMS il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}", normal_style))
        
        # Genera PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"audit_evento_{evento_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore export PDF audit evento {evento_id}: {e}")
        return jsonify({'error': str(e)}), 500

@qms_bp.route("/eventi/<int:evento_id>/download_attestati_zip", methods=["GET"])
@login_required
@admin_required
def download_attestati_zip(evento_id):
    """
    Download ZIP con tutti gli attestati firmati per un evento.
    
    Args:
        evento_id (int): ID dell'evento formativo.
        
    Returns:
        ZIP: File ZIP contenente tutti gli attestati PDF.
    """
    try:
        import zipfile
        from io import BytesIO
        from flask import make_response
        
        evento = EventoFormazione.query.get_or_404(evento_id)
        
        # Ottieni partecipazioni con attestati
        partecipazioni = PartecipazioneFormazione.query.filter_by(evento_id=evento_id).all()
        
        # Crea ZIP in memoria
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # Contatore attestati aggiunti
            attestati_aggiunti = 0
            
            for partecipazione in partecipazioni:
                user = partecipazione.user
                
                # Verifica se l'attestato esiste
                if partecipazione.attestato_path and os.path.exists(partecipazione.attestato_path):
                    try:
                        # Nome file nel ZIP
                        nome_file = f"{user.first_name}_{user.last_name}_attestato.pdf"
                        nome_file = nome_file.replace(" ", "_").replace("'", "").replace('"', "")
                        
                        # Aggiungi file al ZIP
                        zip_file.write(partecipazione.attestato_path, nome_file)
                        attestati_aggiunti += 1
                        
                    except Exception as e:
                        current_app.logger.error(f"Errore aggiunta attestato {partecipazione.attestato_path}: {e}")
                        continue
            
            # Aggiungi file README con informazioni
            readme_content = f"""ATTESTATI EVENTO FORMATIVO

Evento: {evento.titolo}
Data: {evento.data_evento.strftime('%d/%m/%Y') if evento.data_evento else 'N/A'}
Durata: {evento.durata_ore} ore
Trainer: {evento.trainer or 'N/A'}

Totale partecipanti: {len(partecipazioni)}
Attestati inclusi: {attestati_aggiunti}
Attestati mancanti: {len(partecipazioni) - attestati_aggiunti}

Data generazione: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Generato da: {current_user.username}

NOTA: Questo ZIP contiene tutti gli attestati PDF firmati disponibili per l'evento.
Gli attestati mancanti non sono stati inclusi nel download.
"""
            
            zip_file.writestr("README.txt", readme_content)
        
        # Prepara response
        zip_buffer.seek(0)
        zip_data = zip_buffer.getvalue()
        zip_buffer.close()
        
        # Nome file ZIP
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"attestati_evento_{evento_id}_{timestamp}.zip"
        
        response = make_response(zip_data)
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Log dell'azione
        current_app.logger.info(f"Download ZIP attestati evento {evento_id} da {current_user.username}")
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Errore download ZIP attestati: {e}")
        return jsonify({'error': 'Errore durante il download degli attestati'}), 500

def invia_notifica_audit(evento, problemi):
    """
    Invia notifica AI per problemi audit rilevati.
    
    Args:
        evento (EventoFormazione): Evento verificato
        problemi (list): Lista dei problemi rilevati
        
    Returns:
        bool: True se inviata con successo
    """
    try:
        from flask_mail import Message
        from extensions import mail
        
        if not problemi or len(problemi) == 0:
            return True  # Nessun problema da notificare
        
        # Trova il responsabile dell'evento (assumiamo admin)
        admin_users = User.query.filter_by(role='admin').all()
        if not admin_users:
            current_app.logger.warning("Nessun admin trovato per notifica audit")
            return False
        
        # Prepara suggerimenti AI
        suggerimenti = []
        firme_mancanti = []
        attestati_mancanti = []
        
        for problema in problemi:
            if problema["firma"] == "❌":
                firme_mancanti.append(problema["nome"])
                suggerimenti.append(f"🔔 Firma mancante: {problema['nome']} ({problema['email']})")
            if problema["attestato"] == "❌":
                attestati_mancanti.append(problema["nome"])
                suggerimenti.append(f"📄 Attestato mancante: {problema['nome']} ({problema['email']})")
        
        # Costruisci messaggio
        messaggio = f"""
🛡️ VERIFICA AUDIT EVENTO FORMATIVO

Evento: {evento.titolo}
Data: {evento.data_evento.strftime('%d/%m/%Y') if evento.data_evento else 'N/A'}
Partecipanti totali: {len(problemi) + (evento.partecipanti_totali - len(problemi))}
Problemi rilevati: {len(problemi)}

📋 DETTAGLIO PROBLEMI:
{chr(10).join(suggerimenti)}

🎯 SUGGERIMENTI AI:
"""
        
        if firme_mancanti:
            messaggio += f"• Contattare {len(firme_mancanti)} partecipanti per firma presenza\n"
        if attestati_mancanti:
            messaggio += f"• Generare {len(attestati_mancanti)} attestati mancanti\n"
        
        messaggio += f"""
📊 STATISTICHE:
• Firme mancanti: {len(firme_mancanti)}
• Attestati mancanti: {len(attestati_mancanti)}
• Percentuale problemi: {(len(problemi) / evento.partecipanti_totali * 100):.1f}%

🔧 AZIONI RACCOMANDATE:
1. Inviare reminder ai partecipanti con firma mancante
2. Generare attestati per i partecipanti completati
3. Verificare documentazione per audit compliance
4. Pianificare follow-up per completamento

---
Sistema QMS - Audit Automatico
Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
        
        # Invia email a tutti gli admin
        for admin in admin_users:
            try:
                msg = Message(
                    subject=f"🛡️ Audit Check Formazione – Anomalie Rilevate: {evento.titolo}",
                    recipients=[admin.email],
                    body=messaggio,
                    sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@company.com')
                )
                mail.send(msg)
                current_app.logger.info(f"Notifica audit inviata a {admin.email}")
            except Exception as e:
                current_app.logger.error(f"Errore invio notifica audit a {admin.email}: {e}")
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Errore generazione notifica audit: {e}")
        return False 