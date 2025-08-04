from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app
from flask_login import login_required, current_user
from datetime import datetime
from flask import current_app
from extensions import db, bcrypt
from models import Document, Company, Department
from utils_extra import save_file_and_upload_to_drive, allowed_file, notify_upload  # assicurati che siano in utils_extra.py
import os

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

        # 🔄 Salvataggio multiplo per combinazioni azienda/reparto
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
                    notify_upload(doc)  # opzionale

            db.session.commit()
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
