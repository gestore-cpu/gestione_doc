"""
Route per la dashboard CEO.
"""

from flask import Blueprint, render_template, jsonify, request, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from models import Document, FirmaDocumento, AuditLog, db
from datetime import datetime
from datetime import datetime, timedelta
from decorators import ceo_required

ceo_bp = Blueprint('ceo_dashboard', __name__)


@ceo_bp.route("/ceo/docs")
@login_required
@ceo_required
def dashboard_docs_ceo():
    """
    Dashboard CEO per i documenti.
    
    Returns:
        Template con statistiche e trend documentali
    """
    try:
        # Filtro modulo
        modulo_filter = request.args.get('modulo')
        
        # Query base per statistiche
        base_query = Document.query
        if modulo_filter:
            base_query = base_query.filter_by(collegato_a_modulo=modulo_filter)
        
        # Statistiche generali
        documenti_totali = base_query.count()
        documenti_danni = base_query.filter_by(tag="Danno").count()
        documenti_policy = base_query.filter(
            Document.tag.in_(["Risorse Umane", "Policy", "Regolamento"])
        ).count()
        documenti_qms = Document.query.filter_by(collegato_a_modulo="qms").count()
        documenti_service = Document.query.filter_by(collegato_a_modulo="service").count()
        documenti_elevate = Document.query.filter_by(collegato_a_modulo="elevate").count()
        
        # Firme mancanti
        documenti_obbligatori = Document.query.filter(
            Document.tag.in_(["Risorse Umane", "Policy", "Regolamento", "Sicurezza"])
        ).all()
        
        firme_mancanti = 0
        documenti_senza_firme = []
        
        for doc in documenti_obbligatori:
            if not doc.firme:
                firme_mancanti += 1
                documenti_senza_firme.append(doc)
        
        # Documenti critici (non approvati)
        documenti_critici = Document.query.filter(
            ~Document.validazione_admin | ~Document.validazione_ceo
        ).count()
        
        # Trend settimanale
        una_settimana_fa = datetime.utcnow() - timedelta(days=7)
        documenti_ultima_settimana = Document.query.filter(
            Document.created_at >= una_settimana_fa
        ).count()
        
        # Download negati
        download_negati = AuditLog.query.filter_by(
            azione='download_negato'
        ).filter(
            AuditLog.timestamp >= una_settimana_fa
        ).count()
        
        # Documenti scaduti o in scadenza
        oggi = datetime.utcnow().date()
        documenti_scaduti = Document.query.filter(
            Document.expiry_date < oggi
        ).count()
        
        documenti_in_scadenza = Document.query.filter(
            Document.expiry_date >= oggi,
            Document.expiry_date <= (oggi + timedelta(days=30))
        ).count()
        
        # Statistiche per modulo
        moduli_stats = {
            'qms': documenti_qms,
            'service': documenti_service,
            'elevate': documenti_elevate,
            'acquisti': Document.query.filter_by(collegato_a_modulo="acquisti").count()
        }
        
        # Alert AI
        alert_ai = []
        
        if firme_mancanti > 0:
            alert_ai.append(f"🧠 Attenzione: ci sono {firme_mancanti} documenti obbligatori senza firme")
        
        if documenti_critici > 0:
            alert_ai.append(f"🧠 Attenzione: ci sono {documenti_critici} documenti critici non ancora approvati")
        
        if documenti_scaduti > 0:
            alert_ai.append(f"🧠 Attenzione: ci sono {documenti_scaduti} documenti scaduti")
        
        if documenti_in_scadenza > 0:
            alert_ai.append(f"🧠 Attenzione: ci sono {documenti_in_scadenza} documenti in scadenza nei prossimi 30 giorni")
        
        # Documenti recenti per trend
        documenti_recenti = Document.query.filter(
            Document.created_at >= una_settimana_fa
        ).order_by(Document.created_at.desc()).limit(10).all()
        
        return render_template("ceo/dashboard_docs_ceo.html",
                             documenti_totali=documenti_totali,
                             documenti_danni=documenti_danni,
                             documenti_policy=documenti_policy,
                             documenti_qms=documenti_qms,
                             firme_mancanti=firme_mancanti,
                             documenti_critici=documenti_critici,
                             documenti_ultima_settimana=documenti_ultima_settimana,
                             download_negati=download_negati,
                             documenti_scaduti=documenti_scaduti,
                             documenti_in_scadenza=documenti_in_scadenza,
                             moduli_stats=moduli_stats,
                             alert_ai=alert_ai,
                             documenti_senza_firme=documenti_senza_firme,
                             documenti_recenti=documenti_recenti)
                             
    except Exception as e:
        current_app.logger.error(f"Errore dashboard CEO docs: {e}")
        return render_template("ceo/dashboard_docs_ceo.html", error=str(e))


