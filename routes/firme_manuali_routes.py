from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from models import db, FirmaManuale, Document
from decorators import roles_required
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Blueprint per firme manuali
firme_manuali_bp = Blueprint('firme_manuali', __name__)

@firme_manuali_bp.route('/firma_manuale/upload', methods=['GET', 'POST'])
@login_required
@roles_required(['admin', 'hr', 'quality_manager'])
def upload_firma_manuale():
    """
    Upload firma manuale scansionata con accettazione privacy.
    """
    if request.method == 'POST':
        try:
            # Recupera dati dal form
            documento_id = request.form.get('documento_id')
            firmato_da = request.form.get('firmato_da')
            ruolo = request.form.get('ruolo')
            data_firma = request.form.get('data_firma')
            note = request.form.get('note')
            privacy = request.form.get('privacy_accettata')
            file = request.files.get('file_scan')

            # Validazione privacy
            if not privacy:
                flash("⚠️ Devi accettare l'informativa privacy per procedere.", "danger")
                return redirect(request.url)

            # Validazione dati obbligatori
            if not all([documento_id, firmato_da, data_firma, file]):
                flash("❌ Tutti i campi obbligatori devono essere compilati.", "danger")
                return redirect(request.url)

            # Validazione file
            if file.filename == '':
                flash("❌ Seleziona un file da caricare.", "danger")
                return redirect(request.url)

            # Controlla estensione file
            allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
            if not file.filename.lower().endswith(tuple('.' + ext for ext in allowed_extensions)):
                flash("❌ Formato file non supportato. Usa PDF, JPG, JPEG o PNG.", "danger")
                return redirect(request.url)

            # Salva file
            filename = None
            if file:
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                safe_filename = secure_filename(file.filename)
                filename = f"{timestamp}_{safe_filename}"
                
                # Assicurati che la cartella esista
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'firme_manuali')
                os.makedirs(upload_folder, exist_ok=True)
                
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                logger.info(f"File salvato: {file_path}")

            # Crea record firma manuale
            firma = FirmaManuale(
                documento_id=documento_id,
                firmato_da=firmato_da,
                ruolo=ruolo,
                data_firma=datetime.strptime(data_firma, "%Y-%m-%d").date(),
                note=note,
                file_scan=filename,
                created_by=current_user.id
            )
            
            db.session.add(firma)
            db.session.commit()
            
            flash("✅ Firma manuale registrata correttamente.", "success")
            logger.info(f"Firma manuale registrata: {firma.id} per documento {documento_id}")
            
            return redirect(url_for('admin.view_document', documento_id=documento_id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore registrazione firma manuale: {str(e)}")
            flash(f"❌ Errore durante la registrazione: {str(e)}", "danger")
            return redirect(request.url)

    # GET - Mostra form
    try:
        documenti = Document.query.order_by(Document.nome.asc()).all()
        return render_template("upload_firma_manuale.html", documenti=documenti)
    except Exception as e:
        logger.error(f"Errore caricamento form firma manuale: {str(e)}")
        flash("❌ Errore nel caricamento del form.", "danger")
        return redirect(url_for('admin.dashboard'))

@firme_manuali_bp.route('/firma_manuale/<int:firma_id>/delete', methods=['POST'])
@login_required
@roles_required(['admin'])
def delete_firma_manuale(firma_id):
    """
    Elimina una firma manuale (solo Admin).
    """
    try:
        firma = FirmaManuale.query.get_or_404(firma_id)
        documento_id = firma.documento_id
        
        # Elimina file se presente
        if firma.file_scan:
            file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'firme_manuali', firma.file_scan)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File eliminato: {file_path}")
        
        db.session.delete(firma)
        db.session.commit()
        
        flash("✅ Firma manuale eliminata correttamente.", "success")
        logger.info(f"Firma manuale eliminata: {firma_id}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore eliminazione firma manuale: {str(e)}")
        flash(f"❌ Errore durante l'eliminazione: {str(e)}", "danger")
    
    return redirect(url_for('admin.view_document', documento_id=documento_id))

@firme_manuali_bp.route('/firma_manuale/<int:firma_id>/download', methods=['GET'])
@login_required
@roles_required(['admin', 'hr', 'quality_manager', 'auditor'])
def download_firma_manuale(firma_id):
    """
    Download del file scan della firma manuale.
    """
    try:
        from flask import send_file
        
        firma = FirmaManuale.query.get_or_404(firma_id)
        
        if not firma.file_scan:
            flash("❌ Nessun file associato a questa firma.", "danger")
            return redirect(url_for('admin.view_document', documento_id=firma.documento_id))
        
        file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'firme_manuali', firma.file_scan)
        
        if not os.path.exists(file_path):
            flash("❌ File non trovato.", "danger")
            return redirect(url_for('admin.view_document', documento_id=firma.documento_id))
        
        return send_file(file_path, as_attachment=True, download_name=f"firma_manuale_{firma.firmato_da}_{firma.data_firma_display}.pdf")
        
    except Exception as e:
        logger.error(f"Errore download firma manuale: {str(e)}")
        flash(f"❌ Errore durante il download: {str(e)}", "danger")
        return redirect(url_for('admin.view_document', documento_id=firma.documento_id))

