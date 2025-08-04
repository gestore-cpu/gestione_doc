from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from extensions import db
from models import Document, User, Department, Company, AuditLog

ceo_bp = Blueprint('ceo', __name__, url_prefix='/ceo')

@ceo_bp.before_request
@login_required
def restrict_to_ceo():
    """
    Middleware per limitare l'accesso solo ai CEO.
    """
    if not current_user.is_authenticated or current_user.role != 'ceo':
        abort(403)

@ceo_bp.route('/dashboard')
def dashboard():
    """
    Dashboard principale per i CEO.
    
    Returns:
        template: Dashboard CEO con statistiche e documenti in attesa.
    """
    # Documenti in attesa di approvazione CEO
    pending_docs = Document.query.filter(
        Document.validazione_admin == True,
        Document.validazione_ceo == False
    ).all()
    
    # Statistiche generali
    total_docs = Document.query.count()
    approved_docs = Document.query.filter(
        Document.validazione_admin == True,
        Document.validazione_ceo == True
    ).count()
    
    return render_template('ceo/dashboard.html',
                         pending_docs=pending_docs,
                         total_docs=total_docs,
                         approved_docs=approved_docs)

@ceo_bp.route('/documents')
def documents_list():
    """
    Lista di tutti i documenti per il CEO.
    
    Returns:
        template: Lista documenti con filtri per stato approvazione.
    """
    # Filtri per stato approvazione
    filter_status = request.args.get('status', 'all')
    
    if filter_status == 'pending':
        docs = Document.query.filter(
            Document.validazione_admin == True,
            Document.validazione_ceo == False
        ).all()
    elif filter_status == 'approved':
        docs = Document.query.filter(
            Document.validazione_admin == True,
            Document.validazione_ceo == True
        ).all()
    elif filter_status == 'waiting_admin':
        docs = Document.query.filter(
            Document.validazione_admin == False
        ).all()
    else:
        docs = Document.query.all()
    
    return render_template('ceo/documents.html', documents=docs, filter_status=filter_status)

@ceo_bp.route('/document/<int:doc_id>')
def document_detail(doc_id):
    """
    Dettaglio documento per il CEO.
    
    Args:
        doc_id (int): ID del documento.
        
    Returns:
        template: Dettaglio documento con opzioni di approvazione.
    """
    doc = Document.query.get_or_404(doc_id)
    return render_template('ceo/document_detail.html', document=doc)

@ceo_bp.route("/document/<int:doc_id>/approva", methods=["POST"])
@login_required
def approva_documento_ceo(doc_id):
    """
    Approva un documento come CEO.
    
    Args:
        doc_id (int): ID del documento da approvare.
        
    Returns:
        redirect: Reindirizzamento alla pagina del documento.
    """
    if current_user.role != 'ceo':
        abort(403)

    doc = Document.query.get_or_404(doc_id)
    
    # Verifica che l'admin abbia già approvato
    if not doc.validazione_admin:
        flash("⛔ Il documento deve essere prima approvato dall'Admin.", "warning")
        return redirect(url_for("ceo.document_detail", doc_id=doc.id))
    
    doc.validazione_ceo = True
    
    # Log dell'approvazione CEO
    audit_log = AuditLog(
        user_id=current_user.id,
        document_id=doc.id,
        azione='approvazione_ceo',
        note=f'Documento "{doc.title or doc.original_filename}" approvato da CEO'
    )
    db.session.add(audit_log)
    db.session.commit()
    
    flash("👑 Documento approvato da CEO.", "success")
    return redirect(url_for("ceo.document_detail", doc_id=doc.id))

@ceo_bp.route('/reports')
def reports():
    """
    Report e statistiche per il CEO.
    
    Returns:
        template: Pagina con report e statistiche.
    """
    # Statistiche per reparto
    departments = Department.query.all()
    dept_stats = []
    
    for dept in departments:
        total = Document.query.filter_by(department_id=dept.id).count()
        approved = Document.query.filter(
            Document.department_id == dept.id,
            Document.validazione_admin == True,
            Document.validazione_ceo == True
        ).count()
        
        dept_stats.append({
            'department': dept,
            'total': total,
            'approved': approved,
            'pending': total - approved
        })
    
    return render_template('ceo/reports.html', dept_stats=dept_stats) 