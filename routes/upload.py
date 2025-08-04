import os
import qrcode
from datetime import datetime
from flask import Blueprint, request, redirect, url_for, render_template, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from flask_mail import Message

from extensions import db, mail
from models import Document, Company, Department
from forms import UploadForm
import bcrypt

upload_bp = Blueprint('upload', __name__, url_prefix='/upload')

# Estensioni consentite
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp',
    'pages', 'numbers', 'key', 'txt', 'rtf', 'csv',
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'
}

def is_allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/file', methods=['POST'])
@login_required
def upload_file():
    print("[DEBUG] ✅ Funzione upload_file() attivata")
    print("[DEBUG] ➕ FILES:", request.files)
    print("[DEBUG] 📝 FORM:", request.form)

    file = request.files.get('file')
    title = request.form.get('title', '').strip()
    description = request.form.get('description')
    visibility = request.form.get('visibility')
    password = request.form.get('password') or None
    shared_email = request.form.get('shared_email')
    destination = request.form.get('destination')
    target_companies = request.form.getlist('target_companies')
    target_departments = request.form.getlist('target_departments')

    if not file or file.filename == '':
        flash("⚠️ Nessun file selezionato.", "danger")
        return redirect(url_for('upload.upload'))

    if not is_allowed(file.filename):
        flash("🚫 Estensione file non ammessa.", "danger")
        return redirect(url_for('upload.upload'))

    if not visibility or not title:
        flash("⚠️ Tutti i campi obbligatori devono essere compilati.", "danger")
        return redirect(url_for('upload.upload'))

    try:
        for company_id in target_companies:
            for department_id in target_departments:
                # Salva file in modo centralizzato
                local_path, _ = save_file_and_upload(file, upload_to_drive=False)
                new_filename = os.path.basename(local_path)
                filepath = local_path

                doc = Document(
                    title=title,
                    description=description,
                    filename=new_filename,
                    original_filename=file.filename,
                    visibility=visibility,
                    password=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8') if password else None,
                    shared_email=shared_email,
                    uploader_email=current_user.email,
                    user_id=current_user.id,
                    company_id=int(company_id),
                    department_id=int(department_id),
                    created_at=datetime.utcnow()
                )

                db.session.add(doc)
                db.session.flush()

                # === CLASSIFICAZIONE AI DEL DOCUMENTO ===
                try:
                    from services.ai_classifier import classifica_e_processa_documento
                    classifica_e_processa_documento(doc)
                except Exception as e:
                    current_app.logger.error(f"Errore classificazione AI: {e}")
                
                        # === INDICIZZAZIONE PER RICERCA SEMANTICA ===
        try:
            from services.semantic_search import indicizza_documento
            indicizza_documento(doc, file_path)
        except Exception as e:
            current_app.logger.error(f"Errore indicizzazione semantica: {e}")
        
        # === GESTIONE VERSIONI AUTOMATICA ===
        try:
            from utils.version_utils import attiva_nuova_versione
            # Crea la prima versione del documento
            attiva_nuova_versione(doc, filename, file_path, current_user, "Versione iniziale")
        except Exception as e:
            current_app.logger.error(f"Errore creazione versione: {e}")

        generate_qr_for_doc(doc)
        notify_upload(doc)

        db.session.commit()
        flash("✅ Documento caricato con successo", "success")
        return redirect(url_for('my_documents'))

    except Exception as e:
        current_app.logger.error(f"[UPLOAD] Errore: {e}")
        db.session.rollback()
        flash("❌ Errore durante il caricamento. Contatta il supporto tecnico.", "danger")
        return redirect(url_for('upload.upload'))

@upload_bp.route('/', methods=['GET', 'POST'])
@login_required
def upload():
    from app import drive_service  # importa il servizio Drive se serve
    form = UploadForm()
    companies = Company.query.all()
    departments = Department.query.all()

    if request.method == 'POST':
        file = request.files.get('file')
        title = request.form.get('title', '').strip()
        description = request.form.get('description')
        visibility = request.form.get('visibility')
        password = request.form.get('password') or None
        shared_email = request.form.get('shared_email')
        target_companies = request.form.getlist('target_companies')
        target_departments = request.form.getlist('target_departments')
        upload_mode = request.form.get('upload_mode', 'local')  # 'local' o 'gdrive'
        drive_folder_id = request.form.get('drive_folder_id') if upload_mode == 'gdrive' else None

        if not file or file.filename == '':
            flash("⚠️ Nessun file selezionato.", "danger")
            return redirect(url_for('upload.upload'))

        if not is_allowed(file.filename):
            flash("🚫 Estensione file non ammessa.", "danger")
            return redirect(url_for('upload.upload'))

        if not visibility or not title:
            flash("⚠️ Tutti i campi obbligatori devono essere compilati.", "danger")
            return redirect(url_for('upload.upload'))

        try:
            for company_id in target_companies:
                for department_id in target_departments:
                    local_path, drive_file_id = save_file_and_upload(
                        file,
                        upload_to_drive=(upload_mode == 'gdrive'),
                        drive_service=drive_service if upload_mode == 'gdrive' else None,
                        drive_folder_id=drive_folder_id
                    )
                    new_filename = os.path.basename(local_path)
                    filepath = local_path

                    doc = Document(
                        title=title,
                        description=description,
                        filename=new_filename,
                        original_filename=file.filename,
                        visibility=visibility,
                        password=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8') if password else None,
                        shared_email=shared_email,
                        uploader_email=current_user.email,
                        user_id=current_user.id,
                        company_id=int(company_id),
                        department_id=int(department_id),
                        created_at=datetime.utcnow(),
                        drive_file_id=drive_file_id
                    )

                    db.session.add(doc)
                    db.session.flush()

                    generate_qr_for_doc(doc)
                    notify_upload(doc)

            db.session.commit()
            flash("✅ Documento caricato con successo", "success")
            return redirect(url_for('my_documents'))

        except Exception as e:
            current_app.logger.error(f"[UPLOAD] Errore: {e}")
            db.session.rollback()
            flash("❌ Errore durante il caricamento. Contatta il supporto tecnico.", "danger")
            return redirect(url_for('upload.upload'))

    return render_template('upload.html', form=form, companies=companies, departments=departments)

def generate_qr_for_doc(doc):
    try:
        qr_data = f"https://docs.mercurysurgelati.org/view/{doc.id}"
        qr_img = qrcode.make(qr_data)
        qr_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'qr')
        os.makedirs(qr_folder, exist_ok=True)
        qr_path = os.path.join(qr_folder, f"{doc.id}.png")
        qr_img.save(qr_path)
    except Exception as e:
        current_app.logger.error(f"[QR] Errore generazione QR per doc {doc.id}: {e}")

def notify_upload(doc):
    try:
        msg = Message(
            subject=f"📤 Documento caricato: {doc.title}",
            recipients=[doc.uploader_email],
            body=f"Documento caricato da {current_user.username} nel reparto ID {doc.department_id}"
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"[EMAIL] Errore invio notifica: {e}")
