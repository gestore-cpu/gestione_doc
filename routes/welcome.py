from flask import Blueprint, render_template
from flask_login import login_required, current_user
from flask import request, flash, redirect, url_for
from models import Document, AccessRequest, GuestActivity, AuthorizedAccess
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

welcome_bp = Blueprint('welcome', __name__)

@welcome_bp.route('/welcome')
@login_required
def welcome():
    print(f"[DEBUG] Welcome page visitata da: {current_user.email}, ruolo: {current_user.role}")
    return render_template(
        'welcome.html',
        is_admin=current_user.is_admin,
        is_user=current_user.is_user,
        is_guest=current_user.is_guest
    )

@welcome_bp.route('/download')
@login_required
def download_page():
    user = current_user

    # Tutti i documenti
    all_documents = Document.query.all()

    # Recupera ID documenti a cui l'utente ha accesso
    if user.role == 'admin':
        accessible_ids = {doc.id for doc in all_documents}
    else:
        accessible_ids = {
            access.document_id for access in AuthorizedAccess.query.filter_by(user_id=user.id)
        }

    # Prepara lista documenti con flag accesso
    document_list = []
    for doc in all_documents:
        document_list.append({
            'id': doc.id,
            'filename': doc.filename,
            'company': doc.company,
            'department': doc.department,
            'upload_date': doc.upload_date,
            'accessible': doc.id in accessible_ids
        })

    # Statistiche riepilogo
    total_files = len(all_documents)
    companies_count = len({doc.company_id for doc in all_documents if doc.company_id})
    departments_count = len({doc.department_id for doc in all_documents if doc.department_id})
    recent_downloads_count = GuestActivity.query.filter(
        GuestActivity.user_id == user.id,
        GuestActivity.timestamp >= datetime.utcnow() - timedelta(days=7)
    ).count()

    return render_template(
        "download.html",
        documents=document_list,
        total_files=total_files,
        companies_count=companies_count,
        departments_count=departments_count,
        recent_downloads_count=recent_downloads_count
    )

@welcome_bp.route('/my-downloads')
@login_required
def my_downloads():
    from sqlalchemy import or_
    from models import Document, AccessRequest
    from services.ai import ai_suggerisci_documenti, ai_suggerisci_documenti_nascosti
    # Documenti accessibili per ruolo diretto
    docs_direct = Document.query.filter(
        or_(
            current_user.role == 'admin',
            Document.company_id.in_([c.id for c in current_user.companies]),
            Document.department_id.in_([d.id for d in current_user.departments])
        )
    ).all()
    # Documenti accessibili da richiesta approvata
    approved_doc_ids = db.session.query(AccessRequest.document_id).filter_by(user_id=current_user.id, status="approved").all()
    approved_ids = [doc_id for doc_id, in approved_doc_ids]
    docs_approved = Document.query.filter(Document.id.in_(approved_ids)).all()
    # Richieste inviate
    requests = AccessRequest.query.filter_by(user_id=current_user.id).order_by(AccessRequest.timestamp.desc()).all()
    # Unione documenti diretti + approvati (senza duplicati)
    access_ids = {doc.id for doc in docs_direct} | {doc.id for doc in docs_approved}
    access_docs = Document.query.filter(Document.id.in_(access_ids)).order_by(Document.uploaded_at.desc()).all()
    # Suggerimenti AI
    all_docs = Document.query.order_by(Document.uploaded_at.desc()).all()
    suggestions = ai_suggerisci_documenti(current_user, all_docs)
    hidden_suggestions = ai_suggerisci_documenti_nascosti(current_user, all_docs)
    return render_template("my_downloads.html", access_docs=access_docs, requests=requests, suggestions=suggestions, hidden_suggestions=hidden_suggestions)

@welcome_bp.route("/request_access/<int:document_id>", methods=["POST"])
@login_required
def request_access(document_id):
    from models import AccessRequest
    from flask import jsonify, request
    existing = AccessRequest.query.filter_by(
        user_id=current_user.id,
        document_id=document_id,
        status='pending'
    ).first()
    if existing:
        return jsonify({"status": "already_pending"})

    req = AccessRequest(
        user_id=current_user.id,
        document_id=document_id,
        message=request.json.get("message", "")
    )
    db.session.add(req)
    db.session.commit()

    # Invia email al proprietario del documento
    from flask_mail import Message
    from extensions import mail
    document = Document.query.get(document_id)
    owner = document.uploader  # relazione User
    msg = Message(
        subject="📄 Richiesta accesso a un documento",
        recipients=[owner.email],
        body=f"""Ciao {owner.username},\n\nL'utente {current_user.username} ({current_user.email}) ha richiesto l'accesso al documento '{document.filename}'.\n\nMessaggio: {req.message or '— nessun messaggio —'}\n\nPuoi approvare o rifiutare la richiesta dalla dashboard admin:\nhttps://docs.mercurysurgelati.org/admin/access_requests\n"""
    )
    mail.send(msg)
    return jsonify({"status": "ok"})