@ceo_bp.route("/ceo/docs/export")
@login_required
@ceo_required
def export_dashboard_ceo():
    """
    Esporta i dati della dashboard CEO in formato CSV.
    
    Returns:
        File CSV con i dati della dashboard
    """
    try:
        from io import StringIO
        import csv
        from flask import make_response
        
        # Raccogli dati
        documenti_totali = Document.query.count()
        documenti_danni = Document.query.filter_by(tag="Danno").count()
        documenti_critici = Document.query.filter(
            ~Document.validazione_admin | ~Document.validazione_ceo
        ).count()
        
        # Crea CSV
        si = StringIO()
        writer = csv.writer(si)
        writer.writerow([
            "Metrica", "Valore", "Data Report"
        ])
        
        writer.writerow([
            "Documenti Totali", documenti_totali, datetime.utcnow().strftime('%d/%m/%Y')
        ])
        writer.writerow([
            "Documenti Danni", documenti_danni, datetime.utcnow().strftime('%d/%m/%Y')
        ])
        writer.writerow([
            "Documenti Critici", documenti_critici, datetime.utcnow().strftime('%d/%m/%Y')
        ])
        
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=dashboard_ceo_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        output.headers["Content-type"] = "text/csv"
        return output
        
    except Exception as e:
        current_app.logger.error(f"Errore export dashboard CEO: {e}")
        return jsonify({"error": str(e)}), 500 

# === VALIDAZIONE GERARCHICA FIRME CEO ===
@ceo_bp.route("/documenti/<int:doc_id>/firma-ceo/<int:firma_id>", methods=["POST"])
@login_required
@ceo_required
def approva_firma_ceo(doc_id, firma_id):
    """
    Approva una firma da parte del CEO (approvazione finale).
    
    Args:
        doc_id (int): ID del documento
        firma_id (int): ID della firma da approvare
        
    Returns:
        Redirect alla pagina del documento
    """
    try:
        firma = FirmaDocumento.query.get_or_404(firma_id)
        
        # Verifica che la firma appartenga al documento
        if firma.document_id != doc_id:
            flash("❌ Firma non valida per questo documento.", "danger")
            return redirect(url_for("ceo.dashboard_docs_ceo"))
        
        # Verifica che la firma sia già stata approvata dall'admin
        if not firma.firma_admin:
            flash("⚠️ La firma deve essere prima approvata dall'amministratore.", "warning")
            return redirect(url_for("ceo.dashboard_docs_ceo"))
        
        # Verifica che la firma non sia già stata approvata dal CEO
        if firma.approvato_dal_ceo:
            flash("⚠️ Firma già approvata dal CEO.", "warning")
            return redirect(url_for("ceo.dashboard_docs_ceo"))
        
        # Approva la firma
        firma.approvato_dal_ceo = True
        firma.data_firma_ceo = datetime.utcnow()
        
        # Log dell'azione
        from routes.admin_routes import log_admin_action
        log_admin_action(
            f"Approvazione finale CEO: documento {doc_id}, utente {firma.user.email}",
            current_user.email,
            f"Firma ID: {firma_id}"
        )
        
        # === INVIO AUTOMATICO DOPO APPROVAZIONE CEO ===
        if not firma.inviato_auto:
            try:
                # Ottieni il documento
                documento = firma.document
                
                # Invia email automatica
                if invia_email_documento_firmato(firma, documento):
                    # Aggiorna i campi di invio
                    firma.inviato_auto = True
                    firma.data_invio_auto = datetime.utcnow()
                    firma.email_inviata_a = firma.user.email if firma.user else "N/A"
                    firma.errore_invio = None
                    
                    current_app.logger.info(f"Invio automatico completato per documento {doc_id}")
                    flash("✅ Approvazione finale effettuata dal CEO - Email inviata automaticamente", "success")
                else:
                    # Errore nell'invio
                    firma.errore_invio = "Errore nell'invio dell'email automatica"
                    current_app.logger.error(f"Errore invio automatico per documento {doc_id}")
                    flash("✅ Approvazione finale effettuata dal CEO - Errore nell'invio email", "warning")
                    
            except Exception as e:
                # Errore nella generazione PDF o invio
                firma.errore_invio = f"Errore: {str(e)}"
                current_app.logger.error(f"Errore invio automatico documento {doc_id}: {e}")
                flash("✅ Approvazione finale effettuata dal CEO - Errore nell'invio automatico", "warning")
        else:
            flash("✅ Approvazione finale effettuata dal CEO", "success")
        
        # === UPLOAD AUTOMATICO SU GOOGLE DRIVE ===
        try:
            from routes.drive_upload import trigger_drive_upload
            
            # Trigger upload automatico su Drive
            if trigger_drive_upload(doc_id):
                current_app.logger.info(f"Upload automatico su Google Drive completato per documento {doc_id}")
                flash("✅ Documento caricato automaticamente su Google Drive", "success")
                
                # === BONUS AI: SUGGERIMENTI CORRELATI ===
                from utils.ai_utils import suggerisci_documenti_da_caricare
                suggeriti_correlati = suggerisci_documenti_da_caricare()
                
                if suggeriti_correlati:
                    flash(f"🧠 AI: Ci sono {len(suggeriti_correlati)} altri documenti da caricare su Drive", "info")
            else:
                current_app.logger.warning(f"Errore upload automatico su Google Drive per documento {doc_id}")
                flash("⚠️ Errore durante l'upload automatico su Google Drive", "warning")
                
        except Exception as e:
            current_app.logger.error(f"Errore upload automatico Drive documento {doc_id}: {e}")
            flash("⚠️ Errore durante l'upload automatico su Google Drive", "warning")
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore approvazione firma CEO: {e}")
        flash("❌ Errore durante l'approvazione finale.", "danger")
    
    return redirect(url_for("ceo.dashboard_docs_ceo"))

