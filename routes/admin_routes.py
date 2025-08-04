import traceback
from sqlalchemy import func
from models import GuestActivity, Company, Department, User, Document, AdminLog, AccessRequest, AuthorizedAccess, DocumentActivityLog, DocumentVersion, DocumentReadLog, DownloadDeniedLog, DocumentApprovalLog, ApprovalStep, AIAnalysisLog, FirmaDocumento, LogInvioDocumento
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, Response, send_file, jsonify, abort
from flask_login import login_required, current_user
from extensions import db, bcrypt
from sqlalchemy.exc import IntegrityError
from itsdangerous import URLSafeTimedSerializer
from decorators import admin_required
from flask_mail import Message
from extensions import mail
from flask import render_template
from sqlalchemy.orm import joinedload
import os
import requests
from collections import OrderedDict
import csv
from io import StringIO, BytesIO
from weasyprint import HTML
from collections import defaultdict
from collections import Counter
from flask import make_response
# from flask_login import roles_required  # Non esiste in flask_login


# === Blueprint Admin ===
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# === Dashboard Admin ===
@admin_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('auth.login'))

    # Verifica alert automatici
    alerts = check_download_denied_alerts()
    if alerts:
        send_alert_notifications(alerts)

    # Statistiche di upload e download
    total_uploads = Document.query.count()
    total_downloads = db.session.query(func.count()).select_from(GuestActivity).scalar()

    # Dati settimanali (esempio semplificato)
    labels = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
    uploads = [3, 5, 2, 4, 1, 0, 2]
    downloads = [2, 1, 0, 5, 4, 3, 1]

    # Dati per documenti per tipo
    doc_stats = db.session.query(
        func.lower(func.substr(Document.filename, -3)).label('type'),
        func.count()
    ).group_by('type').all()
    doc_types = [row[0].upper() for row in doc_stats]
    doc_counts = [row[1] for row in doc_stats]

    # === Nuovi dati per grafico a torta ===
    pie_labels = doc_types
    pie_values = doc_counts

    return render_template(
        'admin/dashboard.html',
        total_uploads=total_uploads,
        total_downloads=total_downloads,
        labels=labels,
        uploads=uploads,
        downloads=downloads,
        doc_types=doc_types,
        doc_counts=doc_counts,
        pie_labels=pie_labels,
        pie_values=pie_values,
        alerts=alerts  # Passa gli alert al template
    )

# === Gestione Aziende ===
@admin_bp.route('/company')
@login_required
@admin_required
def company_management():
    companies = Company.query.order_by(Company.name).all()
    return render_template('admin/company_management.html', companies=companies)

@admin_bp.route('/company/create', methods=['POST'])
@login_required
@admin_required
def create_company():
    company_name = request.form.get('company_name', '').strip()
    if not company_name:
        flash("Il nome dell'azienda è obbligatorio.", "danger")
        return redirect(url_for('admin.company_management'))

    existing = Company.query.filter_by(name=company_name).first()
    if existing:
        flash("Esiste già un'azienda con questo nome.", "warning")
        return redirect(url_for('admin.company_management'))

    new_company = Company(name=company_name)
    db.session.add(new_company)
    db.session.commit()
    flash(f"Azienda '{company_name}' creata con successo.", "success")
    return redirect(url_for('admin.company_management'))

@admin_bp.route('/company/<int:company_id>/update', methods=['POST'])
@login_required
@admin_required
def update_company(company_id):
    new_name = request.form.get('company_name', '').strip()
    if not new_name:
        flash("Il nome non può essere vuoto.", "danger")
        return redirect(url_for('admin.company_management'))

    company = Company.query.get_or_404(company_id)
    company.name = new_name
    db.session.commit()

    flash("Azienda aggiornata con successo.", "success")
    return redirect(url_for('admin.company_management'))