@firme_manuali_bp.route('/documento/<int:documento_id>/firme/export/pdf', methods=['GET'])
@login_required
@roles_required(['admin', 'hr', 'quality_manager'])
def export_firme_pdf(documento_id):
    """
    Esporta registro PDF delle firme manuali per un documento.
    """
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from datetime import datetime
        
        doc = Document.query.get_or_404(documento_id)
        firme = doc.firme_manuali.order_by(FirmaManuale.data_firma).all()
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 50
        
        # Header con logo aziendale (se disponibile)
        try:
            logo_path = os.path.join(current_app.root_path, 'static', 'img', 'logo_mercury.png')
            if os.path.exists(logo_path):
                c.drawImage(ImageReader(logo_path), 50, height - 80, width=80, preserveAspectRatio=True, mask='auto')
                y = height - 100
        except:
            pass
        
        # Titolo documento
        c.setFont("Helvetica-Bold", 16)
        c.drawString(140, y, f"Registro Firme Manuali")
        y -= 25
        c.setFont("Helvetica", 12)
        c.drawString(140, y, f"Documento: {doc.title}")
        y -= 30
        
        # Informazioni documento
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"📄 ID Documento: {doc.id}")
        y -= 15
        c.drawString(50, y, f"📅 Creato il: {doc.created_at.strftime('%d/%m/%Y %H:%M')}")
        y -= 15
        c.drawString(50, y, f"👤 Uploader: {doc.uploader_email}")
        y -= 30
        
        # Statistiche firme
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, f"📊 Statistiche Firme:")
        y -= 15
        c.setFont("Helvetica", 10)
        c.drawString(60, y, f"• Totale firme registrate: {len(firme)}")
        y -= 15
        c.drawString(60, y, f"• Con file scan: {len([f for f in firme if f.file_scan])}")
        y -= 15
        c.drawString(60, y, f"• Firme recenti (≤30 giorni): {len([f for f in firme if f.is_recente])}")
        y -= 30
        
        # Elenco firme
        if firme:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, f"✍️ Elenco Firme Registrate:")
            y -= 20
            
            for i, firma in enumerate(firme, 1):
                if y < 100:  # Nuova pagina se necessario
                    c.showPage()
                    y = height - 50
                    c.setFont("Helvetica", 10)
                
                # Intestazione firma
                c.setFont("Helvetica-Bold", 11)
                c.drawString(50, y, f"👤 Firma #{i}: {firma.firmato_da}")
                y -= 15
                
                c.setFont("Helvetica", 10)
                c.drawString(60, y, f"🏢 Ruolo: {firma.ruolo or 'Non specificato'}")
                y -= 15
                c.drawString(60, y, f"📅 Data Firma: {firma.data_firma_display}")
                y -= 15
                c.drawString(60, y, f"📝 Registrato il: {firma.created_at.strftime('%d/%m/%Y %H:%M')}")
                y -= 15
                
                if firma.note:
                    c.drawString(60, y, f"📋 Note: {firma.note}")
                    y -= 15
                
                if firma.file_scan:
                    c.drawString(60, y, f"📎 File Scan: {firma.file_scan}")
                    y -= 15
                
                # Badge recente se applicabile
                if firma.is_recente:
                    c.setFont("Helvetica-Bold", 9)
                    c.drawString(60, y, f"🆕 FIRMA RECENTE (≤30 giorni)")
                    y -= 15
                    c.setFont("Helvetica", 10)
                
                y -= 10  # Spazio tra firme
        else:
            c.setFont("Helvetica", 11)
            c.drawString(50, y, f"⚠️ Nessuna firma manuale registrata per questo documento.")
            y -= 20
        
        # Footer con firma digitale
        y = 80
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(50, y, f"📄 Documento generato da SYNTHIA DOCS")
        y -= 15
        c.drawString(50, y, f"🔐 Firma digitale: SYNTHIA-AUDIT-FIRME-{documento_id}-{datetime.utcnow().timestamp():.0f}")
        y -= 15
        c.drawString(50, y, f"🌐 Verifica autenticità: docs.mercurysurgelati.org")
        y -= 15
        c.drawString(50, y, f"📅 Generato il: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}")
        
        c.save()
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            download_name=f"registro_firme_{doc.title.replace(' ', '_')}.pdf",
            as_attachment=True
        )
        
    except Exception as e:
        logger.error(f"Errore export PDF firme manuali: {str(e)}")
        flash(f"❌ Errore durante l'esportazione PDF: {str(e)}", "danger")
        return redirect(url_for('admin.view_document', documento_id=documento_id)) 