@ceo_bp.route("/documenti/<int:doc_id>/firma-ceo/<int:firma_id>/rifiuta", methods=["POST"])
@login_required
@ceo_required
def rifiuta_firma_ceo(doc_id, firma_id):
    """
    Rifiuta una firma da parte del CEO.
    
    Args:
        doc_id (int): ID del documento
        firma_id (int): ID della firma da rifiutare
        
    Returns:
        Redirect alla pagina del documento
    """
    try:
        firma = FirmaDocumento.query.get_or_404(firma_id)
        
        # Verifica che la firma appartenga al documento
        if firma.document_id != doc_id:
            flash("❌ Firma non valida per questo documento.", "danger")
            return redirect(url_for("ceo.dashboard_docs_ceo"))
        
        # Rimuovi l'approvazione CEO se presente
        firma.approvato_dal_ceo = False
        firma.data_firma_ceo = None
        
        # Log dell'azione
        from routes.admin_routes import log_admin_action
        log_admin_action(
            f"Rifiuto firma CEO: documento {doc_id}, utente {firma.user.email}",
            current_user.email,
            f"Firma ID: {firma_id}"
        )
        
        db.session.commit()
        flash("⚠️ Firma rifiutata dal CEO", "warning")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore rifiuto firma CEO: {e}")
        flash("❌ Errore durante il rifiuto della firma.", "danger")
    
    return redirect(url_for("ceo.dashboard_docs_ceo")) 

