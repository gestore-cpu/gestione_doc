from flask import Blueprint, redirect, url_for, render_template, abort
from flask_login import login_required, current_user
from models import Document  # assicurati che il modello sia importato

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))  # dashboard admin
    else:
        return redirect(url_for('welcome.welcome'))  # pagina welcome utenti normali

@user_bp.route('/my_documents')
@login_required
def my_documents():
    # Recupera i documenti associati all'utente
    documents = getattr(current_user, 'documents', [])
    return render_template('user/my_documents.html', documents=documents)

@user_bp.route('/document/<int:document_id>')
@login_required
def view_document(document_id):
    doc = Document.query.get_or_404(document_id)
    # Controlla che l'utente sia proprietario o admin
    if doc.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return render_template('user/view_document.html', document=doc)