@admin_bp.route('/company/<int:company_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)
    try:
        db.session.delete(company)
        db.session.commit()
        flash("Azienda eliminata con successo.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("⚠️ Impossibile eliminare l'azienda: ci sono documenti o utenti associati.", "danger")
    return redirect(url_for('admin.company_management'))

# === Gestione Reparti ===
@admin_bp.route('/departments')
@login_required
@admin_required
def department_management():
    companies = Company.query.options(db.joinedload(Company.departments)).order_by(Company.name).all()
    selected_company_id = request.args.get('company_id', type=int)
    departments = []
    selected_company = None

    if selected_company_id:
        selected_company = Company.query.get(selected_company_id)
        if selected_company:
            departments = Department.query.filter_by(company_id=selected_company_id).order_by(Department.name).all()

    return render_template(
        'admin/department_management.html',
        companies=companies,
        selected_company=selected_company,
        departments=departments
    )

@admin_bp.route('/departments/create', methods=['POST'])
@login_required
@admin_required
def create_department():
    company_id = request.form.get('company_id', type=int)
    department_name = request.form.get('department_name', '').strip()

    if not company_id or not department_name:
        flash("Tutti i campi sono obbligatori.", "danger")
        return redirect(url_for('admin.department_management', company_id=company_id))

    existing = Department.query.filter_by(name=department_name, company_id=company_id).first()
    if existing:
        flash("Esiste già un reparto con questo nome per l'azienda selezionata.", "warning")
        return redirect(url_for('admin.department_management', company_id=company_id))

    new_department = Department(name=department_name, company_id=company_id)
    db.session.add(new_department)
    db.session.commit()
    flash("Reparto creato con successo.", "success")
    return redirect(url_for('admin.department_management', company_id=company_id))

@admin_bp.route('/departments/<int:department_id>/update', methods=['POST'])
@login_required
@admin_required
def update_department(department_id):
    new_name = request.form.get('department_name', '').strip()
    department = Department.query.get_or_404(department_id)
    company_id = department.company_id

    if not new_name:
        flash("Il nome del reparto non può essere vuoto.", "danger")
        return redirect(url_for('admin.department_management', company_id=company_id))

    department.name = new_name
    db.session.commit()
    flash("Reparto aggiornato con successo.", "success")
    return redirect(url_for('admin.department_management', company_id=company_id))

@admin_bp.route('/departments/<int:department_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_department(department_id):
    department = Department.query.get_or_404(department_id)
    company_id = department.company_id

    if department.documents:
        flash("Impossibile eliminare: ci sono documenti associati a questo reparto.", "danger")
        return redirect(url_for('admin.department_management', company_id=company_id))

    db.session.delete(department)
    db.session.commit()
    flash("Reparto eliminato con successo.", "success")
    return redirect(url_for('admin.department_management', company_id=company_id))

# === Gestione Utenti ===
@admin_bp.route('/users')
@login_required
@admin_required
def user_management():
    companies = Company.query.order_by(Company.name).all()
    departments = Department.query.order_by(Department.name).all()
    users = User.query.order_by(User.username).all()

    # ✅ Questa è la variabile mancante
    company_departments = {
        company.id: Department.query.filter_by(company_id=company.id).order_by(Department.name).all()
        for company in companies
    }

    return render_template(
        'admin/user_management.html',
        companies=companies,
        departments=departments,
        users=users,
        company_departments=company_departments  # <== QUESTA È OBBLIGATORIA
    )

@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    if request.form.get('role') == 'guest':
        flash("Creazione utenti guest non consentita da qui.", "danger")
        return redirect(url_for('admin.user_management'))
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    role = request.form.get('role', 'user')
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    can_download = 'can_download' in request.form
    can_access_reserved = 'can_access_reserved' in request.form
    can_manage_files = 'can_manage_files' in request.form

    company_ids = request.form.getlist('company_ids')
    department_ids = request.form.getlist('department_ids')
    access_expiration = request.form.get('access_expiration')

    if role not in ['user', 'guest', 'admin']:
        flash("❌ Ruolo non valido.", "danger")
        return redirect(url_for('admin.user_management'))

    if not username or not email or not password or not company_ids:
        flash("❌ Compila tutti i campi obbligatori e seleziona almeno un'azienda.", "danger")
        return redirect(url_for('admin.user_management'))

    if User.query.filter_by(username=username).first():
        flash("❌ Username già esistente.", "warning")
        return redirect(url_for('admin.user_management'))

    try:
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            username=username,
            email=email,
            password=hashed_pw,
            role=role,
            first_name=first_name,
            last_name=last_name,
            can_download=can_download,
            can_access_reserved=can_access_reserved,
            can_manage_files=can_manage_files,
            password_set_at=datetime.utcnow()
        )

        # Relazioni aziende
        new_user.companies.clear()
        companies = Company.query.filter(Company.id.in_(company_ids)).all()
        new_user.companies.extend(companies)

        # Relazioni reparti
        new_user.departments.clear()
        if department_ids:
            departments = Department.query.filter(Department.id.in_(department_ids)).all()
            new_user.departments.extend(departments)

        # Gestione scadenza solo per guest
        if role == 'guest' and access_expiration:
            try:
                new_user.access_expiration = datetime.strptime(access_expiration, "%Y-%m-%d")
            except Exception:
                flash("⚠️ Data di scadenza non valida.", "warning")

        db.session.add(new_user)
        db.session.commit()

        # Email di benvenuto
        subject = f"Benvenuto in Mercury, {first_name or username}"
        body = (
            f"Ciao {first_name or username},\n\n"
            f"è stato creato per te un account sulla piattaforma Mercury.\n\n"
            f"🔐 Username: {username}\n"
            f"🔑 Password temporanea: {password}\n\n"
            f"Ti consigliamo di accedere e modificare la password al primo accesso.\n\n"
            f"👉 Accedi qui: https://docs.mercurysurgelati.org/login\n\n"
            f"In caso di problemi, contatta l'amministratore."
        )
        try:
            send_email(subject=subject, recipients=[email], body=body)
            current_app.logger.info(f"📧 Email inviata con successo a {email}")
        except Exception as mail_err:
            current_app.logger.error(f"❌ Errore durante invio email a {email}: {mail_err}")

        flash(f"✅ Utente '{username}' creato con successo.<br><strong>Password temporanea:</strong> {password}", "success")

    except IntegrityError:
        db.session.rollback()
        flash("❌ Errore di integrità dati (utente/email già esistente).", "danger")
    except Exception as e:
        db.session.rollback()
        flash("❌ Errore durante la creazione dell'utente.", "danger")
        print("❌ [ERRORE create_user]:", e)
        with open('/tmp/error_create_user.log', 'a') as f:
            f.write(f"\n---\n{datetime.now()}\n")
            f.write(traceback.format_exc())

    return redirect(url_for('admin.user_management'))

@admin_bp.route('/users/<int:user_id>/update', methods=['POST'])
@login_required
def update_user(user_id):
    if not current_user.is_admin:
        return "Accesso negato", 403

    user = User.query.get_or_404(user_id)

    # === Dati comuni ===
    user.username = request.form.get('username', '').strip()
    user.email = request.form.get('email', '').strip().lower()
    user.role = request.form.get('role', 'user')
    print(f"[DEBUG] Prima: user.can_download={user.can_download}")
    user.can_download = bool(request.form.get('can_download'))
    if user.role == 'guest' and 'can_download' not in request.form:
        user.can_download = False
    print(f"[DEBUG] Dopo assegnazione: user.can_download={user.can_download}")

    # === GUEST: access_expiration + revoke_docs ===
    if user.role == 'guest':
        expiration_str = request.form.get('access_expiration')
        if expiration_str:
            try:
                user.access_expiration = datetime.strptime(expiration_str, '%Y-%m-%d').date()
            except ValueError:
                flash("❌ Data scadenza non valida", "danger")
                return redirect(url_for('admin.user_management'))

        revoke_ids = request.form.getlist('revoke_docs')
        if revoke_ids:
            documents = Document.query.filter(Document.id.in_(revoke_ids)).all()
            for doc in documents:
                if doc in user.documents:
                    user.documents.remove(doc)

        # Pulisci aziende/reparti se presenti
        user.companies.clear()
        user.departments.clear()

    # === USER/ADMIN: relazioni aziende/reparti ===
    else:
        company_ids = request.form.getlist('company_ids')
        department_ids = request.form.getlist('department_ids')

        user.companies.clear()
        user.departments.clear()

        if company_ids:
            user.companies.extend(Company.query.filter(Company.id.in_(company_ids)))
        if department_ids:
            user.departments.extend(Department.query.filter(Department.id.in_(department_ids)))

        user.access_expiration = None  # non deve esistere per user/admin

    # === Salva tutto ===
    try:
        db.session.commit()
        print(f"[DEBUG] Dopo commit: user.can_download={user.can_download}")
        flash("✅ Utente aggiornato con successo.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Errore durante il salvataggio: {str(e)}", "danger")

    return redirect(url_for('admin.user_management'))

@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash("✅ Utente eliminato con successo.", "success")
    except Exception as e:
        db.session.rollback()
        flash("❌ Errore durante l'eliminazione dell'utente.", "danger")
        print("❌ [ERRORE delete_user]:", e)
        with open('/tmp/error_delete_user.log', 'a') as f:
            f.write(f"\n---\n{datetime.now()}\n")
            f.write(traceback.format_exc())
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/users/<int:user_id>/reset_password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    new_password = request.form.get('new_password', '').strip()
    if not new_password:
        flash("La nuova password non può essere vuota.", "danger")
        return redirect(url_for('admin.user_management'))
    user = User.query.get_or_404(user_id)
    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
    user.password_set_at = datetime.utcnow()
    db.session.commit()
    flash(f"🔐 Password aggiornata per {user.username}.", "success")
    return redirect(url_for('admin.user_management'))

def send_welcome_email(user, password_plain):
    msg = Message(
        subject="Benvenuto in Mercury Surgelati",
        recipients=[user.email],
        html=render_template("emails/welcome_guest.html", user=user, password=password_plain)
    )
    mail.send(msg)

@admin_bp.route('/guests')
@login_required
def guest_management():
    if not current_user.is_admin:
        flash("Accesso negato", "danger")
        return redirect(url_for('admin.admin_dashboard'))
    guests = User.query.filter_by(role='guest').all()
    companies = Company.query.all()
    departments = Department.query.all()
    return render_template('admin/guest_management.html', guests=guests, companies=companies, departments=departments)

@admin_bp.route('/guests/create', methods=['POST'])
@login_required
@admin_required
def create_guest():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    access_expiration = request.form.get('access_expiration')
    can_download = 'can_download' in request.form
    nome = request.form.get('nome', '').strip()
    cognome = request.form.get('cognome', '').strip()

    # Validazioni avanzate
    if not username:
        flash("Username obbligatorio.", "danger")
        return redirect(url_for('admin.guest_management'))
    if User.query.filter_by(username=username).first():
        flash("Username già in uso.", "danger")
        return redirect(url_for('admin.guest_management'))
    if not email:
        flash("Email obbligatoria.", "danger")
        return redirect(url_for('admin.guest_management'))
    if User.query.filter_by(email=email).first():
        flash("Email già registrata.", "danger")
        return redirect(url_for('admin.guest_management'))
    if not password or len(password) < 8:
        flash("La password deve essere di almeno 8 caratteri.", "danger")
        return redirect(url_for('admin.guest_management'))

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    new_guest = User(
        username=username,
        email=email,
        password=hashed_pw,
        role='guest',
        can_download=can_download
    )
    new_guest.nome = nome
    new_guest.cognome = cognome

    if access_expiration:
        try:
            new_guest.access_expiration = datetime.strptime(access_expiration, "%Y-%m-%d")
        except Exception:
            flash("⚠️ Data di scadenza non valida.", "warning")

    db.session.add(new_guest)
    db.session.commit()
    send_welcome_email(new_guest, password)
    flash("✅ Guest creato con successo e email inviata.", "success")
    return redirect(url_for('admin.guest_management'))

# === Statistiche Attività ===
@admin_bp.route("/stats")
@login_required
def admin_stats():
    if not current_user.is_admin:
        return "Accesso negato", 403

    from sqlalchemy import func
    from datetime import datetime, timedelta

    # Intervallo di giorni (default: 7)
    days = int(request.args.get("days", 7))
    start_date = datetime.utcnow() - timedelta(days=days)

    # === METRICHE
    total_uploads = Document.query.count()
    total_downloads = db.session.query(func.count()).select_from(GuestActivity).scalar()
    active_guests = db.session.query(User).filter_by(role='guest').count()
    total_users = User.query.count()

    # === UPLOAD PER GIORNO (con giorni vuoti)
    date_labels = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    upload_counts_raw = db.session.query(
        func.strftime('%Y-%m-%d', Document.created_at),
        func.count()
    ).filter(Document.created_at >= start_date).group_by(func.strftime('%Y-%m-%d', Document.created_at)).all()
    upload_counts_dict = dict(upload_counts_raw)

    uploads_per_day_labels = date_labels
    uploads_per_day_counts = [upload_counts_dict.get(day, 0) for day in date_labels]

    # === UPLOAD/DOWNLOAD SETTIMANALI (ultimi 7 giorni sempre)
    last_week = datetime.utcnow() - timedelta(days=7)
    weekly_uploads_data = db.session.query(
        func.strftime('%w', Document.created_at),
        func.count()
    ).filter(Document.created_at >= last_week).group_by(func.strftime('%w', Document.created_at)).all()
    weekly_downloads_data = db.session.query(
        func.strftime('%w', GuestActivity.timestamp),
        func.count()
    ).filter(GuestActivity.timestamp >= last_week).group_by(func.strftime('%w', GuestActivity.timestamp)).all()

    weekday_map = ['Dom', 'Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab']
    weekly_labels = weekday_map
    uploads_by_day = {day: 0 for day in range(7)}
    downloads_by_day = {day: 0 for day in range(7)}
    for day, count in weekly_uploads_data:
        uploads_by_day[int(day)] = count
    for day, count in weekly_downloads_data:
        downloads_by_day[int(day)] = count
    weekly_uploads = [uploads_by_day[i] for i in range(7)]
    weekly_downloads = [downloads_by_day[i] for i in range(7)]

    # === DISTRIBUZIONE PER TIPO DOCUMENTO
    doc_type_raw = db.session.query(
        func.lower(func.substr(Document.filename, -4)).label('ext'),
        func.count()
    ).group_by('ext').all()
    doc_type_labels = [ext or "Altro" for ext, _ in doc_type_raw]
    doc_type_counts = [count for _, count in doc_type_raw]

    # === UPLOAD PER AZIENDA
    uploads_by_company = db.session.query(Company.name, func.count()).join(Document.company).group_by(Company.name).all()
    uploads_by_company_labels = [c or "Sconosciuta" for c, _ in uploads_by_company]
    uploads_by_company_counts = [n for _, n in uploads_by_company]

    # === UPLOAD PER REPARTO
    uploads_by_department = db.session.query(Department.name, func.count()).join(Document.department).group_by(Department.name).all()
    uploads_by_department_labels = [d or "Sconosciuto" for d, _ in uploads_by_department]
    uploads_by_department_counts = [n for _, n in uploads_by_department]

    # === UPLOAD PER UTENTE
    uploads_by_user = db.session.query(User.username, func.count()).join(Document, Document.user_id == User.id).group_by(User.username).all()
    uploads_by_user_labels = [u or "N/A" for u, _ in uploads_by_user]
    uploads_by_user_counts = [n for _, n in uploads_by_user]

    return render_template("admin/statistiche_attivita.html",
        total_uploads=total_uploads or 0,
        total_downloads=total_downloads or 0,
        active_guests=active_guests or 0,
        total_users=total_users or 0,
        uploads_per_day_labels=uploads_per_day_labels or [],
        uploads_per_day_counts=uploads_per_day_counts or [],
        weekly_labels=weekly_labels,
        weekly_uploads=weekly_uploads or [],
        weekly_downloads=weekly_downloads or [],
        doc_type_labels=doc_type_labels or [],
        doc_type_counts=doc_type_counts or [],
        uploads_by_company_labels=uploads_by_company_labels or [],
        uploads_by_company_counts=uploads_by_company_counts or [],
        uploads_by_department_labels=uploads_by_department_labels or [],
        uploads_by_department_counts=uploads_by_department_counts or [],
        uploads_by_user_labels=uploads_by_user_labels or [],
        uploads_by_user_counts=uploads_by_user_counts or [],
        selected_days=days
    )

# === Visualizzazione File ===
@admin_bp.route('/file_structure')
@login_required
@admin_required
def file_structure():
    if not current_user.is_admin:
        flash("Accesso negato", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    companies = Company.query.options(
        joinedload(Company.departments).joinedload(Department.documents)
    ).all()

    return render_template('admin/file_structure.html', companies=companies)

# === Documenti (Overview) ===
@admin_bp.route('/documents')
@login_required
@admin_required
def documents_overview():
    today = datetime.utcnow()
    modulo_filter = request.args.get('modulo', '').strip()
    
    # Query base per documenti obsoleti e protetti
    obsolete_docs = Document.query.filter(Document.expiry_date != None, Document.expiry_date < today).all()
    protected_docs = Document.query.filter(Document.password != None).all()
    
    # Query per tutti i documenti con filtro modulo
    all_docs_query = Document.query.order_by(Document.created_at.desc())
    
    if modulo_filter:
        all_docs_query = all_docs_query.filter_by(collegato_a_modulo=modulo_filter)
    
    all_docs = all_docs_query.all()
    
    return render_template("admin/documents_overview.html",
                           obsolete_docs=obsolete_docs,
                           protected_docs=protected_docs,
                           all_docs=all_docs,
                           modulo_filter=modulo_filter)

@admin_bp.route('/documents/<int:document_id>')
@login_required
@admin_required
def view_document(document_id):
    doc = Document.query.get_or_404(document_id)
    return render_template("admin/view_document.html", doc=doc)

@admin_bp.route('/documents/<int:document_id>/edit-password', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_document_password(document_id):
    try:
        doc = Document.query.get_or_404(document_id)
    except Exception as e:
        current_app.logger.error(f"Errore caricamento documento {document_id}: {e}")
        return "Documento non trovato", 404
    if request.method == 'POST':
        try:
            new_password = request.form.get('new_password', '').strip()
            if new_password:
                doc.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            else:
                doc.password = None
            db.session.commit()
            flash("Password aggiornata con successo", "success")
            return redirect(url_for('admin.documents_overview'))
        except Exception as e:
            current_app.logger.error(f"Errore aggiornamento password documento {document_id}: {e}")
            flash("Errore durante l'aggiornamento della password.", "danger")
    return render_template("admin/edit_password.html", doc=doc)

# === Visualizzazione File ===
@admin_bp.route('/file-browser')
@login_required
@admin_required
def file_browser():
    
    # Renderizza la pagina di visualizzazione struttura file
    return render_template('admin/file_structure.html')

@admin_bp.route('/users/<int:user_id>/reset_password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):

    user = User.query.get_or_404(user_id)

    # Genera token sicuro valido 24h
    token = serializer.dumps(user.email, salt='reset-password')

    reset_url = url_for('auth.reset_password_token', token=token, _external=True)

    try:
        send_email(
            subject="🔐 Reset password - Mercury",
            recipients=[user.email],
            body=f"Clicca il link seguente per reimpostare la tua password:\n{reset_url}"
        )
        flash(f"✅ Email di reset inviata a {user.email}", "success")
    except Exception as e:
        flash("❌ Errore durante l'invio dell'email.", "danger")
        app.logger.error(f"[RESET PW] Errore invio email: {e}")

    return redirect(url_for('admin.user_management'))

@admin_bp.route('/download_document/<int:document_id>')
@login_required
def download_document(document_id):
    from models import Document, DownloadLog, db
    if not current_user.is_admin:
        flash("Accesso negato", "danger")
        return redirect(url_for('admin.file_structure'))

    document = Document.query.get_or_404(document_id)

    # Log download
    log = DownloadLog(user_id=current_user.id, document_id=document.id)
    db.session.add(log)
    db.session.commit()

    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        document.filename,
        as_attachment=True
    )

@admin_bp.route('/statistiche')
@login_required
def statistiche():
    if not current_user.is_admin:
        flash("Accesso negato", "danger")
        return redirect(url_for('admin.admin_dashboard'))
    # Calcola tutte le statistiche come nella dashboard
    from sqlalchemy import func
    from models import Document, User, GuestActivity, AdminLog
    from datetime import datetime, timedelta
    range_type = request.args.get('range', '7')
    start = request.args.get('start')
    end = request.args.get('end')
    today = datetime.utcnow().date()
    if range_type == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif range_type == 'custom' and start and end:
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()
    else:
        try:
            days = int(range_type)
        except Exception:
            days = 7
        start_date = today - timedelta(days=days-1)
        end_date = today
    delta = (end_date - start_date).days
    weekly_labels = [(start_date + timedelta(days=i)).strftime('%d/%m') for i in range(delta+1)]
    weekly_uploads = []
    weekly_downloads = []
    for i in range(delta+1):
        day = start_date + timedelta(days=i)
        uploads = Document.query.filter(func.date(Document.created_at) == day).count()
        downloads = GuestActivity.query.filter(func.date(GuestActivity.timestamp) == day).count()
        weekly_uploads.append(uploads)
        weekly_downloads.append(downloads)
    total_uploads = Document.query.count()
    total_downloads = GuestActivity.query.count()
    active_guests = User.query.filter_by(role='guest').filter(User.access_expiration == None).count()
    total_users = User.query.count()
    doc_type_counts = []
    doc_type_labels = []
    for ext, count in (
        db.session.query(
            func.lower(func.substr(Document.filename, -4)),
            func.count()
        ).group_by(func.lower(func.substr(Document.filename, -4)))
    ):
        doc_type_labels.append(ext)
        doc_type_counts.append(count)
    recent_logs = AdminLog.query.order_by(AdminLog.timestamp.desc()).limit(20).all()
    weekly_labels = list(weekly_labels) if weekly_labels else []
    weekly_uploads = list(weekly_uploads) if weekly_uploads else []
    weekly_downloads = list(weekly_downloads) if weekly_downloads else []
    doc_type_labels = list(doc_type_labels) if doc_type_labels else []
    doc_type_counts = list(doc_type_counts) if doc_type_counts else []
    return render_template(
        'admin/statistiche.html',
        total_uploads=total_uploads,
        total_downloads=total_downloads,
        active_guests=active_guests,
        total_users=total_users,
        weekly_labels=weekly_labels,
        weekly_uploads=weekly_uploads or [],
        weekly_downloads=weekly_downloads or [],
        doc_type_labels=doc_type_labels or [],
        doc_type_counts=doc_type_counts or [],
        recent_logs=recent_logs,
        start_date=start_date,
        end_date=end_date,
        range_type=range_type
    )

@admin_bp.route('/ai/send_task', methods=['POST'])
@login_required
def ai_send_task():
    if not current_user.is_admin:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"success": False, "message": "Accesso negato"}, 403
        flash("Accesso negato", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    task_title = request.form.get('task_title', '').strip()
    task_description = request.form.get('task_description', '').strip()

    if not task_title or not task_description:
        msg = "Titolo e descrizione sono obbligatori."
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"success": False, "message": msg}, 400
        flash(msg, "warning")
        return redirect(url_for('admin.admin_dashboard'))

    payload = {
        "title": task_title,
        "description": task_description,
        "created_by": current_user.username,
        "priority": "media"
    }
    api_token = os.environ.get('FOCUS_API_TOKEN', 'YOUR_API_TOKEN')
    try:
        response = requests.post(
            "https://focus.mercurysurgelati.org/api/tasks",
            json=payload,
            headers={"Authorization": f"Bearer {api_token}"}
        )
        response.raise_for_status()
    except requests.RequestException as e:
        msg = f"Errore invio task AI: {e}"
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {"success": False, "message": msg}, 500
        flash(msg, "danger")
        return redirect(url_for('admin.admin_dashboard'))

    msg = "Task inviato con successo a FocusMercury!"
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {"success": True, "message": msg}
    flash(msg, "success")
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/ai/tasks', methods=['GET'])
@login_required
@admin_required
def ai_list_tasks():
    api_token = os.environ.get('FOCUS_API_TOKEN', 'YOUR_API_TOKEN')
    username = current_user.username
    try:
        response = requests.get(
            "https://focus.mercurysurgelati.org/api/tasks",
            headers={"Authorization": f"Bearer {api_token}"},
            params={"created_by": username}
        )
        response.raise_for_status()
        tasks = response.json()
        return {"success": True, "tasks": tasks}
    except requests.RequestException as e:
        return {"success": False, "message": f"Errore nel recupero task: {e}"}, 500

@admin_bp.route("/access-requests")
@login_required
def access_requests_admin():
    if not current_user.is_admin:
        return "Accesso negato", 403
    requests = AccessRequest.query.order_by(AccessRequest.timestamp.desc()).all()
    return render_template("admin/access_requests.html", requests=requests)

@admin_bp.route("/access-requests/<int:request_id>/set", methods=["POST"])
@login_required
def set_access_request_status(request_id):
    from models import AccessRequest
    if not current_user.is_admin:
        return "Accesso negato", 403

    status = request.form.get("status")
    req = AccessRequest.query.get_or_404(request_id)

    if status in ["approved", "rejected"]:
        req.status = status
        db.session.commit()

        # Invia email notifica all'utente
        if req.user.email:
            from flask_mail import Message
            from extensions import mail
            subject = "Richiesta accesso documento " + ("approvata ✅" if status == "approved" else "rifiutata ❌")
            msg = Message(subject, recipients=[req.user.email])
            msg.body = f"""
Ciao {req.user.username},

La tua richiesta di accesso al documento "{req.document.original_filename}\" è stata {status.upper()}.

Grazie,
Sistema documenti
"""
            mail.send(msg)

    return redirect(url_for('admin.access_requests_admin'))

@admin_bp.route('/export_downloads_csv')
@login_required
def export_downloads_csv():
    if not current_user.is_admin:
        return "Accesso negato", 403

    from models import DownloadLog, db
    logs = db.session.query(DownloadLog).order_by(DownloadLog.timestamp.desc()).all()

    # CSV in memoria
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(['Utente', 'Email', 'Documento', 'Azienda', 'Reparto', 'Data'])

    for log in logs:
        user = log.user
        doc = log.document
        writer.writerow([
            user.username,
            user.email,
            doc.original_filename,
            doc.company.name if doc.company else '—',
            doc.department.name if doc.department else '—',
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        ])

    response = Response(csv_data.getvalue(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="download_log.csv")
    return response

@admin_bp.route('/access_requests')
@login_required
def access_requests():
    if not current_user.is_admin:
        return "Accesso negato", 403

    # Filtri
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    username_filter = request.args.get('username', '')
    
    # Query base
    query = AccessRequest.query
    
    # Applica filtri
    if status_filter:
        query = query.filter(AccessRequest.status == status_filter)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AccessRequest.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AccessRequest.created_at < to_date)
        except ValueError:
            pass
    
    if username_filter:
        query = query.join(User).filter(User.username.ilike(f'%{username_filter}%'))
    
    # Ordina per data creazione (più recenti prima)
    requests = query.order_by(AccessRequest.created_at.desc()).all()
    
    return render_template("admin/admin_access_requests.html", 
                         requests=requests,
                         status_filter=status_filter,
                         date_from=date_from,
                         date_to=date_to,
                         username_filter=username_filter)

@admin_bp.route('/access_requests/<int:req_id>', methods=['POST'])
@login_required
def handle_access_request(req_id):
    if not current_user.is_admin:
        return "Accesso negato", 403

    action = request.form.get('action')
    req = AccessRequest.query.get_or_404(req_id)

    if req.status != 'pending':
        flash("Richiesta già gestita.", "warning")
        return redirect(url_for('admin.access_requests'))

    user_email = req.user.email
    doc_name = req.document.filename
    subject = f"Esito richiesta accesso al file '{doc_name}'"
    
    if action == 'approve':
        req.status = 'approved'
        req.resolved_at = datetime.utcnow()
        db.session.add(AuthorizedAccess(user_id=req.user_id, document_id=req.document_id))
        flash("Accesso approvato!", "success")
        subject = "✅ Richiesta approvata"
        body = f"""Ciao {req.user.username},

La tua richiesta di accesso al documento "{doc_name}" è stata APPROVATA.

Data risposta: {req.resolved_at.strftime('%d/%m/%Y %H:%M')}

Ora puoi scaricare il documento dal tuo pannello.

Grazie,
Sistema documenti"""
    elif action == 'deny':
        req.status = 'denied'
        req.resolved_at = datetime.utcnow()
        flash("Accesso rifiutato.", "danger")
        subject = "❌ Richiesta negata"
        body = f"""Ciao {req.user.username},

Purtroppo la tua richiesta di accesso al documento "{doc_name}" è stata RIFIUTATA.

Data risposta: {req.resolved_at.strftime('%d/%m/%Y %H:%M')}

Per maggiori informazioni, contatta l'amministrazione.

Grazie,
Sistema documenti"""
    else:
        flash("Azione non valida.", "warning")
        return redirect(url_for('admin.access_requests'))

    db.session.commit()

    # Invio email
    try:
        from app import send_email
        send_email(subject, [user_email], body)
        flash("Email di notifica inviata con successo.", "info")
    except Exception as e:
        current_app.logger.error(f"Errore invio email a {user_email}: {str(e)}")
        flash("Errore nell'invio dell'email di notifica.", "warning")

    return redirect(url_for('admin.access_requests'))

@admin_bp.route('/export_access_requests')
@login_required
def export_access_requests():
    """
    Esporta le richieste di accesso in formato CSV.
    """
    if not current_user.is_admin:
        return "Accesso negato", 403

    # Applica gli stessi filtri della vista principale
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    username_filter = request.args.get('username', '')
    
    # Query base
    query = AccessRequest.query
    
    # Applica filtri
    if status_filter:
        query = query.filter(AccessRequest.status == status_filter)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AccessRequest.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AccessRequest.created_at < to_date)
        except ValueError:
            pass
    
    if username_filter:
        query = query.join(User).filter(User.username.ilike(f'%{username_filter}%'))
    
    # Ordina per data creazione
    requests = query.order_by(AccessRequest.created_at.desc()).all()

    # Crea CSV
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow([
        'ID Richiesta', 'Username', 'Email', 'Documento', 'Azienda', 'Reparto',
        'Stato', 'Nota', 'Data Richiesta', 'Data Risposta'
    ])

    for req in requests:
        writer.writerow([
            req.id,
            req.user.username,
            req.user.email,
            req.document.title or req.document.original_filename,
            req.document.company.name if req.document.company else 'N/A',
            req.document.department.name if req.document.department else 'N/A',
            req.status,
            req.note or '',
            req.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            req.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if req.resolved_at else ''
        ])

    response = Response(csv_data.getvalue(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename=f"access_requests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    return response

@admin_bp.route("/log_attivita")
@login_required
def log_attivita():
    if not current_user.is_admin:
        return "Accesso negato", 403

    logs = DocumentActivityLog.query.order_by(DocumentActivityLog.timestamp.desc()).limit(200).all()
    return render_template("admin/log_attivita.html", logs=logs)

@admin_bp.route("/documents/<int:doc_id>/riepilogo_pdf")
@login_required
def export_document_summary(doc_id):
    """
    Esporta un PDF riepilogativo per un documento specifico.
    
    Args:
        doc_id (int): ID del documento da esportare.
        
    Returns:
        PDF file: File PDF con riepilogo del documento.
    """
    # Verifica permessi admin o CEO
    if not (current_user.is_admin or current_user.is_ceo):
        flash("❌ Accesso negato. Solo admin e CEO possono esportare riepiloghi.", "danger")
        return redirect(url_for('admin.documents_overview'))
    
    # Recupera documento con relazioni
    documento = Document.query.options(
        joinedload(Document.company),
        joinedload(Document.department),
        joinedload(Document.uploader),
        joinedload(Document.versioni).joinedload(DocumentVersion.read_logs).joinedload(DocumentReadLog.user)
    ).get(doc_id)
    
    if not documento:
        flash("❌ Documento non trovato.", "danger")
        return redirect(url_for('admin.documents_overview'))
    
    try:
        # Genera HTML per il PDF
        html_content = render_template(
            "pdf/document_summary.html",
            documento=documento,
            now=datetime.utcnow()
        )
        
        # Genera PDF con WeasyPrint
        pdf = HTML(string=html_content).write_pdf()
        
        # Crea nome file
        filename = f"riepilogo_documento_{documento.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Log dell'azione
        current_app.logger.info(f"[PDF EXPORT] Admin {current_user.username} ha esportato il riepilogo PDF del documento {documento.id}")
        
        # Ritorna il PDF come file da scaricare
        return send_file(
            BytesIO(pdf),
            download_name=filename,
            as_attachment=True,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"[PDF EXPORT] Errore generazione PDF per documento {doc_id}: {str(e)}")
        flash("❌ Errore durante la generazione del PDF. Contatta il supporto tecnico.", "danger")
        return redirect(url_for('admin.view_document', document_id=doc_id))

# === LOG DOWNLOAD DOCUMENTI ===
from models import DownloadLog, DocumentVersion
import csv
from io import StringIO

@admin_bp.route('/admin/log_download')
@login_required
def log_download():
    if not (current_user.is_admin or current_user.is_ceo):
        flash("Accesso negato: solo admin e CEO.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    # Filtri
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('utente', type=int) or request.args.get('user_id', type=int)
    company_id = request.args.get('azienda', type=int) or request.args.get('company_id', type=int)
    department_id = request.args.get('reparto', type=int) or request.args.get('department_id', type=int)
    is_ajax = request.args.get('ajax') == '1'

    # Query base con join
    query = DownloadLog.query \
        .join(User, DownloadLog.user_id == User.id) \
        .join(Document, DownloadLog.document_id == Document.id) \
        .join(Company, Document.company_id == Company.id) \
        .join(Department, Document.department_id == Department.id) \
        .outerjoin(DocumentVersion, (DocumentVersion.document_id == Document.id) & (DocumentVersion.data_caricamento <= DownloadLog.timestamp))

    # Applica filtri
    if start_date:
        try:
            from_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(DownloadLog.timestamp >= from_date)
        except Exception:
            pass
    if end_date:
        try:
            to_date = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(DownloadLog.timestamp <= to_date)
        except Exception:
            pass
    if user_id:
        query = query.filter(DownloadLog.user_id == user_id)
    if company_id:
        query = query.filter(Document.company_id == company_id)
    if department_id:
        query = query.filter(Document.department_id == department_id)

    # Ordinamento per data decrescente
    query = query.order_by(DownloadLog.timestamp.desc())

    logs = query.all()

    # Funzioni di utilità per protetta/scaduto
    def is_protected(doc):
        # Considera protetto se visibilità non pubblica o scaduto
        return (getattr(doc, 'visibility', None) != 'pubblico') or is_expired(doc)
    def is_expired(doc):
        expiry = getattr(doc, 'expiry_date', None)
        return expiry is not None and expiry < datetime.utcnow()

    # Risposta AJAX (JSON)
    if is_ajax:
        result = []
        for log in logs:
            user = log.user
            doc = log.document
            company = doc.company
            dept = doc.department
            versione = DocumentVersion.query.filter_by(document_id=doc.id).filter(DocumentVersion.data_caricamento <= log.timestamp).order_by(DocumentVersion.data_caricamento.desc()).first()
            result.append({
                'timestamp': log.timestamp.strftime('%d/%m/%Y %H:%M'),
                'user': f"{user.first_name or ''} {user.last_name or ''} <{user.email}>",
                'azienda': company.name if company else '',
                'reparto': dept.name if dept else '',
                'documento': doc.title or doc.original_filename,
                'versione': versione.numero_versione if versione else '',
                'protetta': is_protected(doc),
                'scaduto': is_expired(doc),
                'ip': getattr(log, 'ip', ''),
                'file': doc.filename
            })
        return jsonify(result)

    # Recupera dati per i filtri (dropdown)
    utenti = User.query.order_by(User.first_name, User.last_name).all()
    aziende = Company.query.order_by(Company.name).all()
    reparti = Department.query.order_by(Department.name).all()

    return render_template(
        "admin/log_download.html",
        logs=logs,
        utenti=utenti,
        aziende=aziende,
        reparti=reparti,
        filtri={
            'start_date': start_date,
            'end_date': end_date,
            'user_id': user_id,
            'company_id': company_id,
            'department_id': department_id
        }
    )

@admin_bp.route('/admin/log_download/export')
@login_required
def export_log_download():
    if not (current_user.is_admin or current_user.is_ceo):
        flash("Accesso negato: solo admin e CEO.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    # Filtri come sopra
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id', type=int)
    company_id = request.args.get('company_id', type=int)
    department_id = request.args.get('department_id', type=int)

    query = DownloadLog.query \
        .join(User, DownloadLog.user_id == User.id) \
        .join(Document, DownloadLog.document_id == Document.id) \
        .join(Company, Document.company_id == Company.id) \
        .join(Department, Document.department_id == Department.id) \
        .outerjoin(DocumentVersion, (DocumentVersion.document_id == Document.id) & (DocumentVersion.data_caricamento <= DownloadLog.timestamp))

    if start_date:
        try:
            from_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(DownloadLog.timestamp >= from_date)
        except Exception:
            pass
    if end_date:
        try:
            to_date = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(DownloadLog.timestamp <= to_date)
        except Exception:
            pass
    if user_id:
        query = query.filter(DownloadLog.user_id == user_id)
    if company_id:
        query = query.filter(Document.company_id == company_id)
    if department_id:
        query = query.filter(Document.department_id == department_id)

    query = query.order_by(DownloadLog.timestamp.desc())
    logs = query.all()

    # Genera CSV
    csv_data = StringIO()
    writer = csv.writer(csv_data, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        'Data Download', 'Nome Utente', 'Email', 'Titolo Documento', 'Versione', 'Azienda', 'Reparto', 'IP', 'Nome File'
    ])
    for log in logs:
        user = log.user
        doc = log.document
        company = doc.company
        dept = doc.department
        # Trova versione più recente <= download
        versione = DocumentVersion.query.filter_by(document_id=doc.id).filter(DocumentVersion.data_caricamento <= log.timestamp).order_by(DocumentVersion.data_caricamento.desc()).first()
        writer.writerow([
            log.timestamp.strftime('%d/%m/%Y %H:%M'),
            f"{user.first_name or ''} {user.last_name or ''}",
            user.email,
            doc.title or doc.original_filename,
            versione.numero_versione if versione else '',
            company.name if company else '',
            dept.name if dept else '',
            getattr(log, 'ip', ''),
            doc.filename
        ])

    # Logging esportazione
    admin_log = AdminLog(
        action="esportazione_log_download",
        performed_by=current_user.email,
        document_id=None,
        downloadable=False
    )
    db.session.add(admin_log)
    db.session.commit()

    response = Response(csv_data.getvalue(), mimetype='text/csv; charset=utf-8')
    response.headers.set("Content-Disposition", "attachment", filename="log_download.csv")
    return response

def create_ai_task_for_missing_signature(user_id, document_id, reason):
    """
    Crea un task automatico AI per richiesta firma mancante.
    
    Args:
        user_id (int): ID utente che ha tentato il download.
        document_id (int): ID documento critico.
        reason (str): Motivo del rifiuto.
    """
    try:
        user = User.query.get(user_id)
        document = Document.query.get(document_id)
        
        if not user or not document:
            current_app.logger.error(f"Utente o documento non trovato per task AI: user_id={user_id}, doc_id={document_id}")
            return
        
        # Verifica se il documento è critico e richiede firma
        if not document.is_critical or not document.richiedi_firma:
            return
        
        # Verifica se esiste già un task per questa combinazione
        existing_task = AdminLog.query.filter(
            AdminLog.action == "ai_task_signature_request",
            AdminLog.performed_by == user.email,
            AdminLog.document_id == document_id,
            AdminLog.extra_info.like(f"%{reason}%")
        ).first()
        
        if existing_task:
            current_app.logger.info(f"Task AI già esistente per {user.email} e documento {document_id}")
            return
        
        # Crea il task AI
        task_data = {
            'title': f"Richiesta firma urgente – {document.title}",
            'assigned_to': document.uploader_email,  # Assegna al proprietario del documento
            'description': f"L'utente {user.email} ha tentato il download del documento critico '{document.title}', ma manca la firma richiesta.",
            'deadline': datetime.utcnow() + timedelta(hours=48),
            'priority': 'Alta',
            'origin': 'Sistema AI – Controllo Download',
            'document_id': document_id,
            'requesting_user': user.email
        }
        
        # Log del task AI
        admin_log = AdminLog(
            action="ai_task_signature_request",
            performed_by=user.email,
            document_id=document_id,
            downloadable=False,
            extra_info=f"Task creato: {task_data['title']} - Assegnato a: {task_data['assigned_to']}"
        )
        db.session.add(admin_log)
        
        # Invia notifica email al proprietario del documento
        try:
            if document.uploader_email:
                subject = f"🔐 Richiesta Firma Urgente - {document.title}"
                body = f"""
                Attenzione! È richiesta la tua firma per il documento critico.
                
                Documento: {document.title}
                Richiesto da: {user.email}
                Motivo: {reason}
                Scadenza: 48 ore
                
                Accedi al sistema per completare la firma.
                """
                
                msg = Message(
                    subject=subject,
                    recipients=[document.uploader_email],
                    body=body
                )
                mail.send(msg)
                current_app.logger.info(f"Email task AI inviata a {document.uploader_email}")
                
        except Exception as e:
            current_app.logger.error(f"Errore invio email task AI: {e}")
        
        # Notifica FocusMe AI (se endpoint disponibile)
        try:
            focusme_url = current_app.config.get('FOCUSME_AI_URL')
            if focusme_url:
                task_notification = {
                    'type': 'signature_request_task',
                    'task_data': task_data,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                response = requests.post(
                    f"{focusme_url}/tasks",
                    json=task_notification,
                    timeout=10
                )
                if response.status_code == 200:
                    current_app.logger.info(f"Task FocusMe AI creato per {user.email}")
                    
        except Exception as e:
            current_app.logger.error(f"Errore creazione task FocusMe AI: {e}")
        
        db.session.commit()
        current_app.logger.info(f"Task AI creato per firma mancante: {user.email} -> {document.title}")
        
    except Exception as e:
        current_app.logger.error(f"Errore creazione task AI: {e}")
        db.session.rollback()

def log_download_denied(user_id, document_id, reason, ip_address=None, user_agent=None):
    """
    Registra un tentativo di download negato.
    
    Args:
        user_id (int): ID utente che ha tentato il download.
        document_id (int): ID documento richiesto.
        reason (str): Motivo del rifiuto.
        ip_address (str, optional): IP del client.
        user_agent (str, optional): User agent del browser.
    """
    try:
        denied_log = DownloadDeniedLog(
            user_id=user_id,
            document_id=document_id,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(denied_log)
        db.session.commit()
        
        # Log amministrativo
        admin_log = AdminLog(
            action="download_denied",
            performed_by=f"user_id:{user_id}",
            document_id=document_id,
            downloadable=False,
            extra_info=f"Motivo: {reason}"
        )
        db.session.add(admin_log)
        db.session.commit()
        
        # Se è firma mancante su documento critico, crea task AI
        if reason == "Firma mancante":
            create_ai_task_for_missing_signature(user_id, document_id, reason)
        
        current_app.logger.info(f"Download negato registrato: utente {user_id}, documento {document_id}, motivo: {reason}")
        
    except Exception as e:
        current_app.logger.error(f"Errore registrazione download negato: {e}")
        db.session.rollback()

# === FUNZIONI ALERT AUTOMATICI AI ===

# === FUNZIONI AI ASSISTANT PER INSIGHT STRATEGICI ===
def generate_ai_insights():
    """
    Genera insight AI analizzando i dati recenti dei download negati.
    """
    try:
        # Analizza dati ultimi 14 giorni
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        recent_denials = DownloadDeniedLog.query.filter(
            DownloadDeniedLog.timestamp >= two_weeks_ago
        ).all()
        
        if not recent_denials:
            return []
        
        insights = []
        
        # 1. Analisi utenti critici (più di 5 tentativi negati)
        critical_users = db.session.query(
            DownloadDeniedLog.user_id,
            func.count(DownloadDeniedLog.id).label('count')
        ).filter(
            DownloadDeniedLog.timestamp >= two_weeks_ago
        ).group_by(DownloadDeniedLog.user_id).having(
            func.count(DownloadDeniedLog.id) >= 5
        ).all()
        
        for user_id, count in critical_users:
            user = User.query.get(user_id)
            if user:
                insight = InsightAI(
                    insight_text=f"⚠️ ATTENZIONE: L'utente {user.email} ha tentato {count} download negati negli ultimi 14 giorni. "
                               f"Verificare se necessita di formazione o se ci sono problemi di accesso.",
                    insight_type="sicurezza",
                    severity="critico",
                    affected_users=json.dumps([{"id": user_id, "email": user.email, "count": count}]),
                    pattern_data=json.dumps({"pattern": "user_critical", "count": count, "period": "14_days"})
                )
                insights.append(insight)
        
        # 2. Analisi motivi ricorrenti (più del 40% di un motivo)
        total_denials = len(recent_denials)
        if total_denials > 0:
            reasons_analysis = db.session.query(
                DownloadDeniedLog.reason,
                func.count(DownloadDeniedLog.id).label('count')
            ).filter(
                DownloadDeniedLog.timestamp >= two_weeks_ago
            ).group_by(DownloadDeniedLog.reason).all()
            
            for reason, count in reasons_analysis:
                percentage = (count / total_denials) * 100
                if percentage > 40:
                    insight = InsightAI(
                        insight_text=f"📊 PATTERN RILEVATO: Il motivo '{reason}' rappresenta il {percentage:.1f}% dei download negati. "
                                   f"Considerare interventi specifici per ridurre questo tipo di rifiuti.",
                        insight_type="pattern",
                        severity="attenzione",
                        pattern_data=json.dumps({
                            "reason": reason,
                            "count": count,
                            "percentage": percentage,
                            "total_denials": total_denials
                        })
                    )
                    insights.append(insight)
        
        # 3. Analisi documenti critici con firma mancante
        critical_docs_denials = db.session.query(
            DownloadDeniedLog.document_id,
            func.count(DownloadDeniedLog.id).label('count')
        ).join(Document).filter(
            DownloadDeniedLog.timestamp >= two_weeks_ago,
            DownloadDeniedLog.reason == "Firma mancante",
            Document.is_critical == True
        ).group_by(DownloadDeniedLog.document_id).having(
            func.count(DownloadDeniedLog.id) >= 3
        ).all()
        
        for doc_id, count in critical_docs_denials:
            doc = Document.query.get(doc_id)
            if doc:
                insight = InsightAI(
                    insight_text=f"🔒 CRITICO: Il documento critico '{doc.title}' ha {count} tentativi di download negati per firma mancante. "
                               f"Richiedere immediatamente le firme mancanti.",
                    insight_type="firma",
                    severity="critico",
                    affected_documents=json.dumps([{"id": doc_id, "title": doc.title, "count": count}]),
                    pattern_data=json.dumps({"pattern": "critical_doc_missing_signature", "count": count})
                )
                insights.append(insight)
        
        # 4. Analisi trend temporale (aumento negli ultimi 3 giorni)
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        recent_3_days = DownloadDeniedLog.query.filter(
            DownloadDeniedLog.timestamp >= three_days_ago
        ).count()
        
        previous_3_days = DownloadDeniedLog.query.filter(
            DownloadDeniedLog.timestamp >= datetime.utcnow() - timedelta(days=6),
            DownloadDeniedLog.timestamp < three_days_ago
        ).count()
        
        if recent_3_days > previous_3_days and recent_3_days >= 3:
            increase = ((recent_3_days - previous_3_days) / previous_3_days * 100) if previous_3_days > 0 else 100
            insight = InsightAI(
                insight_text=f"📈 TREND NEGATIVO: Aumento del {increase:.1f}% nei download negati negli ultimi 3 giorni "
                           f"({recent_3_days} vs {previous_3_days}). Verificare cause e implementare correttivi.",
                insight_type="trend",
                severity="attenzione",
                pattern_data=json.dumps({
                    "recent_count": recent_3_days,
                    "previous_count": previous_3_days,
                    "increase_percentage": increase
                })
            )
            insights.append(insight)
        
        # 5. Analisi reparti con più problemi
        dept_analysis = db.session.query(
            Department.name,
            func.count(DownloadDeniedLog.id).label('count')
        ).join(User, User.department_id == Department.id).join(
            DownloadDeniedLog, DownloadDeniedLog.user_id == User.id
        ).filter(
            DownloadDeniedLog.timestamp >= two_weeks_ago
        ).group_by(Department.name).order_by(
            func.count(DownloadDeniedLog.id).desc()
        ).limit(3).all()
        
        if dept_analysis and dept_analysis[0][1] >= 3:
            top_dept, top_count = dept_analysis[0]
            insight = InsightAI(
                insight_text=f"🏢 REPARTO CRITICO: Il reparto '{top_dept}' ha {top_count} download negati negli ultimi 14 giorni. "
                           f"Considerare formazione specifica o revisione procedure.",
                insight_type="pattern",
                severity="attenzione",
                pattern_data=json.dumps({
                    "department": top_dept,
                    "count": top_count,
                    "all_departments": [{"name": dept, "count": count} for dept, count in dept_analysis]
                })
            )
            insights.append(insight)
        
        # Salva gli insight nel database
        for insight in insights:
            # Verifica se esiste già un insight simile
            existing = InsightAI.query.filter(
                InsightAI.insight_type == insight.insight_type,
                InsightAI.status == "attivo",
                InsightAI.created_at >= datetime.utcnow() - timedelta(days=2)
            ).first()
            
            if not existing:
                db.session.add(insight)
        
        db.session.commit()
        return insights
        
    except Exception as e:
        current_app.logger.error(f"Errore generazione insight AI: {e}")
        return []

def get_ai_insights_summary():
    """
    Restituisce un riepilogo degli insight AI attivi.
    """
    try:
        active_insights = InsightAI.query.filter(
            InsightAI.status == "attivo"
        ).order_by(InsightAI.created_at.desc()).limit(5).all()
        
        summary = {
            "total_active": len(active_insights),
            "critical_count": len([i for i in active_insights if i.severity == "critico"]),
            "attention_count": len([i for i in active_insights if i.severity == "attenzione"]),
            "recent_insights": [
                {
                    "id": insight.id,
                    "text": insight.insight_text,
                    "type": insight.insight_type,
                    "severity": insight.severity,
                    "created_at": insight.created_at.strftime("%d/%m/%Y %H:%M")
                }
                for insight in active_insights
            ]
        }
        
        return summary
        
    except Exception as e:
        current_app.logger.error(f"Errore recupero insight AI: {e}")
        return {"total_active": 0, "critical_count": 0, "attention_count": 0, "recent_insights": []}

def check_download_denied_alerts():
    """
    Verifica se ci sono utenti con tentativi anomali di download negati.
    
    Returns:
        list: Lista di alert da mostrare nella dashboard.
    """
    alerts = []
    now = datetime.utcnow()
    yesterday = now - timedelta(hours=24)
    
    # Query per utenti con >3 tentativi negati in 24h
    users_with_multiple_denials = db.session.query(
        DownloadDeniedLog.user_id,
        func.count(DownloadDeniedLog.id).label('denial_count')
    ).filter(
        DownloadDeniedLog.timestamp >= yesterday
    ).group_by(DownloadDeniedLog.user_id).having(
        func.count(DownloadDeniedLog.id) > 3
    ).all()
    
    for user_id, denial_count in users_with_multiple_denials:
        user = User.query.get(user_id)
        if user:
            # Verifica se già inviato alert oggi
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            existing_alert = AdminLog.query.filter(
                AdminLog.action == "alert_download_denied",
                AdminLog.performed_by == user.email,
                AdminLog.timestamp >= today_start
            ).first()
            
            if not existing_alert:
                alerts.append({
                    'type': 'multiple_denials',
                    'user': user,
                    'count': denial_count,
                    'reason': f"Utente ha tentato {denial_count} download negati nelle ultime 24h"
                })
    
    # Query per utenti con ≥2 tentativi "firma mancante" su documenti critici
    critical_document_denials = db.session.query(
        DownloadDeniedLog.user_id,
        func.count(DownloadDeniedLog.id).label('critical_denial_count')
    ).join(Document, DownloadDeniedLog.document_id == Document.id).filter(
        DownloadDeniedLog.timestamp >= yesterday,
        DownloadDeniedLog.reason == "Firma mancante",
        Document.is_critical == True
    ).group_by(DownloadDeniedLog.user_id).having(
        func.count(DownloadDeniedLog.id) >= 2
    ).all()
    
    for user_id, critical_count in critical_document_denials:
        user = User.query.get(user_id)
        if user:
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            existing_alert = AdminLog.query.filter(
                AdminLog.action == "alert_critical_document_denied",
                AdminLog.performed_by == user.email,
                AdminLog.timestamp >= today_start
            ).first()
            
            if not existing_alert:
                alerts.append({
                    'type': 'critical_document_denials',
                    'user': user,
                    'count': critical_count,
                    'reason': f"Utente ha tentato {critical_count} download di documenti critici senza firma"
                })
    
    return alerts

def send_alert_notifications(alerts):
    """
    Invia notifiche per gli alert generati.
    
    Args:
        alerts (list): Lista di alert da notificare.
    """
    for alert in alerts:
        user = alert['user']
        
        # Log dell'alert
        admin_log = AdminLog(
            action=f"alert_{alert['type']}",
            performed_by=user.email,
            document_id=None,
            downloadable=False,
            extra_info=alert['reason']
        )
        db.session.add(admin_log)
        
        # Email agli admin (se configurata)
        try:
            admin_users = User.query.filter(User.role.in_(['admin', 'ceo'])).all()
            admin_emails = [admin.email for admin in admin_users if admin.email != user.email]
            
            if admin_emails:
                subject = f"⚠️ Alert Download Negato - {user.email}"
                body = f"""
                Attenzione! L'utente {user.email} ha generato un alert:
                
                Motivo: {alert['reason']}
                Tipo: {alert['type']}
                Conteggio: {alert['count']} tentativi
                Data: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}
                
                Verificare immediatamente la situazione.
                """
                
                msg = Message(
                    subject=subject,
                    recipients=admin_emails,
                    body=body
                )
                mail.send(msg)
                
        except Exception as e:
            current_app.logger.error(f"Errore invio email alert: {e}")
        
        # Notifica FocusMe AI (se endpoint disponibile)
        try:
            focusme_url = current_app.config.get('FOCUSME_AI_URL')
            if focusme_url:
                notification_data = {
                    'type': 'download_denied_alert',
                    'user_email': user.email,
                    'reason': alert['reason'],
                    'count': alert['count'],
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                response = requests.post(
                    f"{focusme_url}/notifications",
                    json=notification_data,
                    timeout=10
                )
                if response.status_code == 200:
                    current_app.logger.info(f"Notifica FocusMe AI inviata per {user.email}")
                    
        except Exception as e:
            current_app.logger.error(f"Errore notifica FocusMe AI: {e}")
    
    db.session.commit()

@admin_bp.route('/admin/ai_tasks')
@login_required
def ai_tasks():
    """
    Visualizza i task AI generati automaticamente.
    """
    if not (current_user.is_admin or current_user.is_ceo):
        flash("Accesso negato: solo admin e CEO.", "danger")
        return redirect(url_for('admin.admin_dashboard'))
    
    # Recupera i task AI dai log
    ai_tasks = AdminLog.query.filter(
        AdminLog.action == "ai_task_signature_request"
    ).order_by(AdminLog.timestamp.desc()).all()
    
    # Formatta i task per la visualizzazione
    formatted_tasks = []
    for task in ai_tasks:
        try:
            # Estrai informazioni dal extra_info
            extra_info = task.extra_info or ""
            if "Task creato:" in extra_info:
                title = extra_info.split("Task creato: ")[1].split(" - ")[0]
                assigned_to = extra_info.split("Assegnato a: ")[1] if "Assegnato a: " in extra_info else "N/A"
            else:
                title = "Task AI"
                assigned_to = "N/A"
            
            formatted_tasks.append({
                'id': task.id,
                'title': title,
                'assigned_to': assigned_to,
                'requested_by': task.performed_by,
                'document_id': task.document_id,
                'created_at': task.timestamp,
                'status': 'Attivo'  # Per ora tutti attivi
            })
        except Exception as e:
            current_app.logger.error(f"Errore formattazione task AI {task.id}: {e}")
    
    return render_template(
        'admin/ai_tasks.html',
        tasks=formatted_tasks
    )

@admin_bp.route('/admin/api/log_download_denied/stats')
@login_required
def api_denied_stats():
    """
    API per statistiche download negati.
    Restituisce JSON con dati per dashboard.
    """
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_ago = today_start - timedelta(days=7)
        
        # Download negati oggi
        today_count = DownloadDeniedLog.query.filter(
            DownloadDeniedLog.timestamp >= today_start
        ).count()
        
        # Download negati ieri
        yesterday_count = DownloadDeniedLog.query.filter(
            DownloadDeniedLog.timestamp >= yesterday_start,
            DownloadDeniedLog.timestamp < today_start
        ).count()
        
        # Calcola variazione percentuale
        if yesterday_count > 0:
            change_percentage = f"{((today_count - yesterday_count) / yesterday_count * 100):+.1f}%"
        else:
            change_percentage = "N/A"
        
        # Utente con più negati oggi
        top_user_query = db.session.query(
            DownloadDeniedLog.user_id,
            func.count(DownloadDeniedLog.id).label('count')
        ).filter(
            DownloadDeniedLog.timestamp >= today_start
        ).group_by(DownloadDeniedLog.user_id).order_by(
            func.count(DownloadDeniedLog.id).desc()
        ).first()
        
        top_user = {
            'count': top_user_query[1] if top_user_query else 0,
            'name': User.query.get(top_user_query[0]).email if top_user_query else 'Nessuno'
        }
        
        # Motivo più frequente oggi
        top_reason_query = db.session.query(
            DownloadDeniedLog.reason,
            func.count(DownloadDeniedLog.id).label('count')
        ).filter(
            DownloadDeniedLog.timestamp >= today_start
        ).group_by(DownloadDeniedLog.reason).order_by(
            func.count(DownloadDeniedLog.id).desc()
        ).first()
        
        top_reason = {
            'count': top_reason_query[1] if top_reason_query else 0,
            'name': top_reason_query[0] if top_reason_query else 'Nessuno'
        }
        
        # Totale settimana
        total_week = DownloadDeniedLog.query.filter(
            DownloadDeniedLog.timestamp >= week_ago
        ).count()
        
        # Dati giornalieri ultimi 7 giorni
        daily_data = []
        daily_labels = []
        for i in range(7):
            day_start = today_start - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            count = DownloadDeniedLog.query.filter(
                DownloadDeniedLog.timestamp >= day_start,
                DownloadDeniedLog.timestamp < day_end
            ).count()
            
            daily_data.append(count)
            daily_labels.append(day_start.strftime('%d/%m'))
        
        daily_data.reverse()  # Dal più vecchio al più recente
        daily_labels.reverse()
        
        # Dati distribuzione motivi settimana
        reasons_data = db.session.query(
            DownloadDeniedLog.reason,
            func.count(DownloadDeniedLog.id).label('count')
        ).filter(
            DownloadDeniedLog.timestamp >= week_ago
        ).group_by(DownloadDeniedLog.reason).order_by(
            func.count(DownloadDeniedLog.id).desc()
        ).all()
        
        reasons_labels = [reason for reason, count in reasons_data]
        reasons_values = [count for reason, count in reasons_data]
        
        # Top 5 utenti per tentativi negati settimana
        top_users_data = db.session.query(
            DownloadDeniedLog.user_id,
            func.count(DownloadDeniedLog.id).label('count')
        ).filter(
            DownloadDeniedLog.timestamp >= week_ago
        ).group_by(DownloadDeniedLog.user_id).order_by(
            func.count(DownloadDeniedLog.id).desc()
        ).limit(5).all()
        
        top_users_labels = []
        top_users_values = []
        for user_id, count in top_users_data:
            user = User.query.get(user_id)
            if user:
                top_users_labels.append(user.email)
                top_users_values.append(count)
        
        return jsonify({
            'today_count': today_count,
            'change_percentage': change_percentage,
            'top_user': top_user,
            'top_reason': top_reason,
            'total_week': total_week,
            'daily_data': {
                'labels': daily_labels,
                'values': daily_data
            },
            'reasons_data': {
                'labels': reasons_labels,
                'values': reasons_values
            },
            'top_users_data': {
                'labels': top_users_labels,
                'values': top_users_values
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore API statistiche download negati: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500

@admin_bp.route('/admin/create_test_denied_data')
@login_required
def create_test_denied_data():
    """
    Crea dati di test per le statistiche download negati.
    Solo per sviluppo/test.
    """
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        # Trova alcuni utenti e documenti esistenti
        users = User.query.limit(3).all()
        documents = Document.query.limit(5).all()
        
        if not users or not documents:
            return jsonify({'error': 'Nessun utente o documento trovato'}), 400
        
        reasons = [
            "Firma mancante",
            "Documento scaduto", 
            "Permessi insufficienti",
            "Documento protetto",
            "Validazione richiesta"
        ]
        
        # Crea dati per gli ultimi 7 giorni
        now = datetime.utcnow()
        for i in range(7):
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
            
            # Crea 2-8 record per giorno
            for j in range(2 + (i % 6)):
                user = users[j % len(users)]
                document = documents[j % len(documents)]
                reason = reasons[j % len(reasons)]
                
                # Crea timestamp casuale durante il giorno
                hour = 9 + (j * 3) % 12  # 9-21
                minute = (j * 15) % 60
                timestamp = day_start.replace(hour=hour, minute=minute)
                
                denied_log = DownloadDeniedLog(
                    user_id=user.id,
                    document_id=document.id,
                    reason=reason,
                    timestamp=timestamp,
                    ip_address=f"192.168.1.{100 + j}",
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                db.session.add(denied_log)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Creati {7 * 5} record di test per le statistiche'
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore creazione dati test: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/log_download_denied/export', methods=['POST'])
@login_required
def export_denied_stats():
    """
    Esporta statistiche download negati in CSV.
    """
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        # Log dell'esportazione
        admin_log = AdminLog(
            action="esportazione_stats_download_negati",
            performed_by=current_user.email,
            document_id=None,
            downloadable=False,
            extra_info="Esportazione statistiche download negati"
        )
        db.session.add(admin_log)
        db.session.commit()
        
        # Genera CSV con statistiche
        csv_data = StringIO()
        writer = csv.writer(csv_data, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        
        # Header
        writer.writerow([
            'Statistiche Download Negati',
            f'Esportato il: {datetime.utcnow().strftime("%d/%m/%Y %H:%M")}',
            '',
            ''
        ])
        
        # Dati giornalieri
        writer.writerow(['Giorno', 'Download Negati', 'Motivo Top', 'Utente Top'])
        
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for i in range(7):
            day_start = today_start - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            # Conteggio giornaliero
            daily_count = DownloadDeniedLog.query.filter(
                DownloadDeniedLog.timestamp >= day_start,
                DownloadDeniedLog.timestamp < day_end
            ).count()
            
            # Motivo top del giorno
            top_reason = db.session.query(
                DownloadDeniedLog.reason,
                func.count(DownloadDeniedLog.id).label('count')
            ).filter(
                DownloadDeniedLog.timestamp >= day_start,
                DownloadDeniedLog.timestamp < day_end
            ).group_by(DownloadDeniedLog.reason).order_by(
                func.count(DownloadDeniedLog.id).desc()
            ).first()
            
            # Utente top del giorno
            top_user = db.session.query(
                DownloadDeniedLog.user_id,
                func.count(DownloadDeniedLog.id).label('count')
            ).filter(
                DownloadDeniedLog.timestamp >= day_start,
                DownloadDeniedLog.timestamp < day_end
            ).group_by(DownloadDeniedLog.user_id).order_by(
                func.count(DownloadDeniedLog.id).desc()
            ).first()
            
            writer.writerow([
                day_start.strftime('%d/%m/%Y'),
                daily_count,
                top_reason[0] if top_reason else 'N/A',
                User.query.get(top_user[0]).email if top_user else 'N/A'
            ])
        
        # Footer con statistiche aggregate
        writer.writerow(['', '', '', ''])
        writer.writerow(['STATISTICHE AGGREGATE', '', '', ''])
        writer.writerow(['Totale settimana', total_week, '', ''])
        writer.writerow(['Utente con più tentativi', top_user['name'], top_user['count'], ''])
        writer.writerow(['Motivo più frequente', top_reason['name'], top_reason['count'], ''])
        
        response = Response(csv_data.getvalue(), mimetype='text/csv; charset=utf-8')
        response.headers.set("Content-Disposition", "attachment", 
                           filename=f"statistiche_download_negati_{datetime.utcnow().strftime('%Y%m%d')}.csv")
        return response
        
    except Exception as e:
        current_app.logger.error(f"Errore esportazione statistiche: {e}")
        return jsonify({'error': 'Errore interno del server'}), 500

# === ROUTE AI ASSISTANT ===
@admin_bp.route('/admin/ai_insights')
@login_required
def ai_insights():
    """
    Pagina per visualizzare e gestire gli insight AI.
    """
    if not (current_user.is_admin or current_user.is_ceo):
        flash("Accesso negato", "danger")
        return redirect(url_for('admin.dashboard'))
    
    # Genera nuovi insight
    new_insights = generate_ai_insights()
    
    # Recupera insight esistenti
    active_insights = InsightAI.query.filter(
        InsightAI.status == "attivo"
    ).order_by(InsightAI.created_at.desc()).all()
    
    resolved_insights = InsightAI.query.filter(
        InsightAI.status == "risolto"
    ).order_by(InsightAI.resolved_at.desc()).limit(10).all()
    
    return render_template('admin/ai_insights.html', 
                         active_insights=active_insights,
                         resolved_insights=resolved_insights,
                         new_insights=len(new_insights))


@admin_bp.route('/admin/api/ai_insights/generate', methods=['POST'])
@login_required
def generate_insights_api():
    """
    API per generare nuovi insight AI.
    """
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        insights = generate_ai_insights()
        return jsonify({
            'success': True,
            'insights_generated': len(insights),
            'message': f'Generati {len(insights)} nuovi insight AI'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/ai_insights/summary')
@login_required
def ai_insights_summary():
    """
    API per ottenere il riepilogo degli insight AI.
    """
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        summary = get_ai_insights_summary()
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/ai_insights/<int:insight_id>/resolve', methods=['POST'])
@login_required
def resolve_insight(insight_id):
    """
    Marca un insight come risolto.
    """
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        insight = InsightAI.query.get_or_404(insight_id)
        insight.status = "risolto"
        insight.resolved_at = datetime.utcnow()
        insight.resolved_by = current_user.email
        
        # Log dell'azione
        admin_log = AdminLog(
            action="risoluzione_insight_ai",
            performed_by=current_user.email,
            extra_info=f"Insight ID: {insight_id}, Tipo: {insight.insight_type}"
        )
        db.session.add(admin_log)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Insight risolto con successo'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/api/ai_insights/<int:insight_id>/ignore', methods=['POST'])
@login_required
def ignore_insight(insight_id):
    """
    Ignora un insight (lo marca come risolto senza azione).
    """
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        insight = InsightAI.query.get_or_404(insight_id)
        insight.status = "ignorato"
        insight.resolved_at = datetime.utcnow()
        insight.resolved_by = current_user.email
        insight.action_taken = "Ignorato dall'amministratore"
        
        # Log dell'azione
        admin_log = AdminLog(
            action="ignoramento_insight_ai",
            performed_by=current_user.email,
            extra_info=f"Insight ID: {insight_id}, Tipo: {insight.insight_type}"
        )
        db.session.add(admin_log)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Insight ignorato'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


def trasforma_insight_in_task(insight_id):
    """
    Trasforma un insight AI in un task operativo.
    
    Args:
        insight_id (int): ID dell'insight da trasformare
        
    Returns:
        int: ID del task creato, None se errore
    """
    try:
        insight = InsightAI.query.get(insight_id)
        if not insight:
            return None
            
        if insight.trasformato_in_task:
            return insight.task_id  # Già trasformato
        
        # Determina la priorità basata sulla severità
        priorita_map = {
            "critico": "Alta",
            "attenzione": "Media", 
            "informativo": "Bassa"
        }
        priorita = priorita_map.get(insight.severity, "Media")
        
        # Crea il titolo del task
        titolo = f"AI: {insight.insight_type.capitalize()} - {insight.severity.capitalize()}"
        
        # Crea la descrizione
        descrizione = f"🔍 Insight AI: {insight.insight_text}\n\n"
        descrizione += f"📊 Tipo: {insight.insight_type}\n"
        descrizione += f"⚠️ Severità: {insight.severity}\n"
        descrizione += f"📅 Creato il: {insight.created_at.strftime('%d/%m/%Y %H:%M')}\n"
        
        if insight.pattern_data:
            descrizione += f"\n📈 Dati Pattern:\n{insight.pattern_data}"
        
        # Crea il task
        nuovo_task = Task(
            titolo=titolo,
            descrizione=descrizione,
            priorita=priorita,
            assegnato_a="admin@example.com",  # Default, può essere migliorato
            stato="Da fare",
            scadenza=datetime.utcnow() + timedelta(days=7),  # Scadenza 7 giorni
            created_by=current_user.email,
            insight_id=insight.id
        )
        
        db.session.add(nuovo_task)
        db.session.flush()  # Ottieni l'ID del task
        
        # Aggiorna l'insight
        insight.task_id = nuovo_task.id
        insight.trasformato_in_task = True
        insight.action_taken = f"Trasformato in task ID: {nuovo_task.id}"
        
        # Log dell'azione
        admin_log = AdminLog(
            action="trasformazione_insight_in_task",
            performed_by=current_user.email,
            extra_info=f"Insight ID: {insight_id} -> Task ID: {nuovo_task.id}"
        )
        db.session.add(admin_log)
        
        db.session.commit()
        
        return nuovo_task.id
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore trasformazione insight in task: {e}")
        return None


@admin_bp.route('/admin/api/ai_insights/<int:insight_id>/task', methods=['POST'])
@login_required
def api_trasforma_insight_in_task(insight_id):
    """
    API endpoint per trasformare un insight in task.
    """
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    task_id = trasforma_insight_in_task(insight_id)
    
    if task_id:
        return jsonify({
            'success': True, 
            'task_id': task_id,
            'message': f'Insight trasformato in task ID: {task_id}'
        })
    else:
        return jsonify({
            'success': False, 
            'error': 'Errore nella trasformazione dell\'insight in task'
        }), 400


@admin_bp.route('/admin/create_test_ai_data')
@login_required
def create_test_ai_data():
    """
    Crea dati di test specifici per l'AI Assistant.
    """
    if not (current_user.is_admin or current_user.is_ceo):
        return jsonify({'error': 'Accesso negato'}), 403
    
    try:
        # Ottieni utenti e documenti esistenti
        users = User.query.limit(5).all()
        documents = Document.query.limit(5).all()
        
        if not users or not documents:
            flash("❌ Errore: Necessari almeno 1 utente e 1 documento", "danger")
            return redirect(url_for('admin.stats'))
        
        # Pulisci dati esistenti per test pulito
        DownloadDeniedLog.query.delete()
        InsightAI.query.filter(InsightAI.status == "attivo").delete()
        db.session.commit()
        
        # 1. Simulazione: utente critico con 6 download negati
        critical_user = users[0]
        critical_doc = documents[0]
        
        for i in range(6):
            log = DownloadDeniedLog(
                user_id=critical_user.id,
                document_id=critical_doc.id,
                reason="Firma mancante",
                ip_address="192.168.1.100",
                user_agent="TestAgent/1.0",
                timestamp=datetime.utcnow() - timedelta(days=i)
            )
            db.session.add(log)
        
        # 2. Simulazione: reparto problematico (stesso utente, documenti diversi)
        for i in range(4):
            doc = documents[i % len(documents)]
            log = DownloadDeniedLog(
                user_id=critical_user.id,
                document_id=doc.id,
                reason="Accesso scaduto",
                ip_address="192.168.1.101",
                user_agent="TestAgent/1.0",
                timestamp=datetime.utcnow() - timedelta(days=1)
            )
            db.session.add(log)
        
        # 3. Simulazione: altri utenti con problemi minori
        for i, user in enumerate(users[1:3]):
            for j in range(2):
                doc = documents[j % len(documents)]
                log = DownloadDeniedLog(
                    user_id=user.id,
                    document_id=doc.id,
                    reason="Permessi insufficienti",
                    ip_address=f"192.168.1.{102 + i}",
                    user_agent="TestAgent/1.0",
                    timestamp=datetime.utcnow() - timedelta(days=j)
                )
                db.session.add(log)
        
        # 4. Simulazione: documento critico con firma mancante
        if len(documents) > 1:
            critical_doc2 = documents[1]
            # Marca come documento critico
            critical_doc2.is_critical = True
            critical_doc2.richiedi_firma = True
            
            for i in range(3):
                log = DownloadDeniedLog(
                    user_id=users[0].id,
                    document_id=critical_doc2.id,
                    reason="Firma mancante",
                    ip_address="192.168.1.105",
                    user_agent="TestAgent/1.0",
                    timestamp=datetime.utcnow() - timedelta(days=i)
                )
                db.session.add(log)
        
        db.session.commit()
        
        # Log dell'azione
        admin_log = AdminLog(
            action="creazione_dati_test_ai",
            performed_by=current_user.email,
            extra_info="Creati dati di test per AI Assistant"
        )
        db.session.add(admin_log)
        db.session.commit()
        
        flash("✅ Dati di test AI creati con successo! Ora puoi testare l'AI Assistant.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Errore creazione dati di test AI: {e}", "danger")
    
    return redirect(url_for('admin.stats'))

# === Route per firma digitale interna ===
@admin_bp.route('/documents/<int:doc_id>/sign', methods=['POST'])
@login_required
def sign_document(doc_id):
    if not current_user.is_admin:
        return "Accesso negato", 403

    document = Document.query.get_or_404(doc_id)
    if document.stato_approvazione != "approvato":
        flash("❌ Solo i documenti approvati possono essere firmati.", "danger")
        return redirect(url_for('admin.documents_overview'))

    document.is_signed = True
    document.signed_at = datetime.utcnow()
    document.signed_by = current_user.username
    document.firma_commento = request.form.get("firma_commento", "")
    db.session.commit()

    # Log dell'azione
    log = AdminLog(
        action="Firma documento",
        performed_by=current_user.email,
        document_id=document.id,
        extra_info=f"Firmato da {current_user.username} con commento: {document.firma_commento}"
    )
    db.session.add(log)
    db.session.commit()

    flash("✅ Documento firmato con successo.", "success")
    return redirect(url_for('admin.documents_overview'))

# === Route per log firme documenti ===
@admin_bp.route("/firme")
@login_required
def firme_documenti():
    if not current_user.is_admin:
        return "Accesso negato", 403

    firmati = Document.query.filter_by(is_signed=True).order_by(Document.signed_at.desc()).all()
    
    # Calcola le date per le statistiche
    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    return render_template("admin/firme.html", 
                         firmati=firmati,
                         today=today,
                         week_ago=week_ago)

# === Route per esportazione CSV log firme ===
@admin_bp.route("/firme/export")
@login_required
def export_firme_csv():
    """
    Esporta le firme gerarchiche in formato CSV per audit.
    """
    try:
        # Query tutte le firme con relazioni
        firme = FirmaDocumento.query.join(Document).join(User).all()
        
        # Crea CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'ID Firma', 'Documento', 'Utente', 'Data Firma Utente', 'Nome Firma',
            'Firma Admin', 'Data Firma Admin', 'Approvato CEO', 'Data Firma CEO',
            'Stato Completo', 'IP Address', 'User Agent'
        ])
        
        # Dati
        for firma in firme:
            writer.writerow([
                firma.id,
                firma.document.title if firma.document else 'N/A',
                firma.user.full_name if firma.user else 'N/A',
                firma.data_firma.strftime('%Y-%m-%d %H:%M:%S') if firma.data_firma else 'N/A',
                firma.nome_firma,
                'Sì' if firma.firma_admin else 'No',
                firma.data_firma_admin.strftime('%Y-%m-%d %H:%M:%S') if firma.data_firma_admin else 'N/A',
                'Sì' if firma.approvato_dal_ceo else 'No',
                firma.data_firma_ceo.strftime('%Y-%m-%d %H:%M:%S') if firma.data_firma_ceo else 'N/A',
                firma.stato_firma_display,
                firma.ip or 'N/A',
                firma.user_agent or 'N/A'
            ])
        
        # Log dell'esportazione
        log_admin_action(
            f"Esportazione firme gerarchiche: {len(firme)} record",
            current_user.email,
            "CSV per audit"
        )
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=firme_gerarchiche_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore esportazione firme CSV: {e}")
        flash("❌ Errore durante l'esportazione delle firme.", "danger")
        return redirect(url_for('admin.firme_documenti'))

# === Route per firma automatica AI ===
@admin_bp.route("/firme/auto-sign", methods=['POST'])
@login_required
def execute_auto_sign():
    if not current_user.is_admin:
        return "Accesso negato", 403
    
    try:
        from tasks.auto_sign import firma_automatica_ai
        firme_eseguite = firma_automatica_ai()
        
        flash(f"🤖 Firma automatica AI completata: {firme_eseguite} documenti firmati", "success")
        
        # Log dell'azione
        log = AdminLog(
            action="Esecuzione firma automatica AI",
            performed_by=current_user.email,
            extra_info=f"Firmati automaticamente {firme_eseguite} documenti"
        )
        db.session.add(log)
        db.session.commit()
        
    except Exception as e:
        flash(f"❌ Errore durante la firma automatica: {str(e)}", "danger")
    
    return redirect(url_for('admin.firme_documenti'))

# === Route per suggerimenti AI ===
@admin_bp.route("/suggerimenti-ai")
@login_required
@admin_required
def suggerimenti_ai():
    """
    Pagina principale per i suggerimenti AI.
    
    Returns:
        Template con dashboard suggerimenti AI
    """
    try:
        # Statistiche AI
        stats = {
            'total_suggestions': 15,  # Placeholder
            'resolved_suggestions': 8,
            'pending_suggestions': 7,
            'accuracy': 85
        }
        
        # Dati utenti per analisi
        users = []
        all_users = User.query.all()
        
        for user in all_users:
            # Simula dati corsi (in produzione verrebbero dal database)
            corsi_completati = [
                "Sicurezza Alimentare",
                "Gestione Qualità",
                "Formazione Base"
            ] if user.id % 2 == 0 else ["Formazione Base"]
            
            corsi_mancanti = [
                "Gestione Danni",
                "Compliance GDPR"
            ] if user.id % 3 == 0 else []
            
            progresso_percentuale = 75 if user.id % 2 == 0 else 25
            
            users.append({
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': user.role,
                'corsi_completati': corsi_completati,
                'corsi_mancanti': corsi_mancanti,
                'progresso_percentuale': progresso_percentuale,
                'tag_ai': 'Formazione Avanzata' if user.id % 2 == 0 else 'Formazione Base'
            })
        
        # Suggerimenti esistenti (placeholder)
        suggerimenti = [
            {
                'titolo': 'Formazione Sicurezza Alimentare',
                'descrizione': 'Il 60% degli utenti non ha completato il corso di sicurezza alimentare.',
                'stato': 'in_corso',
                'data_creazione': datetime.utcnow() - timedelta(days=2),
                'azioni': [
                    'Inviare reminder email agli utenti',
                    'Programmare sessione di formazione',
                    'Monitorare progresso settimanale'
                ]
            },
            {
                'titolo': 'Compliance GDPR',
                'descrizione': 'Aggiornamento necessario per la compliance GDPR.',
                'stato': 'risolto',
                'data_creazione': datetime.utcnow() - timedelta(days=5),
                'azioni': [
                    'Corso completato da tutti gli utenti',
                    'Documentazione aggiornata'
                ]
            }
        ]
        
        return render_template("admin/suggerimenti_ai.html",
                             stats=stats,
                             users=users,
                             suggerimenti=suggerimenti)
                             
    except Exception as e:
        current_app.logger.error(f"Errore pagina suggerimenti AI: {e}")
        flash(f"❌ Errore nel caricamento della pagina: {str(e)}", "danger")
        return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route("/suggerimenti-ai/gpt", methods=["POST"])
@login_required
@admin_required
def genera_suggerimenti_gpt():
    """
    Genera suggerimenti GPT basati sui dati utenti.
    
    Returns:
        JSON con suggerimenti generati
    """
    try:
        data = request.get_json()
        utenti = data.get('utenti', [])
        
        if not utenti:
            return jsonify({
                'success': False,
                'error': 'Nessun dato utente fornito'
            }), 400
        
        # Analizza i dati utenti
        totale_utenti = len(utenti)
        utenti_con_corsi_mancanti = sum(1 for u in utenti if u.get('mancanti'))
        progresso_medio = sum(u.get('progresso', 0) for u in utenti) / totale_utenti if totale_utenti > 0 else 0
        
        # Genera suggerimenti basati sui dati
        suggerimenti = []
        
        if progresso_medio < 50:
            suggerimenti.append("⚠️ PROGRESSO FORMAZIONE BASSO")
            suggerimenti.append(f"• Il progresso medio è del {progresso_medio:.1f}%")
            suggerimenti.append("• Suggerimento: Implementare programma di formazione intensivo")
            suggerimenti.append("• Azioni: Sessione di formazione obbligatoria settimanale")
            suggerimenti.append("")
        
        if utenti_con_corsi_mancanti > 0:
            suggerimenti.append("📚 CORSI MANCANTI")
            suggerimenti.append(f"• {utenti_con_corsi_mancanti} utenti hanno corsi incompleti")
            suggerimenti.append("• Corsi più mancanti:")
            
            # Analizza corsi mancanti
            corsi_mancanti_count = {}
            for utente in utenti:
                for corso in utente.get('mancanti', []):
                    corsi_mancanti_count[corso] = corsi_mancanti_count.get(corso, 0) + 1
            
            for corso, count in sorted(corsi_mancanti_count.items(), key=lambda x: x[1], reverse=True)[:3]:
                suggerimenti.append(f"  - {corso}: {count} utenti")
            
            suggerimenti.append("")
        
        # Suggerimenti personalizzati per utenti specifici
        utenti_bassa_performance = [u for u in utenti if u.get('progresso', 0) < 30]
        if utenti_bassa_performance:
            suggerimenti.append("🎯 UTENTI A RISCHIO")
            suggerimenti.append("• Utenti con progresso < 30%:")
            for utente in utenti_bassa_performance[:3]:
                suggerimenti.append(f"  - {utente['nome']} {utente['cognome']}: {utente['progresso']}%")
            suggerimenti.append("• Azione: Contatto diretto e supporto personalizzato")
            suggerimenti.append("")
        
        # Suggerimenti generali
        suggerimenti.append("💡 SUGGERIMENTI GENERALI")
        suggerimenti.append("• Implementare sistema di gamification")
        suggerimenti.append("• Creare badge per completamento corsi")
        suggerimenti.append("• Organizzare sessioni di formazione di gruppo")
        suggerimenti.append("• Monitorare progresso settimanale")
        suggerimenti.append("")
        suggerimenti.append("📊 STATISTICHE RIEVATE")
        suggerimenti.append(f"• Totale utenti analizzati: {totale_utenti}")
        suggerimenti.append(f"• Progresso medio: {progresso_medio:.1f}%")
        suggerimenti.append(f"• Utenti con corsi mancanti: {utenti_con_corsi_mancanti}")
        suggerimenti.append(f"• Percentuale compliance: {((totale_utenti - utenti_con_corsi_mancanti) / totale_utenti * 100):.1f}%")
        
        # Log dell'azione
        log_admin_action(
            f"Generazione suggerimenti GPT per {totale_utenti} utenti",
            current_user.email,
            f"Progresso medio: {progresso_medio:.1f}%"
        )
        
        return jsonify({
            'success': True,
            'suggerimenti': '\n'.join(suggerimenti),
            'stats': {
                'totale_utenti': totale_utenti,
                'progresso_medio': progresso_medio,
                'utenti_con_corsi_mancanti': utenti_con_corsi_mancanti
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore generazione suggerimenti GPT: {e}")
        return jsonify({
            'success': False,
            'error': f"Errore durante la generazione: {str(e)}"
        }), 500


@admin_bp.route("/api/suggerimenti-ai/stats")
@login_required
@admin_required
def api_suggerimenti_ai_stats():
    """
    API per statistiche suggerimenti AI.
    
    Returns:
        JSON con statistiche aggiornate
    """
    try:
        # Statistiche in tempo reale (placeholder)
        stats = {
            'total_suggestions': 15,
            'resolved_suggestions': 8,
            'pending_suggestions': 7,
            'accuracy': 85
        }
        
        return jsonify(stats)
        
    except Exception as e:
        current_app.logger.error(f"Errore API stats suggerimenti AI: {e}")
        return jsonify({
            'total_suggestions': 0,
            'resolved_suggestions': 0,
            'pending_suggestions': 0,
            'accuracy': 0
        }), 500


@admin_bp.route("/documents/<int:doc_id>/ai-suggestions")
@login_required
def get_ai_suggestions(doc_id):
    if not current_user.is_admin:
        return "Accesso negato", 403
    
    document = Document.query.get_or_404(doc_id)
    
    try:
        from tasks.auto_sign import suggerisci_firma_ai
        suggestion = suggerisci_firma_ai(document)
        
        return jsonify({
            'suggestion': suggestion,
            'eligible_for_auto_sign': bool(suggestion)
        })
        
    except Exception as e:
        return jsonify({
            'suggestion': "",
            'eligible_for_auto_sign': False,
            'error': str(e)
        }), 500

# === Route per statistiche firme AI ===
@admin_bp.route("/firme/ai-stats")
@login_required
def get_ai_sign_stats():
    if not current_user.is_admin:
        return "Accesso negato", 403
    
    try:
        from tasks.auto_sign import get_auto_sign_stats
        stats = get_auto_sign_stats()
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({
            'total_ai_signed': 0,
            'today_ai_signed': 0,
            'ai_sign_percentage': 0,
            'error': str(e)
        }), 500

# === Route per statistiche approvazioni documenti ===
@admin_bp.route("/approval-stats")
@login_required
def approval_stats():
    if not current_user.is_admin:
        return "Accesso negato", 403
    
    now = datetime.utcnow()
    
    # Query documenti per stato
    approvati = Document.query.filter(
        Document.stato_approvazione == "approvato", 
        Document.data_approvazione != None
    ).all()
    
    in_attesa = Document.query.filter(
        Document.stato_approvazione == "in_attesa"
    ).all()
    
    respinti = Document.query.filter(
        Document.stato_approvazione == "respinto"
    ).all()
    
    # Calcolo tempo medio di approvazione
    tempo_totale = 0
    count_approvati = 0
    for doc in approvati:
        if doc.data_approvazione and doc.created_at:
            tempo_totale += (doc.data_approvazione - doc.created_at).total_seconds()
            count_approvati += 1
    
    tempo_medio = round(tempo_totale / count_approvati / 3600, 2) if count_approvati > 0 else 0
    
    # Calcolo approvazioni per giorno
    from collections import defaultdict
    approvazioni_per_giorno = defaultdict(int)
    for doc in approvati:
        if doc.data_approvazione:
            giorno = doc.data_approvazione.strftime('%Y-%m-%d')
            approvazioni_per_giorno[giorno] += 1
    
    approvazioni_per_giorno = dict(sorted(approvazioni_per_giorno.items()))
    
    # Calcolo media per utente
    media_utenti = defaultdict(list)
    for doc in approvati:
        if doc.data_approvazione and doc.created_at and doc.approvato_da:
            ore = (doc.data_approvazione - doc.created_at).total_seconds() / 3600
            media_utenti[doc.approvato_da].append(ore)
    
    # Calcolo media ore per utente
    for user in media_utenti:
        media_utenti[user] = round(sum(media_utenti[user]) / len(media_utenti[user]), 2)
    
    # Identificazione ritardi
    ritardi = []
    for doc in in_attesa:
        if doc.created_at and (now - doc.created_at).days > 3:
            ritardi.append(doc)
    
    # Insight AI
    insight_ai = []
    
    if tempo_medio > 24:
        insight_ai.append("⏱️ Il tempo medio di approvazione supera 24 ore. Possibili colli di bottiglia.")
    
    for user, ore in media_utenti.items():
        if ore > 48:
            insight_ai.append(f"🐢 L'utente {user} approva in media dopo {ore} ore.")
    
    if len(ritardi) > 5:
        insight_ai.append(f"⚠️ Ci sono {len(ritardi)} documenti in attesa da oltre 3 giorni.")
    
    if len(in_attesa) > len(approvati) * 0.3:
        insight_ai.append(f"📊 Il {round(len(in_attesa) / (len(approvati) + len(in_attesa)) * 100, 1)}% dei documenti è in attesa di approvazione.")
    
    if not insight_ai:
        insight_ai.append("✅ Nessuna anomalia rilevata nel processo di approvazione.")
    
    return render_template("admin/approval_stats.html",
                         approvati=approvati,
                         in_attesa=in_attesa,
                         respinti=respinti,
                         tempo_medio=tempo_medio,
                         approvazioni_per_giorno=approvazioni_per_giorno,
                         media_utenti=media_utenti,
                         ritardi=ritardi,
                         insight_ai=insight_ai)

# === Route per panoramica documentale cross-azienda ===
@admin_bp.route("/doc-overview")
@login_required
def doc_overview():
    if not current_user.is_admin:
        return "Accesso negato", 403

    # === FILTRI AI DOCUMENT INTELLIGENCE ===
    ai_status = request.args.get("ai_status")
    ai_explain = request.args.get("ai_explain")
    
    # Query base per documenti
    query = Document.query

    # Applica filtri AI se specificati
    if ai_status:
        query = query.filter(Document.ai_status == ai_status)
    
    if ai_explain:
        query = query.filter(Document.ai_explain.ilike(f"%{ai_explain}%"))

    # === BOX RIEPILOGO ===
    totale_documenti = Document.query.count()
    approvati = Document.query.filter_by(stato_approvazione='approvato').count()
    in_attesa = Document.query.filter_by(stato_approvazione='in_attesa').count()
    firmati = Document.query.filter_by(is_signed=True).count()

    # === REVISIONI FREQUENTI ===
    from sqlalchemy import func
    revisioni_freq = (
        db.session.query(DocumentVersion.document_id, func.count().label("num"))
        .group_by(DocumentVersion.document_id)
        .having(func.count() > 3)
        .all()
    )

    documenti_revisionati = len(revisioni_freq)

    # === DOWNLOAD TOTALI (AdminLog) ===
    total_downloads = AdminLog.query.filter(AdminLog.action == 'download').count()

    # === FASE 2: AGGREGAZIONE DATI PER GRAFICI ===
    from collections import defaultdict

    # Upload per azienda
    upload_per_azienda = defaultdict(int)
    documents = Document.query.all()
    for doc in documents:
        if hasattr(doc, 'company') and doc.company:
            company_name = doc.company.name if hasattr(doc.company, 'name') else str(doc.company)
            upload_per_azienda[company_name] += 1
        elif hasattr(doc, 'company_name') and doc.company_name:
            upload_per_azienda[doc.company_name] += 1

    # Download per azienda (AdminLog)
    download_per_azienda = defaultdict(int)
    logs = AdminLog.query.filter_by(action='download').all()
    for log in logs:
        if hasattr(log, 'document') and log.document:
            if hasattr(log.document, 'company') and log.document.company:
                company_name = log.document.company.name if hasattr(log.document.company, 'name') else str(log.document.company)
                download_per_azienda[company_name] += 1
            elif hasattr(log.document, 'company_name') and log.document.company_name:
                download_per_azienda[log.document.company_name] += 1

    # Stato documenti
    stato_documenti = {
        "approvato": Document.query.filter_by(stato_approvazione="approvato").count(),
        "in_attesa": Document.query.filter_by(stato_approvazione="in_attesa").count(),
        "respinto": Document.query.filter_by(stato_approvazione="respinto").count(),
        "bozza": Document.query.filter_by(stato_approvazione="bozza").count()
    }

    # Attività per reparto
    attivita_reparto = defaultdict(int)
    for doc in documents:
        if hasattr(doc, 'department') and doc.department:
            dept_name = doc.department.name if hasattr(doc.department, 'name') else str(doc.department)
            attivita_reparto[dept_name] += 1
        elif hasattr(doc, 'department_name') and doc.department_name:
            attivita_reparto[doc.department_name] += 1

    # === FASE 3: INSIGHT AI STRATEGICI ===
    insight_ai = generate_document_insights()

    # === FASE 4: TABELLA DOCUMENTI PER AZIENDA/REPARTO ===
    # Carica documenti con filtri applicati
    documenti_tabella = query.order_by(Document.created_at.desc()).all()

    return render_template("admin/doc_overview.html",
        totale_documenti=totale_documenti,
        approvati=approvati,
        in_attesa=in_attesa,
        firmati=firmati,
        revisioni_frequenti=documenti_revisionati,
        total_downloads=total_downloads,
        upload_per_azienda=dict(upload_per_azienda),
        download_per_azienda=dict(download_per_azienda),
        stato_documenti=stato_documenti,
        attivita_reparto=dict(attivita_reparto),
        insight_ai=insight_ai,
        documenti_tabella=documenti_tabella,
        ai_status=ai_status,
        ai_explain=ai_explain
    )

@admin_bp.route('/admin/approval_history')
@login_required
def approval_history():
    """
    Pagina per visualizzare lo storico delle approvazioni documenti.
    
    Returns:
        str: Template HTML con lo storico approvazioni.
    """
    if not current_user.is_admin and not current_user.is_ceo:
        flash('Accesso negato. Solo admin e CEO possono visualizzare lo storico approvazioni.', 'danger')
        return redirect(url_for('admin.dashboard'))

    # === Filtri dalla query string ===
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    approver_id = request.args.get('approver_id')
    action_type = request.args.get('action')
    method_type = request.args.get('method')
    document_id = request.args.get('document_id')

    # === Query base ===
    query = DocumentApprovalLog.query.join(Document).join(User, DocumentApprovalLog.approver_id == User.id)

    # === Applica filtri ===
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(DocumentApprovalLog.timestamp >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(DocumentApprovalLog.timestamp <= end_dt)
        except ValueError:
            pass

    if approver_id:
        query = query.filter(DocumentApprovalLog.approver_id == approver_id)

    if action_type:
        query = query.filter(DocumentApprovalLog.action == action_type)

    if method_type:
        query = query.filter(DocumentApprovalLog.method == method_type)

    if document_id:
        query = query.filter(DocumentApprovalLog.document_id == document_id)

    # === Ordinamento e paginazione ===
    logs = query.order_by(DocumentApprovalLog.timestamp.desc()).all()

    # === Dati per filtri ===
    approvers = User.query.filter(User.role.in_(['admin', 'ceo'])).all()
    documents = Document.query.all()
    actions = ['approved', 'rejected', 'commented', 'submitted', 'auto_approved']
    methods = ['manual', 'AI', 'auto']

    # === Statistiche ===
    total_logs = len(logs)
    approved_count = len([log for log in logs if log.action == 'approved'])
    rejected_count = len([log for log in logs if log.action == 'rejected'])
    ai_count = len([log for log in logs if log.is_ai_approval])

    # === Top approvers ===
    approver_stats = {}
    for log in logs:
        approver_name = log.approver_display
        if approver_name not in approver_stats:
            approver_stats[approver_name] = 0
        approver_stats[approver_name] += 1

    top_approver = max(approver_stats.items(), key=lambda x: x[1]) if approver_stats else ("Nessuno", 0)

    return render_template("admin/approval_history.html",
        logs=logs,
        approvers=approvers,
        documents=documents,
        actions=actions,
        methods=methods,
        total_logs=total_logs,
        approved_count=approved_count,
        rejected_count=rejected_count,
        ai_count=ai_count,
        top_approver=top_approver,
        filters={
            'start_date': start_date,
            'end_date': end_date,
            'approver_id': approver_id,
            'action': action_type,
            'method': method_type,
            'document_id': document_id
        }
    )

@admin_bp.route('/admin/approval_history/export')
@login_required
def export_approval_history():
    """
    Esporta lo storico approvazioni in formato CSV.
    
    Returns:
        Response: File CSV con lo storico approvazioni.
    """
    if not current_user.is_admin and not current_user.is_ceo:
        flash('Accesso negato. Solo admin e CEO possono esportare lo storico approvazioni.', 'danger')
        return redirect(url_for('admin.dashboard'))

    # === Applica gli stessi filtri della route principale ===
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    approver_id = request.args.get('approver_id')
    action_type = request.args.get('action')
    method_type = request.args.get('method')
    document_id = request.args.get('document_id')

    query = DocumentApprovalLog.query.join(Document).join(User, DocumentApprovalLog.approver_id == User.id)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(DocumentApprovalLog.timestamp >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(DocumentApprovalLog.timestamp <= end_dt)
        except ValueError:
            pass

    if approver_id:
        query = query.filter(DocumentApprovalLog.approver_id == approver_id)

    if action_type:
        query = query.filter(DocumentApprovalLog.action == action_type)

    if method_type:
        query = query.filter(DocumentApprovalLog.method == method_type)

    if document_id:
        query = query.filter(DocumentApprovalLog.document_id == document_id)

    logs = query.order_by(DocumentApprovalLog.timestamp.desc()).all()

    # === Genera CSV ===
    output = StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # === Intestazioni ===
    writer.writerow([
        'Data/Ora',
        'Documento',
        'Azione',
        'Approvatore',
        'Ruolo Approvatore',
        'Metodo',
        'Note',
        'ID Documento',
        'ID Approvatore'
    ])

    # === Dati ===
    for log in logs:
        writer.writerow([
            log.timestamp.strftime('%d/%m/%Y %H:%M:%S'),
            log.document_title,
            log.action_display,
            log.approver_display,
            log.approver_role,
            log.method_display,
            log.note or '',
            log.document_id,
            log.approver_id
        ])

    # === Log dell'esportazione ===
    log_admin_action(
        "Esportazione storico approvazioni CSV",
        current_user.email,
        f"Filtri applicati: {len(logs)} record esportati"
    )

    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'storico_approvazioni_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

# === Funzione per generare insight AI strategici ===
def generate_document_insights():
    """Genera insight AI strategici basati sui dati documentali"""
    insights = []
    
    try:
        # Documenti con più di 5 revisioni
        from sqlalchemy import func
        revisioni_frequenti = (
            db.session.query(DocumentVersion.document_id, func.count().label("num"))
            .group_by(DocumentVersion.document_id)
            .having(func.count() > 5)
            .all()
        )
        
        for doc_id, num in revisioni_frequenti:
            doc = Document.query.get(doc_id)
            if doc:
                insights.append(f"🔁 Il documento \"{doc.title}\" ha {num} revisioni: valutare semplificazione del processo.")

        # Documenti in attesa da più di 3 giorni
        now = datetime.utcnow()
        in_attesa = Document.query.filter_by(stato_approvazione='in_attesa').all()
        ritardi = [d for d in in_attesa if d.created_at and (now - d.created_at).days > 3]
        
        if ritardi:
            insights.append(f"⚠️ {len(ritardi)} documenti sono in attesa da oltre 3 giorni: monitorare il flusso approvativo.")

        # Documenti più scaricati
        download_counter = defaultdict(int)
        logs = AdminLog.query.filter_by(action="download").all()
        for log in logs:
            if hasattr(log, 'document_id') and log.document_id:
                download_counter[log.document_id] += 1

        top_docs = sorted(download_counter.items(), key=lambda x: x[1], reverse=True)[:3]
        for doc_id, count in top_docs:
            doc = Document.query.get(doc_id)
            if doc and count > 20:
                insights.append(f"📥 Il documento \"{doc.title}\" ha ricevuto {count} download: considerare link rapido o accesso semplificato.")

        # Analisi percentuali
        totale_docs = Document.query.count()
        if totale_docs > 0:
            percentuale_approvati = (Document.query.filter_by(stato_approvazione='approvato').count() / totale_docs) * 100
            if percentuale_approvati < 70:
                insights.append(f"📊 Solo il {percentuale_approvati:.1f}% dei documenti è approvato: ottimizzare il processo di approvazione.")

            percentuale_firmati = (Document.query.filter_by(is_signed=True).count() / totale_docs) * 100
            if percentuale_firmati < 60:
                insights.append(f"🖋️ Solo il {percentuale_firmati:.1f}% dei documenti è firmato: accelerare il processo di firma digitale.")

        # Analisi aziende
        if len(upload_per_azienda) > 1:
            azienda_piu_attiva = max(upload_per_azienda.items(), key=lambda x: x[1])
            insights.append(f"🏢 L'azienda \"{azienda_piu_attiva[0]}\" è la più attiva con {azienda_piu_attiva[1]} documenti: considerare best practices.")

        # Se non ci sono insight, aggiungi un messaggio positivo
        if not insights:
            insights.append("✅ Nessuna criticità rilevata: il sistema documentale funziona correttamente.")

    except Exception as e:
        insights.append(f"⚠️ Errore nell'analisi AI: {str(e)}")

    return insights

@admin_bp.route('/admin/documents/<int:doc_id>/approvals')
@login_required
def document_approval_flow(doc_id):
    if not current_user.is_admin and not current_user.is_ceo:
        abort(403)

    document = Document.query.get_or_404(doc_id)
    approval_steps = ApprovalStep.query.filter_by(document_id=doc_id).order_by(ApprovalStep.id).all()

    # Calcola statistiche
    total_steps = len(approval_steps)
    completed_steps = len([s for s in approval_steps if s.status == 'approved'])
    pending_steps = len([s for s in approval_steps if s.status == 'pending'])
    rejected_steps = len([s for s in approval_steps if s.status == 'rejected'])
    
    progress_percentage = (completed_steps / total_steps * 100) if total_steps > 0 else 0

    # Ottieni approvatori disponibili
    available_approvers = User.query.filter(User.role.in_(['admin', 'manager', 'ceo'])).all()

    return render_template("admin/document_approval_flow.html",
                           document=document,
                           approval_steps=approval_steps,
                           total_steps=total_steps,
                           completed_steps=completed_steps,
                           pending_steps=pending_steps,
                           rejected_steps=rejected_steps,
                           progress_percentage=progress_percentage,
                           available_approvers=available_approvers)

@admin_bp.route('/documents/<int:doc_id>/approvals', methods=['GET'])
@login_required
def document_approvals(doc_id):
    """
    Visualizza la checklist di approvazione con visibilità per ruolo.
    
    Args:
        doc_id (int): ID del documento
        
    Returns:
        Response: Template con checklist filtrata per ruolo
    """
    document = Document.query.get_or_404(doc_id)
    approval_steps = ApprovalStep.query.filter_by(document_id=doc_id).order_by(ApprovalStep.id).all()
    
    # === Individua lo step attivo (primo pending) ===
    active_step = next((s for s in approval_steps if s.status == 'pending'), None)
    
    # === Flag di visibilità logica per ogni step ===
    for step in approval_steps:
        step.is_active = (step == active_step)
        step.can_take_action = step.is_active and (
            current_user.role == step.approver_role or current_user.is_admin
        )
        step.is_future_step = (
            step.status == 'pending' and 
            step != active_step and 
            approval_steps.index(step) > approval_steps.index(active_step) if active_step else False
        )
        step.is_past_step = step.status in ['approved', 'rejected', 'commented']
    
    # === Controllo autorizzazioni ===
    # Admin vede tutto, altri utenti solo se hanno step attivi o sono approvatori
    if not current_user.is_admin:
        has_active_step = any(step.is_active and step.approver_role == current_user.role for step in approval_steps)
        has_past_step = any(step.is_past_step and step.approver_role == current_user.role for step in approval_steps)
        
        if not (has_active_step or has_past_step):
            flash('❌ Non hai autorizzazioni per visualizzare questo flusso di approvazione.', 'danger')
            return redirect(url_for('admin.dashboard'))

    return render_template("admin/document_approval_checklist.html",
                           document=document,
                           steps=approval_steps,
                           active_step=active_step)

@admin_bp.route('/admin/documents/<int:doc_id>/approvals/add_step', methods=['POST'])
@login_required
def add_approval_step(doc_id):
    """
    Aggiunge un nuovo step di approvazione al documento.
    
    Args:
        doc_id (int): ID del documento.
        
    Returns:
        Response: Redirect alla pagina del flusso.
    """
    if not current_user.is_admin and not current_user.is_ceo:
        flash('Accesso negato. Solo admin e CEO possono aggiungere step di approvazione.', 'danger')
        return redirect(url_for('admin.dashboard'))

    document = Document.query.get_or_404(doc_id)
    
    step_name = request.form.get('step_name')
    approver_id = request.form.get('approver_id')
    approver_role = request.form.get('approver_role')
    note = request.form.get('note')
    
    if not step_name:
        flash('Nome dello step obbligatorio.', 'danger')
        return redirect(url_for('admin.document_approval_flow', doc_id=doc_id))
    
    # === Crea nuovo step ===
    new_step = ApprovalStep(
        document_id=doc_id,
        step_name=step_name,
        approver_id=approver_id if approver_id else None,
        approver_role=approver_role,
        note=note
    )
    
    db.session.add(new_step)
    db.session.commit()
    
    # === Log dell'azione ===
    log_admin_action(
        "Aggiunto step approvazione",
        current_user.email,
        f"Step: {step_name} per documento {document.title}"
    )
    
    flash(f'Step "{step_name}" aggiunto con successo.', 'success')
    return redirect(url_for('admin.document_approval_flow', doc_id=doc_id))

@admin_bp.route('/admin/documents/<int:doc_id>/approvals/approve_step/<int:step_id>', methods=['POST'])
@login_required
def approve_step(doc_id, step_id):
    """
    Approva un singolo step del flusso.
    
    Args:
        doc_id (int): ID del documento.
        step_id (int): ID dello step da approvare.
        
    Returns:
        Response: Redirect alla pagina del flusso.
    """
    if not current_user.is_admin and not current_user.is_ceo:
        flash('Accesso negato. Solo admin e CEO possono approvare step.', 'danger')
        return redirect(url_for('admin.dashboard'))

    document = Document.query.get_or_404(doc_id)
    step = ApprovalStep.query.get_or_404(step_id)
    
    # === Verifica che lo step appartenga al documento ===
    if step.document_id != doc_id:
        flash('Step non valido per questo documento.', 'danger')
        return redirect(url_for('admin.document_approval_flow', doc_id=doc_id))
    
    # === Verifica che l'utente possa approvare ===
    if not step.can_be_approved_by(current_user):
        flash('Non hai i permessi per approvare questo step.', 'danger')
        return redirect(url_for('admin.document_approval_flow', doc_id=doc_id))
    
    action = request.form.get('action')  # 'approve' o 'reject'
    note = request.form.get('note')
    
    if action == 'approve':
        step.status = 'approved'
        step.approved_at = datetime.utcnow()
        step.method = 'manual'
        step.note = note
        
        flash(f'Step "{step.step_name}" approvato con successo.', 'success')
    elif action == 'reject':
        step.status = 'rejected'
        step.approved_at = datetime.utcnow()
        step.method = 'manual'
        step.note = note
        
        flash(f'Step "{step.step_name}" respinto.', 'warning')
    else:
        flash('Azione non valida.', 'danger')
        return redirect(url_for('admin.document_approval_flow', doc_id=doc_id))
    
    db.session.commit()
    
    # === Log dell'azione ===
    log_admin_action(
        f"Step {action}",
        current_user.email,
        f"Step: {step.step_name} per documento {document.title}"
    )
    
    return redirect(url_for('admin.document_approval_flow', doc_id=doc_id))

@admin_bp.route('/admin/documents/<int:doc_id>/approvals/create_default_flow', methods=['POST'])
@login_required
def create_default_approval_flow(doc_id):
    """
    Crea un flusso di approvazione predefinito per il documento.
    
    Args:
        doc_id (int): ID del documento.
        
    Returns:
        Response: Redirect alla pagina del flusso.
    """
    if not current_user.is_admin and not current_user.is_ceo:
        flash('Accesso negato. Solo admin e CEO possono creare flussi predefiniti.', 'danger')
        return redirect(url_for('admin.dashboard'))

    document = Document.query.get_or_404(doc_id)
    
    # === Verifica che non ci siano già step ===
    existing_steps = ApprovalStep.query.filter_by(document_id=doc_id).count()
    if existing_steps > 0:
        flash('Il documento ha già un flusso di approvazione. Rimuovi gli step esistenti prima.', 'warning')
        return redirect(url_for('admin.document_approval_flow', doc_id=doc_id))
    
    # === Step predefiniti ===
    default_steps = [
        {'name': 'Controllo Qualità', 'role': 'admin'},
        {'name': 'Validazione Manager', 'role': 'manager'},
        {'name': 'Approvazione CEO', 'role': 'ceo'}
    ]
    
    # === Crea gli step ===
    for step_data in default_steps:
        step = ApprovalStep(
            document_id=doc_id,
            step_name=step_data['name'],
            approver_role=step_data['role']
        )
        db.session.add(step)
    
    db.session.commit()
    
    # === Log dell'azione ===
    log_admin_action(
        "Creato flusso approvazione predefinito",
        current_user.email,
        f"Documento: {document.title}"
    )
    
    flash('Flusso di approvazione predefinito creato con successo.', 'success')
    return redirect(url_for('admin.document_approval_flow', doc_id=doc_id))

@admin_bp.route('/admin/documents/<int:doc_id>/approvals/remove_step/<int:step_id>', methods=['POST'])
@login_required
def remove_approval_step(doc_id, step_id):
    if not current_user.is_admin and not current_user.is_ceo:
        flash('Accesso negato. Solo admin e CEO possono rimuovere step.', 'danger')
        return redirect(url_for('admin.document_approval_flow', doc_id=doc_id))

    step = ApprovalStep.query.get_or_404(step_id)
    
    # Verifica che lo step appartenga al documento
    if step.document_id != doc_id:
        flash('Step non valido per questo documento.', 'danger')
        return redirect(url_for('admin.document_approval_flow', doc_id=doc_id))

    step_name = step.step_name
    db.session.delete(step)
    db.session.commit()
    
    flash(f'Step "{step_name}" rimosso con successo.', 'success')
    return redirect(url_for('admin.document_approval_flow', doc_id=doc_id))

@admin_bp.route('/documents/<int:doc_id>/approvals/<int:step_id>/action', methods=['POST'])
@login_required
def take_approval_action(doc_id, step_id):
    """
    Gestisce le azioni di approvazione per uno step specifico.
    
    Args:
        doc_id (int): ID del documento
        step_id (int): ID dello step di approvazione
        
    Returns:
        redirect: Reindirizza alla checklist aggiornata
    """
    step = ApprovalStep.query.get_or_404(step_id)
    document = Document.query.get_or_404(doc_id)

    # Verifica che lo step appartenga al documento
    if step.document_id != doc_id:
        flash('Step non valido per questo documento.', 'danger')
        return redirect(url_for('admin.document_approvals', doc_id=doc_id))

    # Controllo autorizzazioni
    if current_user.role != step.approver_role and not current_user.is_admin:
        flash('❌ Non hai i permessi per approvare questo step.', 'danger')
        return redirect(url_for('admin.document_approvals', doc_id=doc_id))

    action = request.form.get('action')
    note = request.form.get('note', '').strip()

    if action not in ['approve', 'reject', 'comment']:
        flash("❌ Azione non valida.", "danger")
        return redirect(url_for('admin.document_approvals', doc_id=doc_id))

    # Aggiorna lo stato dello step
    step.status = {
        'approve': 'approved',
        'reject': 'rejected',
        'comment': 'commented'
    }.get(action, 'pending')
    
    step.approver_id = current_user.id
    step.approved_at = datetime.utcnow()
    step.method = 'manual'
    step.note = note

    db.session.commit()

    # Log dell'azione
    log_admin_action(
        f"Step approvazione aggiornato: {action}",
        current_user.email,
        f"Documento: {document.title}, Step: {step.step_name}"
    )

    # Avanza al prossimo step se approvato
    if action == 'approve':
        advance_to_next_step(doc_id)

    flash(f"✅ Step '{step.step_name}' aggiornato come {step.status}.", "success")
    return redirect(url_for('admin.document_approvals', doc_id=doc_id))

def advance_to_next_step(document_id):
    """
    Avanza automaticamente al prossimo step di approvazione.
    
    Args:
        document_id (int): ID del documento
        
    Returns:
        None
    """
    from datetime import datetime
    
    # Ottieni tutti gli step ordinati per ID
    steps = ApprovalStep.query.filter_by(document_id=document_id).order_by(ApprovalStep.id).all()
    
    for step in steps:
        if step.status == 'pending':
            if step.auto_approval:
                # Auto-approva lo step
                step.status = 'approved'
                step.method = 'auto'
                step.approved_at = datetime.utcnow()
                step.approver_id = None
                step.note = 'Approvato automaticamente (auto_approval)'
                db.session.commit()
                
                print(f"✅ Step '{step.step_name}' auto-approvato")
                continue
            else:
                # Notifica da implementare in futuro
                print(f"🔔 Step attivo: {step.step_name} (notificare a {step.approver_role})")
                break

# === DASHBOARD DANNI ===

@admin_bp.route("/admin/danni")
@login_required
@admin_required
def dashboard_danni():
    """
    Dashboard per monitorare i danni aziendali documentati.
    
    Returns:
        Template con dashboard danni e statistiche.
    """
    # Documenti con tag "Danno"
    documenti_danni = Document.query.filter_by(tag="Danno").all()
    
    # Statistiche generali
    totale = len(documenti_danni)
    per_categoria = Counter(doc.categoria_ai for doc in documenti_danni if doc.categoria_ai)
    per_utente = Counter(doc.responsabile.username if doc.responsabile else "Non Assegnato" for doc in documenti_danni)
    per_asset = Counter(doc.asset.nome if doc.asset else "Non Specificato" for doc in documenti_danni)
    
    # Statistiche temporali
    ultimi_30_giorni = datetime.utcnow() - timedelta(days=30)
    danni_recenti = [doc for doc in documenti_danni if doc.created_at and doc.created_at >= ultimi_30_giorni]
    
    # Calcola costi totali (se disponibili)
    costi_totali = sum(doc.valore_riparazione for doc in documenti_danni if hasattr(doc, 'valore_riparazione') and doc.valore_riparazione)
    costo_medio = costi_totali / len(danni_recenti) if danni_recenti else 0
    
    return render_template("admin/dashboard_danni.html",
                         documenti=documenti_danni,
                         totale=totale,
                         per_categoria=per_categoria,
                         per_utente=per_utente,
                         per_asset=per_asset,
                         danni_recenti=len(danni_recenti),
                         costi_totali=costi_totali,
                         costo_medio=costo_medio)


@admin_bp.route("/admin/danni/export")
@login_required
@admin_required
def export_danni():
    """
    Esporta i dati dei danni in formato CSV.
    
    Returns:
        File CSV con tutti i documenti danni.
    """
    documenti = Document.query.filter_by(tag="Danno").all()
    
    # Crea il file CSV
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow([
        "Nome File", "Tipo", "Responsabile", "Asset", "Data Caricamento", 
        "Uploader", "Descrizione", "Note"
    ])
    
    for doc in documenti:
        writer.writerow([
            doc.filename,
            doc.categoria_ai or "Non Specificato",
            doc.responsabile.username if doc.responsabile else "Non Assegnato",
            doc.asset.nome if doc.asset else "Non Specificato",
            doc.created_at.strftime('%d/%m/%Y %H:%M') if doc.created_at else "N/A",
            doc.uploader_email,
            doc.description or "",
            doc.note or ""
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=danni_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@admin_bp.route("/admin/danni/export-pdf")
@login_required
@admin_required
def export_danni_pdf():
    """
    Esporta i dati dei danni in formato PDF.
    
    Returns:
        File PDF con report danni.
    """
    documenti = Document.query.filter_by(tag="Danno").all()
    
    # Statistiche per il PDF
    totale = len(documenti)
    per_categoria = Counter(doc.categoria_ai for doc in documenti if doc.categoria_ai)
    per_utente = Counter(doc.responsabile.username if doc.responsabile else "Non Assegnato" for doc in documenti)
    
    # Genera HTML per PDF
    html_content = render_template('admin/export_danni_pdf.html',
                                 documenti=documenti,
                                 totale=totale,
                                 per_categoria=per_categoria,
                                 per_utente=per_utente,
                                 data_export=datetime.utcnow().strftime('%d/%m/%Y %H:%M'))
    
    # Converti in PDF
    pdf = HTML(string=html_content).write_pdf()
    
    output = make_response(pdf)
    output.headers["Content-Disposition"] = "attachment; filename=report_danni.pdf"
    output.headers["Content-type"] = "application/pdf"
    return output

# === DASHBOARD ANALISI AI ===
@admin_bp.route("/ai-analysis")
@login_required
@admin_required
def ai_analysis_dashboard():
    """
    Dashboard per visualizzare le analisi AI sui documenti.
    """
    from models import AIAnalysisLog, Document, User
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta
    
    # Filtri
    document_id = request.args.get('document_id', type=int)
    action_type = request.args.get('action_type', '')
    accepted_filter = request.args.get('accepted', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Query base
    query = db.session.query(
        AIAnalysisLog,
        Document.title.label('document_title'),
        User.username.label('user_username')
    ).join(Document).outerjoin(User)
    
    # Applica filtri
    if document_id:
        query = query.filter(AIAnalysisLog.document_id == document_id)
    if action_type:
        query = query.filter(AIAnalysisLog.action_type == action_type)
    if accepted_filter != '':
        accepted = accepted_filter == 'true'
        query = query.filter(AIAnalysisLog.accepted_by_user == accepted)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AIAnalysisLog.timestamp >= date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(AIAnalysisLog.timestamp < date_to_obj)
        except ValueError:
            pass
    
    # Ordina per timestamp decrescente
    query = query.order_by(desc(AIAnalysisLog.timestamp))
    
    # Paginazione
    page = request.args.get('page', 1, type=int)
    per_page = 50
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Statistiche
    stats = {
        'total_analyses': db.session.query(func.count(AIAnalysisLog.id)).scalar(),
        'recent_analyses': db.session.query(func.count(AIAnalysisLog.id))
            .filter(AIAnalysisLog.timestamp >= datetime.utcnow() - timedelta(days=7)).scalar(),
        'accepted_analyses': db.session.query(func.count(AIAnalysisLog.id))
            .filter(AIAnalysisLog.accepted_by_user == True).scalar(),
        'pending_analyses': db.session.query(func.count(AIAnalysisLog.id))
            .filter(AIAnalysisLog.accepted_by_user == False, AIAnalysisLog.user_id == None).scalar()
    }
    
    # Top action types
    top_actions = db.session.query(
        AIAnalysisLog.action_type,
        func.count(AIAnalysisLog.id).label('count')
    ).group_by(AIAnalysisLog.action_type)\
     .order_by(desc(func.count(AIAnalysisLog.id)))\
     .limit(5).all()
    
    # Top documents
    top_documents = db.session.query(
        Document.title,
        func.count(AIAnalysisLog.id).label('analysis_count')
    ).join(AIAnalysisLog)\
     .group_by(Document.id, Document.title)\
     .order_by(desc(func.count(AIAnalysisLog.id)))\
     .limit(10).all()
    
    return render_template("admin/ai_analysis_dashboard.html",
                         logs=pagination.items,
                         pagination=pagination,
                         stats=stats,
                         top_actions=top_actions,
                         top_documents=top_documents,
                         filters={
                             'document_id': document_id,
                             'action_type': action_type,
                             'accepted': accepted_filter,
                             'date_from': date_from,
                             'date_to': date_to
                         })


@admin_bp.route("/ai-analysis/export")
@login_required
@admin_required
def export_ai_analysis():
    """
    Esporta i log delle analisi AI in formato CSV.
    """
    from utils_extra import export_ai_analysis_logs
    
    # Raccogli i filtri
    filters = {}
    if request.args.get('document_id'):
        filters['document_id'] = int(request.args.get('document_id'))
    if request.args.get('action_type'):
        filters['action_type'] = request.args.get('action_type')
    if request.args.get('accepted') != '':
        filters['accepted'] = request.args.get('accepted') == 'true'
    if request.args.get('date_from'):
        filters['date_from'] = datetime.strptime(request.args.get('date_from'), '%Y-%m-%d')
    if request.args.get('date_to'):
        filters['date_to'] = datetime.strptime(request.args.get('date_to'), '%Y-%m-%d') + timedelta(days=1)
    
    # Genera il CSV
    csv_content = export_ai_analysis_logs(filters)
    
    # Crea la risposta
    from flask import Response
    response = Response(csv_content, mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=ai_analysis_logs.csv'
    
    return response


@admin_bp.route("/ai-analysis/accept/<int:log_id>")
@login_required
@admin_required
def accept_ai_analysis(log_id):
    """
    Accetta un'analisi AI.
    """
    from models import AIAnalysisLog
    
    try:
        ai_log = AIAnalysisLog.query.get_or_404(log_id)
        ai_log.accepted_by_user = True
        ai_log.user_id = current_user.id
        db.session.commit()
        
        flash(f"✅ Analisi AI accettata: {ai_log.action_display}", "success")
        
    except Exception as e:
        flash(f"❌ Errore nell'accettazione: {e}", "error")
        db.session.rollback()
    
    return redirect(request.referrer or url_for('admin.ai_analysis_dashboard'))


@admin_bp.route("/ai-analysis/reject/<int:log_id>")
@login_required
@admin_required
def reject_ai_analysis(log_id):
    """
    Rifiuta un'analisi AI.
    """
    from models import AIAnalysisLog
    
    try:
        ai_log = AIAnalysisLog.query.get_or_404(log_id)
        ai_log.accepted_by_user = False
        ai_log.user_id = current_user.id
        db.session.commit()
        
        flash(f"❌ Analisi AI rifiutata: {ai_log.action_display}", "warning")
        
    except Exception as e:
        flash(f"❌ Errore nel rifiuto: {e}", "error")
        db.session.rollback()
    
    return redirect(request.referrer or url_for('admin.ai_analysis_dashboard'))

# === FUNZIONE UTILITY PER LOGGING ===
def log_admin_action(action, performed_by, extra_info=None):
    """
    Logga un'azione amministrativa nel database.
    
    Args:
        action (str): Descrizione dell'azione
        performed_by (str): Email dell'utente che ha eseguito l'azione
        extra_info (str, optional): Informazioni aggiuntive
    """
    try:
        log = AdminLog(
            action=action,
            performed_by=performed_by,
            extra_info=extra_info
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Errore nel logging admin action: {e}")

# === REGISTRO STORICO ANALISI AI ===
@admin_bp.route("/ai-analysis-log")
@login_required
@admin_required
def ai_analysis_log():
    """
    Dashboard per visualizzare lo storico delle analisi AI sui documenti.
    """
    # Parametri di filtro
    document_id = request.args.get('document_id', type=int)
    action_type = request.args.get('action_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    accepted_only = request.args.get('accepted_only', 'false') == 'true'
    
    # Query base
    query = AIAnalysisLog.query
    
    # Applica filtri
    if document_id:
        query = query.filter_by(document_id=document_id)
    if action_type:
        query = query.filter_by(action_type=action_type)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AIAnalysisLog.timestamp >= date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(AIAnalysisLog.timestamp <= date_to_obj + timedelta(days=1))
        except ValueError:
            pass
    if accepted_only:
        query = query.filter_by(accepted_by_user=True)
    
    # Ordina per timestamp decrescente
    logs = query.order_by(AIAnalysisLog.timestamp.desc()).all()
    
    # Statistiche
    total_logs = len(logs)
    accepted_logs = len([log for log in logs if log.accepted_by_user])
    rejected_logs = total_logs - accepted_logs
    
    # Conta per tipo di azione
    action_counts = {}
    for log in logs:
        action_counts[log.action_type] = action_counts.get(log.action_type, 0) + 1
    
    # Documenti disponibili per filtro
    documents = Document.query.order_by(Document.title).all()
    
    return render_template("admin/ai_analysis_log.html",
                         logs=logs,
                         total_logs=total_logs,
                         accepted_logs=accepted_logs,
                         rejected_logs=rejected_logs,
                         action_counts=action_counts,
                         documents=documents,
                         filters={
                             'document_id': document_id,
                             'action_type': action_type,
                             'date_from': date_from,
                             'date_to': date_to,
                             'accepted_only': accepted_only
                         })

@admin_bp.route("/ai-analysis-log/export")
@login_required
@admin_required
def export_ai_analysis_log():
    """
    Esporta il registro delle analisi AI in formato CSV.
    """
    # Parametri di filtro (stessi della dashboard)
    document_id = request.args.get('document_id', type=int)
    action_type = request.args.get('action_type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    accepted_only = request.args.get('accepted_only', 'false') == 'true'
    
    # Query base
    query = AIAnalysisLog.query
    
    # Applica filtri
    if document_id:
        query = query.filter_by(document_id=document_id)
    if action_type:
        query = query.filter_by(action_type=action_type)
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(AIAnalysisLog.timestamp >= date_from_obj)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(AIAnalysisLog.timestamp <= date_to_obj + timedelta(days=1))
        except ValueError:
            pass
    if accepted_only:
        query = query.filter_by(accepted_by_user=True)
    
    logs = query.order_by(AIAnalysisLog.timestamp.desc()).all()
    
    # Crea CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'ID', 'Documento', 'Tipo Azione', 'Payload', 'Timestamp', 
        'Accettato', 'Utente', 'Dettagli'
    ])
    
    # Dati
    for log in logs:
        writer.writerow([
            log.id,
            log.document.title if log.document else 'N/A',
            log.action_display,
            log.payload[:100] + '...' if log.payload and len(log.payload) > 100 else log.payload or '',
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'Sì' if log.accepted_by_user else 'No',
            log.user.full_name if log.user else 'N/A',
            log.payload_parsed.get('details', '') if log.payload_parsed else ''
        ])
    
    # Log dell'esportazione
    log_admin_action(
        f"Esportazione registro AI: {len(logs)} record",
        current_user.email,
        f"Filtri: documento={document_id}, tipo={action_type}, date={date_from}-{date_to}"
    )
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=ai_analysis_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )

# === VALIDAZIONE GERARCHICA FIRME ===
@admin_bp.route("/documenti/<int:doc_id>/firma-admin/<int:firma_id>", methods=["POST"])
@login_required
@admin_required
def approva_firma_admin(doc_id, firma_id):
    """
    Approva una firma utente da parte dell'amministratore.
    
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
            return redirect(url_for("admin.view_document", document_id=doc_id))
        
        # Verifica che la firma non sia già stata approvata dall'admin
        if firma.firma_admin:
            flash("⚠️ Firma già approvata dall'amministratore.", "warning")
            return redirect(url_for("admin.view_document", document_id=doc_id))
        
        # Approva la firma
        firma.firma_admin = True
        firma.data_firma_admin = datetime.utcnow()
        
        # Log dell'azione
        log_admin_action(
            f"Approvazione firma admin: documento {doc_id}, utente {firma.user.email}",
            current_user.email,
            f"Firma ID: {firma_id}"
        )
        
        db.session.commit()
        flash("✅ Firma validata da amministratore", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore approvazione firma admin: {e}")
        flash("❌ Errore durante l'approvazione della firma.", "danger")
    
    return redirect(url_for("admin.view_document", document_id=doc_id))

@admin_bp.route("/documenti/<int:doc_id>/firma-admin/<int:firma_id>/rifiuta", methods=["POST"])
@login_required
@admin_required
def rifiuta_firma_admin(doc_id, firma_id):
    """
    Rifiuta una firma utente da parte dell'amministratore.
    
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
            return redirect(url_for("admin.view_document", document_id=doc_id))
        
        # Rimuovi l'approvazione admin se presente
        firma.firma_admin = False
        firma.data_firma_admin = None
        
        # Log dell'azione
        log_admin_action(
            f"Rifiuto firma admin: documento {doc_id}, utente {firma.user.email}",
            current_user.email,
            f"Firma ID: {firma_id}"
        )
        
        db.session.commit()
        flash("⚠️ Firma rifiutata dall'amministratore", "warning")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore rifiuto firma admin: {e}")
        flash("❌ Errore durante il rifiuto della firma.", "danger")
    
    return redirect(url_for("admin.view_document", document_id=doc_id))

@admin_bp.route("/api/invii-documenti")
@login_required
@admin_required
def api_invii_documenti():
    """
    API endpoint per ottenere i dati degli invii di documenti.
    
    Returns:
        JSON con lista degli invii
    """
    try:
        from models import LogInvioDocumento, FirmaDocumento, Document, User
        
        # Query per ottenere tutti gli invii con relazioni
        invii = db.session.query(
            LogInvioDocumento,
            FirmaDocumento,
            Document,
            User
        ).join(
            FirmaDocumento, LogInvioDocumento.firma_id == FirmaDocumento.id
        ).join(
            Document, LogInvioDocumento.documento_id == Document.id
        ).join(
            User, FirmaDocumento.user_id == User.id
        ).order_by(
            LogInvioDocumento.data_invio.desc()
        ).all()
        
        # Converti in formato JSON
        result = []
        for log_invio, firma, documento, user in invii:
            result.append({
                'id': log_invio.id,
                'firma_id': log_invio.firma_id,
                'documento_id': log_invio.documento_id,
                'email_destinatario': log_invio.email_destinatario,
                'stato': log_invio.stato,
                'errore': log_invio.errore,
                'data_invio': log_invio.data_invio.strftime('%Y-%m-%d') if log_invio.data_invio else None,
                'data_invio_formatted': log_invio.data_invio_formatted,
                'documento_title': documento.title if documento else 'N/A',
                'utente_nome': user.full_name if user else 'N/A',
                'utente_email': user.email if user else 'N/A',
                'firma_nome': firma.nome_firma if firma else 'N/A',
                'firma_data': firma.data_firma.strftime('%d/%m/%Y %H:%M') if firma and firma.data_firma else 'N/A'
            })
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Errore API invii documenti: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route("/documenti-inviati")
@login_required
@admin_required
def documenti_inviati():
    """
    Pagina per visualizzare gli invii di documenti con filtri dinamici.
    
    Returns:
        Template della pagina
    """
    return render_template('admin/documenti_inviati.html')

@admin_bp.route("/docs/ai-dashboard")
@login_required
@admin_required
def ai_docs_dashboard():
    """Dashboard riepilogo AI documentale"""
    from app.models import Document
    from datetime import datetime, timedelta
    
    # Statistiche generali
    totali = Document.query.count()
    analizzati = Document.query.filter(Document.ai_status.isnot(None)).count()
    
    # Statistiche per stato AI
    completi = Document.query.filter_by(ai_status="completo").count()
    incompleti = Document.query.filter_by(ai_status="incompleto").count()
    scaduti = Document.query.filter_by(ai_status="scaduto").count()
    manca_firma = Document.query.filter_by(ai_status="manca_firma").count()
    
    # Calcolo percentuali
    percentuale_analizzati = round((analizzati / totali * 100) if totali > 0 else 0, 1)
    percentuale_completi = round((completi / analizzati * 100) if analizzati > 0 else 0, 1)
    percentuale_critici = round(((incompleti + scaduti + manca_firma) / analizzati * 100) if analizzati > 0 else 0, 1)
    
    # Documenti critici recenti (ultimi 7 giorni)
    una_settimana_fa = datetime.utcnow() - timedelta(days=7)
    critici_recenti = Document.query.filter(
        Document.ai_status.in_(['incompleto', 'scaduto', 'manca_firma']),
        Document.ai_analyzed_at >= una_settimana_fa
    ).order_by(Document.ai_analyzed_at.desc()).limit(10).all()
    
    # Statistiche per categoria
    categorie_stats = db.session.query(
        Document.categoria,
        db.func.count(Document.id).label('totale'),
        db.func.sum(db.case([(Document.ai_status == 'completo', 1)], else_=0)).label('completi'),
        db.func.sum(db.case([(Document.ai_status.in_(['incompleto', 'scaduto', 'manca_firma']), 1)], else_=0)).label('critici')
    ).group_by(Document.categoria).all()
    
    stats = {
        "totali": totali,
        "analizzati": analizzati,
        "completi": completi,
        "incompleti": incompleti,
        "scaduti": scaduti,
        "manca_firma": manca_firma,
        "percentuale_analizzati": percentuale_analizzati,
        "percentuale_completi": percentuale_completi,
        "percentuale_critici": percentuale_critici,
        "critici_recenti": critici_recenti,
        "categorie_stats": categorie_stats
    }
    
    return render_template("admin/ai_docs_dashboard.html", stats=stats)

@admin_bp.route("/docs/obeya-map")
@login_required
@admin_required
def obeya_map():
    """
    Pagina della mappa Obeya per visualizzazione documenti critici.
    
    Returns:
        Template: Pagina con mappa interattiva
    """
    return render_template('admin/doc_obeya_map.html')

@admin_bp.route("/docs/kpi-dashboard")
@login_required
@admin_required
def docs_kpi_dashboard():
    """
    Dashboard KPI AI documentali con performance settimanale.
    
    Returns:
        Template: Pagina dashboard KPI con grafici e insight AI
    """
    from datetime import datetime, timedelta
    from app.models import Document
    
    # Calcola date per la settimana corrente
    oggi = datetime.now().date()
    inizio_settimana = oggi - timedelta(days=oggi.weekday())
    fine_settimana = inizio_settimana + timedelta(days=6)
    
    # KPI della settimana corrente
    kpi_settimana = {
        "documenti_caricati": Document.query.filter(
            Document.created_at >= inizio_settimana,
            Document.created_at <= fine_settimana
        ).count(),
        "documenti_analizzati": Document.query.filter(
            Document.ai_analyzed_at >= inizio_settimana,
            Document.ai_analyzed_at <= fine_settimana
        ).count(),
        "documenti_firmati": Document.query.filter(
            Document.signed_at >= inizio_settimana,
            Document.signed_at <= fine_settimana
        ).count(),
        "documenti_scaduti": Document.query.filter(
            Document.expiry_date >= inizio_settimana,
            Document.expiry_date <= fine_settimana
        ).count()
    }
    
    # KPI della settimana precedente per confronto
    inizio_precedente = inizio_settimana - timedelta(days=7)
    fine_precedente = inizio_precedente + timedelta(days=6)
    
    kpi_precedente = {
        "documenti_caricati": Document.query.filter(
            Document.created_at >= inizio_precedente,
            Document.created_at <= fine_precedente
        ).count(),
        "documenti_analizzati": Document.query.filter(
            Document.ai_analyzed_at >= inizio_precedente,
            Document.ai_analyzed_at <= fine_precedente
        ).count(),
        "documenti_firmati": Document.query.filter(
            Document.signed_at >= inizio_precedente,
            Document.signed_at <= fine_precedente
        ).count(),
        "documenti_scaduti": Document.query.filter(
            Document.expiry_date >= inizio_precedente,
            Document.expiry_date <= fine_precedente
        ).count()
    }
    
    # Calcola variazioni percentuali
    variazioni = {}
    for key in kpi_settimana:
        if kpi_precedente[key] > 0:
            variazioni[key] = round(((kpi_settimana[key] - kpi_precedente[key]) / kpi_precedente[key]) * 100, 1)
        else:
            variazioni[key] = 0 if kpi_settimana[key] == 0 else 100
    
    # Insight AI
    ai_insight = []
    if variazioni["documenti_caricati"] > 20:
        ai_insight.append("📈 Ottimo incremento nell'upload di documenti questa settimana!")
    elif variazioni["documenti_caricati"] < -20:
        ai_insight.append("📉 Diminuzione nell'upload di documenti. Verifica se ci sono problemi.")
    
    if variazioni["documenti_analizzati"] > 15:
        ai_insight.append("🤖 L'analisi AI sta funzionando molto bene!")
    elif variazioni["documenti_analizzati"] < -15:
        ai_insight.append("⚠️ Diminuzione nell'analisi AI. Controlla i parametri.")
    
    if kpi_settimana["documenti_scaduti"] > 5:
        ai_insight.append("🚨 Attenzione: diversi documenti sono scaduti questa settimana.")
    
    if not ai_insight:
        ai_insight.append("✅ Tutto procede normalmente questa settimana.")
    
    return render_template(
        'admin/docs_kpi.html',
        kpi_settimana=kpi_settimana,
        kpi_precedente=kpi_precedente,
        variazioni=variazioni,
        ai_insight=ai_insight,
        inizio_settimana=inizio_settimana,
        fine_settimana=fine_settimana
    )

@admin_bp.route("/docs/scadenziario")
@login_required
@admin_required
def docs_scadenziario():
    """
    Scadenziario documenti con promemoria automatici.
    
    Returns:
        Template: Pagina scadenziario con documenti in scadenza
    """
    from datetime import datetime, timedelta
    from tasks.reminder_tasks import get_documenti_ignorati
    
    oggi = datetime.today().date()
    entro_30gg = oggi + timedelta(days=30)
    
    # Documenti in scadenza entro 30 giorni
    documenti_in_scadenza = Document.query.filter(
        Document.expiry_date.isnot(None),
        Document.expiry_date <= entro_30gg,
        Document.expiry_date >= oggi
    ).order_by(Document.expiry_date).all()
    
    # Documenti scaduti
    documenti_scaduti = Document.query.filter(
        Document.expiry_date.isnot(None),
        Document.expiry_date < oggi
    ).order_by(Document.expiry_date.desc()).all()
    
    # Documenti ignorati (incompleti da 60+ giorni)
    documenti_ignorati = get_documenti_ignorati()
    
    # Calcola statistiche
    stats = {
        "in_scadenza": len(documenti_in_scadenza),
        "scaduti": len(documenti_scaduti),
        "ignorati": len(documenti_ignorati),
        "totali": len(documenti_in_scadenza) + len(documenti_scaduti) + len(documenti_ignorati)
    }
    
    return render_template(
        'admin/docs_scadenziario.html',
        documenti_in_scadenza=documenti_in_scadenza,
        documenti_scaduti=documenti_scaduti,
        documenti_ignorati=documenti_ignorati,
        stats=stats,
        oggi=oggi
    )

@admin_bp.route("/docs/calendar-instructions")
@login_required
@admin_required
def calendar_instructions():
    """
    Pagina con istruzioni per collegare il calendario ICS.
    
    Returns:
        Template: Pagina con istruzioni per client calendario
    """
    import os
    from datetime import datetime, timedelta
    from models import Document
    
    # Token ICS
    ics_token = os.getenv("ICS_SECRET_TOKEN", "tok3n-Firm4-R3visione")
    
    # Statistiche calendario
    oggi = datetime.now().date()
    
    # Revisioni programmate
    revisioni_programmate = Document.query.filter(
        Document.prossima_revisione.isnot(None),
        Document.prossima_revisione >= oggi
    ).count()
    
    # Revisioni urgenti (scadute)
    revisioni_urgenti = Document.query.filter(
        Document.prossima_revisione.isnot(None),
        Document.prossima_revisione < oggi,
        Document.prossima_revisione >= oggi - timedelta(days=30)
    ).count()
    
    # Prossimi 30 giorni
    prossimi_30_giorni = Document.query.filter(
        Document.prossima_revisione.isnot(None),
        Document.prossima_revisione >= oggi,
        Document.prossima_revisione <= oggi + timedelta(days=30)
    ).count()
    
    # Aziende coperte
    aziende_coperte = Document.query.filter(
        Document.prossima_revisione.isnot(None),
        Document.prossima_revisione >= oggi
    ).join(Document.company).distinct(Document.company_id).count()
    
    stats = {
        "revisioni_programmate": revisioni_programmate,
        "revisioni_urgenti": revisioni_urgenti,
        "prossimi_30_giorni": prossimi_30_giorni,
        "aziende_coperte": aziende_coperte
    }
    
    return render_template(
        'admin/calendar_instructions.html',
        ics_token=ics_token,
        stats=stats
    )

@admin_bp.route("/docs/abbandonati")
@login_required
@admin_required
def docs_abbandonati():
    """
    Dashboard per documenti abbandonati (saltato 2 revisioni consecutive).
    
    Returns:
        Template: Pagina con documenti abbandonati
    """
    from tasks.alert_tasks import get_documenti_abbandonati, get_statistiche_abbandonati
    
    # Ottieni documenti abbandonati
    documenti_abbandonati = get_documenti_abbandonati()
    stats = get_statistiche_abbandonati()
    
    return render_template(
        'admin/docs_abbandonati.html',
        documenti_abbandonati=documenti_abbandonati,
        stats=stats
    )

@admin_bp.route("/docs/help")
@login_required
def docs_help():
    """
    Guida completa per l'utilizzo del modulo DOCS.
    
    Returns:
        Template: Guida HTML completa
    """
    return render_template('docs/help_docs.html')

@admin_bp.route("/docs/screenshot-demo")
@login_required
@admin_required
def docs_screenshot_demo():
    """
    Pagina demo per screenshot di onboarding e reportistica.
    
    Returns:
        Template: Struttura HTML per screenshot
    """
    return render_template('docs/screenshot_demo.html')
    """
    Dashboard KPI AI Documentali con performance settimanale.
    
    Returns:
        Template: Dashboard con KPI e grafici
    """
    kpi_data = get_kpi_documentali()
    ai_insight = genera_ai_insight(kpi_data)
    
    return render_template('admin/docs_kpi.html', kpi=kpi_data, ai_insight=ai_insight)

def get_kpi_documentali():
    """
    Calcola KPI documentali per le ultime due settimane.
    
    Returns:
        dict: Dati KPI con variazioni
    """
    from datetime import datetime, timedelta
    
    today = datetime.today()
    week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)
    
    def get_stats(start, end):
        """Calcola statistiche per un periodo specifico."""
        base = Document.query.filter(Document.last_updated.between(start, end))
        return {
            "completi": base.filter_by(ai_status="completo").count(),
            "incompleti": base.filter_by(ai_status="incompleto").count(),
            "scaduti": base.filter_by(ai_status="scaduto").count(),
            "manca_firma": base.filter_by(ai_status="manca_firma").count(),
            "analizzati": base.filter(Document.ai_status.isnot(None)).count(),
            "totali": base.count()
        }
    
    # Statistiche settimana corrente
    last_week = get_stats(week_ago, today)
    
    # Statistiche settimana precedente
    prev_week = get_stats(two_weeks_ago, week_ago)
    
    # Calcola variazioni
    variazioni = {}
    for k in last_week:
        current = last_week[k]
        previous = prev_week.get(k, 0)
        delta = current - previous
        
        # Calcola percentuale di variazione
        if previous > 0:
            percentuale = (delta / previous) * 100
        else:
            percentuale = 100 if delta > 0 else 0
            
        variazioni[k] = {
            "delta": delta,
            "percentuale": round(percentuale, 1),
            "trend": "up" if delta > 0 else "down" if delta < 0 else "stable"
        }
    
    # Dati per grafico lineare (ultimi 14 giorni)
    chart_data = get_chart_data()
    
    return {
        "settimana_corrente": last_week,
        "settimana_precedente": prev_week,
        "variazioni": variazioni,
        "chart_data": chart_data
    }

def get_chart_data():
    """
    Genera dati per il grafico lineare degli ultimi 14 giorni.
    
    Returns:
        dict: Dati per Chart.js
    """
    from datetime import datetime, timedelta
    
    # Genera date per ultimi 14 giorni
    dates = []
    completi_data = []
    incompleti_data = []
    scaduti_data = []
    manca_firma_data = []
    
    for i in range(14, -1, -1):  # Da 14 giorni fa a oggi
        date = datetime.today() - timedelta(days=i)
        dates.append(date.strftime('%d/%m'))
        
        # Statistiche per questa data
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        base = Document.query.filter(Document.last_updated.between(start_of_day, end_of_day))
        
        completi_data.append(base.filter_by(ai_status="completo").count())
        incompleti_data.append(base.filter_by(ai_status="incompleto").count())
        scaduti_data.append(base.filter_by(ai_status="scaduto").count())
        manca_firma_data.append(base.filter_by(ai_status="manca_firma").count())
    
    return {
        "labels": dates,
        "datasets": [
            {
                "label": "Completi",
                "data": completi_data,
                "borderColor": "#28a745",
                "backgroundColor": "rgba(40, 167, 69, 0.1)",
                "tension": 0.4
            },
            {
                "label": "Incompleti",
                "data": incompleti_data,
                "borderColor": "#ffc107",
                "backgroundColor": "rgba(255, 193, 7, 0.1)",
                "tension": 0.4
            },
            {
                "label": "Scaduti",
                "data": scaduti_data,
                "borderColor": "#dc3545",
                "backgroundColor": "rgba(220, 53, 69, 0.1)",
                "tension": 0.4
            },
            {
                "label": "Manca Firma",
                "data": manca_firma_data,
                "borderColor": "#fd7e14",
                "backgroundColor": "rgba(253, 126, 20, 0.1)",
                "tension": 0.4
            }
        ]
    }

def genera_ai_insight(kpi):
    """
    Genera insight AI automatici basati sui KPI.
    
    Args:
        kpi (dict): Dati KPI documentali
        
    Returns:
        str: Insight generato automaticamente
    """
    variazioni = kpi["variazioni"]
    
    # Analizza trend completi vs incompleti
    completi_delta = variazioni["completi"]["delta"]
    incompleti_delta = variazioni["incompleti"]["delta"]
    scaduti_delta = variazioni["scaduti"]["delta"]
    analizzati_delta = variazioni["analizzati"]["delta"]
    
    insights = []
    
    # Insight 1: Miglioramento qualità
    if completi_delta > 3 and incompleti_delta < 0:
        insights.append(f"📈 Ottimo miglioramento nella qualità documentale: +{completi_delta} completi, {incompleti_delta} incompleti")
    
    # Insight 2: Attenzione scaduti
    if scaduti_delta > 2:
        insights.append(f"⚠️ Attenzione: aumento di {scaduti_delta} documenti scaduti rispetto alla settimana scorsa")
    
    # Insight 3: Aumento analisi AI
    if analizzati_delta > 5:
        insights.append(f"🤖 Aumento significativo dell'analisi AI: +{analizzati_delta} documenti analizzati")
    
    # Insight 4: Trend negativo
    if completi_delta < 0 and incompleti_delta > 2:
        insights.append(f"📉 Trend negativo: -{abs(completi_delta)} completi, +{incompleti_delta} incompleti")
    
    # Insight 5: Stabilità
    if abs(completi_delta) <= 1 and abs(incompleti_delta) <= 1 and abs(scaduti_delta) <= 1:
        insights.append("➖ Stabilità nella qualità documentale: nessuna variazione significativa")
    
    # Insight 6: Performance generale
    totale_corrente = kpi["settimana_corrente"]["totali"]
    totale_precedente = kpi["settimana_precedente"]["totali"]
    if totale_corrente > totale_precedente:
        insights.append(f"📊 Aumento attività documentale: +{totale_corrente - totale_precedente} documenti gestiti")
    
    return insights if insights else ["📊 Nessun insight significativo per questo periodo"]