@ceo_bp.route("/documenti/<int:doc_id>/firma-ceo/<int:firma_id>/reinvia-email", methods=["POST"])
@login_required
@ceo_required
def reinvia_email_documento(doc_id, firma_id):
    """
    Reinvia manualmente l'email del documento firmato.
    
    Args:
        doc_id (int): ID del documento
        firma_id (int): ID della firma
        
    Returns:
        Redirect alla pagina del documento
    """
    try:
        firma = FirmaDocumento.query.get_or_404(firma_id)
        
        # Verifica che la firma appartenga al documento
        if firma.document_id != doc_id:
            flash("❌ Firma non valida per questo documento.", "danger")
            return redirect(url_for("ceo.dashboard_docs_ceo"))
        
        # Verifica che la firma sia stata approvata dal CEO
        if not firma.approvato_dal_ceo:
            flash("⚠️ La firma deve essere prima approvata dal CEO.", "warning")
            return redirect(url_for("ceo.dashboard_docs_ceo"))
        
        # Reinvia email
        documento = firma.document
        if invia_email_documento_firmato(firma, documento):
            # Aggiorna i campi di invio
            firma.inviato_auto = True
            firma.data_invio_auto = datetime.utcnow()
            firma.email_inviata_a = firma.user.email if firma.user else "N/A"
            firma.errore_invio = None
            
            # Log dell'azione
            from routes.admin_routes import log_admin_action
            log_admin_action(
                f"Reinvio email documento: documento {doc_id}, utente {firma.user.email}",
                current_user.email,
                f"Firma ID: {firma_id}"
            )
            
            db.session.commit()
            flash("✅ Email reinviata con successo", "success")
        else:
            # Errore nell'invio
            firma.errore_invio = "Errore nel reinvio dell'email"
            db.session.commit()
            flash("❌ Errore nel reinvio dell'email", "danger")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore reinvio email documento {doc_id}: {e}")
        flash("❌ Errore durante il reinvio dell'email.", "danger")
    
    return redirect(url_for("ceo.dashboard_docs_ceo"))

