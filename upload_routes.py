from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app
from flask_login import login_required, current_user
from datetime import datetime
from flask import current_app
from extensions import db, bcrypt
from models import Document, Company, Department
from utils_extra import save_file_and_upload_to_drive, allowed_file, notify_upload  # assicurati che siano in utils_extra.py
from services.antivirus_service import antivirus_service
import os
import tempfile

upload_bp = Blueprint('upload', __name__, url_prefix='/upload')

@upload_bp.route('/')
def upload_home():
    return redirect(url_for('upload.upload_to_drive'))

@upload_bp.route('/upload_to_drive', methods=['GET', 'POST'])
@login_required
def upload_to_drive():
    if request.method == 'POST':
        file = request.files.get('file')
        title = request.form.get('title')
        description = request.form.get('description')
        note = request.form.get('note')
        visibility = request.form.get('visibility')
        password = request.form.get('password') if visibility == 'protetto' else None
        shared_email = request.form.get('shared_email') if visibility == 'condividi' else None

        company_ids = request.form.getlist('target_companies')
        department_ids = request.form.getlist('target_departments')

        # 🔒 Validazione
        if not file or not title:
            flash("⚠️ File e titolo sono obbligatori", "danger")
            return redirect(url_for('upload.upload_to_drive'))

        if not company_ids or not department_ids:
            flash("⚠️ Seleziona almeno un'azienda e un reparto", "danger")
            return redirect(url_for('upload.upload_to_drive'))

        if not allowed_file(file.filename):
            flash("❌ Estensione file non valida", "danger")
            return redirect(url_for('upload.upload_to_drive'))

        # 🛡️ Prima verifica antivirus del file caricato
        try:
            # Salva temporaneamente il file per la scansione
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                file.seek(0)  # Reset position
                temp_file.write(file.read())
                temp_file_path = temp_file.name
                file.seek(0)  # Reset per uso successivo
            
            # Scansiona il file con ClamAV
            scan_result = antivirus_service.scan_file_path(temp_file_path)
            
            # Rimuovi file temporaneo
            try:
                os.unlink(temp_file_path)
            except:
                pass
            
            # Controlla risultato scansione
            if scan_result['verdict'] == 'infected':
                flash(f"🦠 File infetto rilevato: {scan_result['details']}", "danger")
                return redirect(url_for('upload.upload_to_drive'))
            
            elif scan_result['verdict'] == 'error':
                strict_mode = os.getenv('STRICT_UPLOAD_SECURITY', 'False').lower() == 'true'
                if strict_mode:
                    flash(f"⚠️ Errore scansione antivirus: {scan_result['details']}", "danger")
                    return redirect(url_for('upload.upload_to_drive'))
                else:
                    flash(f"⚠️ Scansione antivirus fallita, ma upload consentito: {scan_result['details']}", "warning")
            
        except Exception as e:
            current_app.logger.error(f"Errore scansione antivirus: {e}")
            strict_mode = os.getenv('STRICT_UPLOAD_SECURITY', 'False').lower() == 'true'
            if strict_mode:
                flash("❌ Errore durante la scansione antivirus. Upload bloccato.", "danger")
                return redirect(url_for('upload.upload_to_drive'))
            else:
                flash("⚠️ Errore scansione antivirus, ma upload consentito.", "warning")

        # 🔄 Salvataggio multiplo per combinazioni azienda/reparto
        saved_documents = []
        try:
            for company_id in company_ids:
                company = Company.query.get(company_id)
                if not company:
                    continue

                for department_id in department_ids:
                    department = Department.query.get(department_id)
                    if not department:
                        continue

                    # 📁 Salva il file con struttura personalizzata
                    local_path, _ = save_file_and_upload_to_drive(
                        file, upload_to_drive=False
                    )
                    new_filename = os.path.basename(local_path)
                    drive_file_id = None

                    doc = Document(
                        title=title,
                        description=description,
                        note=note,
                        filename=new_filename,
                        original_filename=file.filename,
                        uploader_email=current_user.email,
                        user_id=current_user.id,
                        company_id=company.id,
                        department_id=department.id,
                        visibility=visibility,
                        shared_email=shared_email,
                        password=bcrypt.generate_password_hash(password).decode('utf-8') if password else None,
                        drive_file_id=drive_file_id,
                        created_at=datetime.utcnow()
                    )

                    db.session.add(doc)
                    db.session.flush()  # Ottieni l'ID del documento
                    
                    saved_documents.append((doc.id, local_path))
                    notify_upload(doc)  # opzionale

            db.session.commit()
            
            # 🛡️ Post-commit: calcola hash e salva risultati scansione per ogni documento
            for doc_id, file_path in saved_documents:
                try:
                    # Processa file: calcola hash SHA-256 e salva risultato antivirus
                    is_safe, detailed_scan = antivirus_service.process_uploaded_file(file_path, doc_id)
                    
                    if not is_safe:
                        current_app.logger.warning(f"Documento {doc_id} marcato come non sicuro dopo elaborazione")
                    
                except Exception as e:
                    current_app.logger.error(f"Errore post-processing documento {doc_id}: {e}")
            
            flash("✅ Documento caricato con successo per tutte le combinazioni", "success")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore salvataggio documento: {e}")
            flash("❌ Errore durante il salvataggio del documento.", "danger")

        return redirect(url_for('user.my_documents'))

    # GET → mostra form
    companies = Company.query.all()
    departments = Department.query.all()
    return render_template("upload.html", all_companies=companies, all_departments=departments)
