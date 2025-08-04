import os
from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from models import Document

list_drive_bp = Blueprint('list_drive', __name__, url_prefix='/gdrive')

@list_drive_bp.route('/list', methods=['GET'])
@login_required
def list_drive_documents():
    try:
        # Filtra solo documenti caricati su Google Drive per l'azienda/reparto correnti
        documents = Document.query.filter(
            Document.drive_file_id.isnot(None),
            Document.company == current_user.company.name,
            Document.department == current_user.department.name
        ).order_by(Document.created_at.desc()).all()

        return render_template('drive_list.html', documents=documents)

    except Exception as e:
        current_app.logger.error(f"[DRIVE LIST ERROR] {e}")
        return render_template('drive_list.html', documents=[], error="Errore durante il recupero dei documenti.")