# === FUNZIONI UTILITY PER INVIO AUTOMATICO ===
def genera_pdf_documento(documento_id):
    """
    Genera un PDF del documento firmato.
    
    Args:
        documento_id (int): ID del documento
        
    Returns:
        BytesIO: Contenuto del PDF
    """
    try:
        documento = Document.query.get_or_404(documento_id)
        
        # Crea il contenuto HTML per il PDF
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{documento.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .document-info {{ margin-bottom: 20px; }}
                .firma-info {{ margin-top: 30px; border-top: 1px solid #ccc; padding-top: 20px; }}
                .stamp {{ position: absolute; top: 50px; right: 50px; color: green; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="stamp">✅ APPROVATO</div>
            <div class="header">
                <h1>{documento.title}</h1>
                <p>Documento firmato e approvato</p>
            </div>
            
            <div class="document-info">
                <h3>Informazioni Documento</h3>
                <p><strong>Titolo:</strong> {documento.title}</p>
                <p><strong>Descrizione:</strong> {documento.description or 'Nessuna descrizione'}</p>
                <p><strong>Uploader:</strong> {documento.uploader_email}</p>
                <p><strong>Data creazione:</strong> {documento.created_at.strftime('%d/%m/%Y %H:%M')}</p>
                <p><strong>Azienda:</strong> {documento.company.name if documento.company else 'N/A'}</p>
                <p><strong>Reparto:</strong> {documento.department.name if documento.department else 'N/A'}</p>
            </div>
            
            <div class="firma-info">
                <h3>Firme e Approvazioni</h3>
        """
        
        # Aggiungi informazioni sulle firme
        if documento.firme:
            for firma in documento.firme:
                html_content += f"""
                <div style="margin-bottom: 15px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                    <p><strong>Utente:</strong> {firma.user.full_name if firma.user else 'N/A'}</p>
                    <p><strong>Firma:</strong> {firma.nome_firma}</p>
                    <p><strong>Data firma:</strong> {firma.data_firma.strftime('%d/%m/%Y %H:%M')}</p>
                    <p><strong>Stato:</strong> {firma.stato_firma_display}</p>
                    {f'<p><strong>Approvato Admin:</strong> {firma.data_firma_admin.strftime("%d/%m/%Y %H:%M") if firma.data_firma_admin else "Non approvato"}</p>' if firma.firma_admin else ''}
                    {f'<p><strong>Approvato CEO:</strong> {firma.data_firma_ceo.strftime("%d/%m/%Y %H:%M") if firma.data_firma_ceo else "Non approvato"}</p>' if firma.approvato_dal_ceo else ''}
                </div>
                """
        
        html_content += """
            </div>
            
            <div style="margin-top: 40px; text-align: center; color: #666;">
                <p>Documento generato automaticamente dal sistema di gestione documenti</p>
                <p>Data generazione: """ + datetime.utcnow().strftime('%d/%m/%Y %H:%M') + """</p>
            </div>
        </body>
        </html>
        """
        
        # Genera PDF usando weasyprint
        from weasyprint import HTML
        from io import BytesIO
        
        pdf = HTML(string=html_content).write_pdf()
        return BytesIO(pdf)
        
    except Exception as e:
        current_app.logger.error(f"Errore generazione PDF documento {documento_id}: {e}")
        raise

def invia_email_documento_firmato(firma, documento):
    """
    Invia email con il documento firmato in allegato.
    
    Args:
        firma (FirmaDocumento): La firma approvata
        documento (Document): Il documento firmato
        
    Returns:
        bool: True se l'invio è riuscito, False altrimenti
    """
    try:
        from flask_mail import Message
        from extensions import mail
        from models import LogInvioDocumento
        
        # Genera PDF
        pdf_content = genera_pdf_documento(documento.id)
        pdf_content.seek(0)
        
        # Prepara destinatari
        destinatari = [firma.user.email] if firma.user and firma.user.email else []
        
        # Aggiungi email di backup se configurata
        backup_email = current_app.config.get('MAIL_BACKUP_EMAIL')
        if backup_email and backup_email not in destinatari:
            destinatari.append(backup_email)
        
        if not destinatari:
            current_app.logger.warning(f"Nessun destinatario trovato per documento {documento.id}")
            return False
        
        # Prepara email
        subject = f"📄 Documento firmato e approvato: {documento.title}"
        
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #2c3e50;">✅ Documento Approvato</h2>
            
            <p>Gentile {firma.user.full_name if firma.user else 'Utente'},</p>
            
            <p>Il documento <strong>"{documento.title}"</strong> è stato firmato e approvato con successo.</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">📋 Dettagli Documento</h3>
                <p><strong>Titolo:</strong> {documento.title}</p>
                <p><strong>Descrizione:</strong> {documento.description or 'Nessuna descrizione'}</p>
                <p><strong>Data creazione:</strong> {documento.created_at.strftime('%d/%m/%Y %H:%M')}</p>
                <p><strong>Stato firma:</strong> {firma.stato_firma_display}</p>
                <p><strong>Data approvazione CEO:</strong> {firma.data_firma_ceo.strftime('%d/%m/%Y %H:%M')}</p>
            </div>
            
            <p>In allegato trovi il PDF del documento firmato e approvato.</p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666;">
                <p><small>Questo messaggio è stato generato automaticamente dal sistema di gestione documenti.</small></p>
            </div>
        </div>
        """
        
        # Crea messaggio
        msg = Message(
            subject=subject,
            recipients=destinatari,
            html=html_body
        )
        
        # Allega PDF
        msg.attach(
            filename=f"documento_firmato_{documento.id}.pdf",
            content_type="application/pdf",
            data=pdf_content.getvalue()
        )
        
        # Invia email
        mail.send(msg)
        
        # === LOGGING AUTOMATICO SUCCESSO ===
        try:
            # Log per ogni destinatario
            for destinatario in destinatari:
                log = LogInvioDocumento(
                    firma_id=firma.id,
                    documento_id=documento.id,
                    email_destinatario=destinatario,
                    stato="success",
                    errore=None
                )
                db.session.add(log)
            
            db.session.commit()
            
            # Log file aggiuntivo
            current_app.logger.info(f"[EMAIL INVIATA] → {', '.join(destinatari)} per documento {documento.title}")
            
        except Exception as log_error:
            current_app.logger.error(f"Errore nel logging invio email: {log_error}")
            db.session.rollback()
        
        current_app.logger.info(f"Email inviata con successo per documento {documento.id} a {destinatari}")
        return True
        
    except Exception as e:
        # === LOGGING AUTOMATICO ERRORE ===
        try:
            log = LogInvioDocumento(
                firma_id=firma.id,
                documento_id=documento.id,
                email_destinatario=firma.user.email if firma.user else "N/A",
                stato="errore",
                errore=str(e)
            )
            db.session.add(log)
            db.session.commit()
            
            # Log file aggiuntivo
            current_app.logger.error(f"[EMAIL ERRORE] → {firma.user.email} per documento {documento.title}: {str(e)}")
            
        except Exception as log_error:
            current_app.logger.error(f"Errore nel logging errore email: {log_error}")
            db.session.rollback()
        
        current_app.logger.error(f"Errore invio email documento {documento.id}: {e}")
        return False 

@ceo_bp.route("/test-logging-invio")
@login_required
@ceo_required
def test_logging_invio():
    """
    Endpoint di test per verificare il logging degli invii.
    """
    try:
        from models import LogInvioDocumento, FirmaDocumento, Document
        
        # Conta i log esistenti
        total_logs = LogInvioDocumento.query.count()
        success_logs = LogInvioDocumento.query.filter_by(stato="success").count()
        error_logs = LogInvioDocumento.query.filter_by(stato="errore").count()
        
        # Ultimi 5 log
        ultimi_logs = LogInvioDocumento.query.order_by(LogInvioDocumento.data_invio.desc()).limit(5).all()
        
        # Statistiche per destinatario
        from sqlalchemy import func
        stats_destinatari = db.session.query(
            LogInvioDocumento.email_destinatario,
            func.count(LogInvioDocumento.id).label('count')
        ).group_by(LogInvioDocumento.email_destinatario).all()
        
        return {
            "status": "success",
            "message": "Test logging invio completato",
            "stats": {
                "total_logs": total_logs,
                "success_logs": success_logs,
                "error_logs": error_logs
            },
            "ultimi_logs": [
                {
                    "id": log.id,
                    "email": log.email_destinatario,
                    "stato": log.stato,
                    "data": log.data_invio_formatted,
                    "errore": log.errore
                } for log in ultimi_logs
            ],
            "stats_destinatari": [
                {
                    "email": stat.email_destinatario,
                    "count": stat.count
                } for stat in stats_destinatari
            ]
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Errore nel test logging: {str(e)}"
        }, 500 

@ceo_bp.route("/dashboard/drive_ai")
@login_required
@ceo_required
def dashboard_drive_ai():
    """
    Dashboard AI per gestione Google Drive.
    
    Returns:
        str: Template della dashboard AI
    """
    try:
        from utils.ai_utils import suggerisci_documenti_da_caricare, analizza_stato_drive_ai
        
        # Ottieni suggerimenti AI
        suggeriti = suggerisci_documenti_da_caricare()
        
        # Analisi stato generale
        analisi = analizza_stato_drive_ai()
        
        return render_template(
            "dashboard_drive_ai.html",
            suggeriti=suggeriti,
            analisi=analisi
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore dashboard Drive AI: {str(e)}")
        flash("❌ Errore nel caricamento della dashboard AI", "danger")
        return redirect(url_for("ceo.dashboard_docs_ceo")) 

@ceo_bp.route("/dashboard/revisione_ai")
@login_required
@ceo_required
def dashboard_revisione_ai():
    """
    Dashboard AI per revisione documenti obsoleti.
    
    Returns:
        str: Template della dashboard di revisione AI
    """
    try:
        from utils.ai_utils import analizza_documenti_obsoleti, analizza_statistiche_revisione
        
        # Ottieni suggerimenti AI
        suggerimenti = analizza_documenti_obsoleti()
        
        # Analisi statistiche
        statistiche = analizza_statistiche_revisione()
        
        return render_template(
            "dashboard_revisione_ai.html",
            suggerimenti=suggerimenti,
            statistiche=statistiche
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore dashboard revisione AI: {str(e)}")
        flash("❌ Errore nel caricamento della dashboard di revisione", "danger")
        return redirect(url_for("ceo.dashboard_docs_ceo")) 

@ceo_bp.route("/documenti/letture")
@login_required
@ceo_required
def documenti_letture():
    """
    Dashboard per visualizzare le letture dei documenti.
    
    Returns:
        template: Template della dashboard letture
    """
    try:
        from utils.read_tracker import get_document_read_stats
        
        # Ottieni tutti i documenti con statistiche
        documents = Document.query.all()
        docs_with_stats = []
        
        for doc in documents:
            stats = get_document_read_stats(doc)
            docs_with_stats.append({
                'document': doc,
                'stats': stats
            })
        
        # Ordina per numero di letture decrescente
        docs_with_stats.sort(key=lambda x: x['stats']['total_reads'], reverse=True)
        
        return render_template("ceo/document_letture.html", docs=docs_with_stats)
        
    except Exception as e:
        flash(f"❌ Errore nel caricamento dashboard letture: {str(e)}", "danger")
        return redirect(url_for("ceo.dashboard")) 