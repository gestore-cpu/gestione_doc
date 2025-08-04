from flask import Blueprint, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, Document
from datetime import datetime
import os
import logging

# Configurazione logging
logger = logging.getLogger(__name__)

drive_bp = Blueprint('drive', __name__)

def trigger_drive_upload(document_id):
    """
    Trigger per l'upload automatico su Google Drive dopo approvazione CEO.
    
    Args:
        document_id (int): ID del documento da caricare
        
    Returns:
        bool: True se upload riuscito
    """
    try:
        from utils.drive_utils import upload_to_drive
        
        # Recupera documento
        doc = Document.query.get(document_id)
        if not doc:
            logger.error(f"Documento {document_id} non trovato")
            return False
        
        # Verifica che sia firmato dal CEO
        if not doc.approvato_dal_ceo:
            logger.warning(f"Documento {document_id} non ancora approvato dal CEO")
            return False
        
        # Verifica esistenza file locale
        local_path = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.filename)
        if not os.path.exists(local_path):
            logger.error(f"File locale non trovato: {local_path}")
            return False
        
        # Prepara struttura cartelle
        subfolders = []
        if doc.company and doc.company.name:
            subfolders.append(doc.company.name)
        if doc.department and doc.department.name:
            subfolders.append(doc.department.name)
        if doc.tag:  # Usa tag come categoria
            subfolders.append(doc.tag)
        
        # Upload su Drive
        drive_file_id = upload_to_drive(local_path, doc.original_filename or doc.filename, subfolders)
        
        # Aggiorna documento
        doc.drive_file_id = drive_file_id
        doc.drive_uploaded_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Documento {document_id} caricato su Drive con ID: {drive_file_id}")
        return True
        
    except Exception as e:
        logger.error(f"Errore nell'upload automatico documento {document_id}: {str(e)}")
        return False

@drive_bp.route("/documenti/<int:id>/reupload_drive", methods=["POST"])
@login_required
def reupload_drive(id):
    """
    Reupload manuale su Google Drive.
    
    Args:
        id (int): ID del documento
        
    Returns:
        str: Redirect alla pagina documento
    """
    try:
        # Verifica permessi
        if not current_user.is_admin and not current_user.is_ceo:
            flash("❌ Accesso negato", "danger")
            return redirect(url_for('index'))
        
        doc = Document.query.get_or_404(id)
        
        # Verifica che sia firmato dal CEO
        if not doc.approvato_dal_ceo:
            flash("❌ Documento non ancora approvato dal CEO", "danger")
            return redirect(url_for('docs.view_document', id=doc.id))
        
        from utils.drive_utils import upload_to_drive
        
        # Verifica esistenza file locale
        local_path = os.path.join(current_app.config["UPLOAD_FOLDER"], doc.filename)
        if not os.path.exists(local_path):
            flash("❌ File locale non trovato", "danger")
            return redirect(url_for('docs.view_document', id=doc.id))
        
        # Prepara struttura cartelle
        subfolders = []
        if doc.company and doc.company.name:
            subfolders.append(doc.company.name)
        if doc.department and doc.department.name:
            subfolders.append(doc.department.name)
        if doc.tag:  # Usa tag come categoria
            subfolders.append(doc.tag)
        
        # Upload su Drive
        drive_file_id = upload_to_drive(local_path, doc.original_filename or doc.filename, subfolders)
        
        # Aggiorna documento
        doc.drive_file_id = drive_file_id
        doc.drive_uploaded_at = datetime.utcnow()
        db.session.commit()
        
        flash("✅ Reupload su Google Drive completato", "success")
        logger.info(f"Reupload Drive completato per documento {id} da user {current_user.id}")
        
    except Exception as e:
        flash("❌ Errore durante il reupload su Drive", "danger")
        logger.error(f"Errore reupload Drive documento {id}: {str(e)}")
    
    return redirect(url_for('docs.view_document', id=id))

@drive_bp.route("/documenti/<int:id>/delete_drive", methods=["POST"])
@login_required
def delete_from_drive(id):
    """
    Elimina file da Google Drive.
    
    Args:
        id (int): ID del documento
        
    Returns:
        str: Redirect alla pagina documento
    """
    try:
        # Verifica permessi
        if not current_user.is_admin and not current_user.is_ceo:
            flash("❌ Accesso negato", "danger")
            return redirect(url_for('index'))
        
        doc = Document.query.get_or_404(id)
        
        if not doc.drive_file_id:
            flash("❌ File non presente su Google Drive", "warning")
            return redirect(url_for('docs.view_document', id=doc.id))
        
        from utils.drive_utils import delete_from_drive
        
        # Elimina da Drive
        if delete_from_drive(doc.drive_file_id):
            # Aggiorna documento
            doc.drive_file_id = None
            doc.drive_uploaded_at = None
            db.session.commit()
            
            flash("✅ File eliminato da Google Drive", "success")
            logger.info(f"File Drive eliminato per documento {id} da user {current_user.id}")
        else:
            flash("❌ Errore nell'eliminazione da Drive", "danger")
        
    except Exception as e:
        flash("❌ Errore durante l'eliminazione da Drive", "danger")
        logger.error(f"Errore eliminazione Drive documento {id}: {str(e)}")
    
    return redirect(url_for('docs.view_document', id=id))

@drive_bp.route("/drive/status")
@login_required
def drive_status():
    """
    Verifica lo stato della connessione Google Drive.
    
    Returns:
        str: Status della connessione
    """
    try:
        from utils.drive_utils import check_drive_connection
        
        if check_drive_connection():
            return "✅ Connessione Google Drive OK"
        else:
            return "❌ Errore connessione Google Drive"
            
    except Exception as e:
        return f"❌ Errore verifica Drive: {str(e)}"


@drive_bp.route("/bulk_upload", methods=["POST"])
@login_required
def bulk_upload_documents():
    """
    Upload in massa di documenti suggeriti dall'AI.
    
    Returns:
        Redirect alla dashboard AI
    """
    try:
        # Verifica permessi (solo CEO)
        if not current_user.is_ceo:
            flash("❌ Solo il CEO può eseguire upload in massa.", "danger")
            return redirect(url_for("ceo.dashboard_docs_ceo"))
        
        from utils.ai_utils import suggerisci_documenti_da_caricare
        suggeriti = suggerisci_documenti_da_caricare()
        
        successi = 0
        errori = 0
        
        for suggerito in suggeriti:
            doc_id = suggerito["doc"].id
            try:
                if trigger_drive_upload(doc_id):
                    successi += 1
                else:
                    errori += 1
            except Exception as e:
                logger.error(f"Errore upload documento {doc_id}: {str(e)}")
                errori += 1
        
        if successi > 0:
            flash(f"✅ {successi} documenti caricati con successo su Google Drive", "success")
        if errori > 0:
            flash(f"⚠️ {errori} documenti non sono stati caricati a causa di errori", "warning")
            
    except Exception as e:
        logger.error(f"Errore upload in massa: {str(e)}")
        flash("❌ Errore durante l'upload in massa", "danger")
    
    return redirect(url_for("ceo.dashboard_drive_ai")) 