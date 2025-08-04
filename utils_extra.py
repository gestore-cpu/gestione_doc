import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app, render_template
from uuid import uuid4
import io
try:
    from googleapiclient.http import MediaIoBaseUpload
except ImportError:
    MediaIoBaseUpload = None

# Import per PDF generation
try:
    from weasyprint import HTML
except ImportError:
    HTML = None

# ============================
# ✅ Verifica estensione file
# ============================
def allowed_file(filename):
    allowed_extensions = {'pdf', 'docx', 'xlsx', 'png', 'jpg', 'jpeg', 'txt'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# ============================
# ✅ Salvataggio e upload su Drive (simulato)
# ============================
def save_file_and_upload_to_drive(file, company_name, department_name):
    """
    Salva il file localmente in sottocartelle azienda/reparto e restituisce info
    """
    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    new_filename = f"{timestamp}_{filename}"

    # 📁 Path: uploads/NOME_AZIENDA/NOME_REPARTO
    base_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    company_folder = os.path.join(base_folder, secure_filename(company_name))
    department_folder = os.path.join(company_folder, secure_filename(department_name))
    os.makedirs(department_folder, exist_ok=True)

    local_path = os.path.join(department_folder, new_filename)
    file.save(local_path)

    # 🟡 Simulazione ID Drive
    drive_file_id = "DRIVE_FILE_ID_SIMULATO"

    return new_filename, local_path, drive_file_id

# ============================
# ✅ Log o notifiche
# ============================
def notify_upload(document):
    """
    Placeholder per log/caricamento notifiche
    """
    current_app.logger.info(f"Documento caricato: {document.title} da {document.uploader_email}")

# ============================
# ✅ Sicurezza password
# ============================
def is_secure_password(password):
    """
    Controlla se una password è sicura:
    - almeno 8 caratteri
    - almeno una lettera maiuscola
    - almeno una lettera minuscola
    - almeno un numero
    - almeno un simbolo speciale
    """
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True

def save_file_and_upload(file, upload_to_drive=False, drive_service=None, drive_folder_id=None):
    """
    Salva temporaneamente il file in uploads/temp/ con nome unico e opzionalmente lo carica su Google Drive.

    Args:
        file (werkzeug.datastructures.FileStorage): Il file da salvare.
        upload_to_drive (bool): Se True, carica il file su Google Drive.
        drive_service: Oggetto Google Drive service autenticato.
        drive_folder_id (str): ID della cartella Drive dove caricare il file.

    Returns:
        tuple: (local_path, drive_file_id or None)
    """
    from flask import current_app
    from datetime import datetime
    import os
    from werkzeug.utils import secure_filename

    # Crea nome unico
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    unique_id = str(uuid4())
    filename = secure_filename(file.filename)
    new_filename = f"{timestamp}_{unique_id}_{filename}"

    # Salva in uploads/temp/
    base_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    temp_folder = os.path.join(base_folder, 'temp')
    os.makedirs(temp_folder, exist_ok=True)
    local_path = os.path.join(temp_folder, new_filename)
    file.seek(0)
    file.save(local_path)

    drive_file_id = None
    if upload_to_drive and drive_service and MediaIoBaseUpload:
        media = MediaIoBaseUpload(io.BytesIO(open(local_path, 'rb').read()), mimetype=file.mimetype)
        body = {'name': new_filename}
        if drive_folder_id:
            body['parents'] = [drive_folder_id]
        uploaded_file = drive_service.files().create(
            body=body,
            media_body=media,
            fields='id'
        ).execute()
        drive_file_id = uploaded_file.get('id')

    return local_path, drive_file_id

def log_document_activity(document_id, user_id, action, note=None):
    """Logga un'attività su un documento."""
    from models import DocumentActivityLog
    from extensions import db
    log = DocumentActivityLog(
        document_id=document_id,
        user_id=user_id,
        action=action,
        note=note
    )
    db.session.add(log)
    db.session.commit()

def generate_pdf_copertura_eventi(eventi, alert_ai, user_email, stats=None):
    """
    Genera un PDF della dashboard copertura attestati.

    Args:
        eventi: Lista di dizionari con i dati degli eventi
        alert_ai: Lista di stringhe (alert AI)
        user_email: Email di chi genera il report
        stats: Dizionario con statistiche generali (opzionale)
    
    Returns:
        str: percorso del file PDF generato
    """
    if HTML is None:
        raise ImportError("WeasyPrint non è installato. Installa con: pip install WeasyPrint")
    
    data_generazione = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Se stats non è fornito, calcola le statistiche dai dati eventi
    if stats is None:
        stats = {
            'total_eventi': len(eventi),
            'total_partecipanti': sum(e.get('totale', 0) for e in eventi),
            'total_attestati': sum(e.get('attestati', 0) for e in eventi),
            'media_copertura': 0
        }
        
        if stats['total_partecipanti'] > 0:
            stats['media_copertura'] = round(
                (stats['total_attestati'] / stats['total_partecipanti']) * 100, 1
            )
    
    # Configura il contesto per WeasyPrint
    with current_app.test_request_context():
        rendered = render_template(
            "qms/copertura_eventi_pdf.html",
            eventi=eventi,
            alert_ai=alert_ai,
            data_generazione=data_generazione,
            user_email=user_email,
            stats=stats
        )

    output_dir = os.path.join(current_app.root_path, "static", "pdf_reports")
    os.makedirs(output_dir, exist_ok=True)

    filename = f"copertura_eventi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    file_path = os.path.join(output_dir, filename)

    # Converte l'HTML in PDF
    HTML(string=rendered, base_url=current_app.root_path).write_pdf(file_path)

    return file_path

"""
Utility functions for document management.
"""

def confronta_documenti_ai(doc1, doc2):
    """
    Confronta due documenti usando AI.
    
    Args:
        doc1: Primo documento
        doc2: Secondo documento
        
    Returns:
        dict: Risultati del confronto
    """
    # Placeholder per confronto AI
    return {
        'similarita': 0.0,
        'differenze': [],
        'note': 'Confronto AI non implementato'
    }

def estrai_testo(file_path):
    """
    Estrae testo da un file (PDF, DOCX, TXT).
    
    Args:
        file_path (str): Percorso del file
    
    Returns:
        str: Testo estratto o None se errore
    """
    try:
        import os
        if not os.path.exists(file_path):
            return None
            
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_ext == '.pdf':
            # Per PDF usa PyPDF2 o pdfplumber se disponibile
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                # Fallback: prova con pdfplumber
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        text = ""
                        for page in pdf.pages:
                            text += page.extract_text() + "\n"
                        return text
                except ImportError:
                    return None
        elif file_ext == '.docx':
            # Per DOCX usa python-docx se disponibile
            try:
                from docx import Document
                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                return None
        else:
            # Per altri formati, prova a leggere come testo
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                return None
                
    except Exception as e:
        current_app.logger.error(f"Errore estrazione testo da {file_path}: {e}")
        return None

def log_ai_analysis(document_id, action_type, payload=None, user_id=None, accepted=False):
    """
    Registra un'analisi AI nel log.
    
    Args:
        document_id (int): ID del documento analizzato.
        action_type (str): Tipo di azione AI.
        payload (dict, optional): Dettagli dell'intervento.
        user_id (int, optional): ID dell'utente che ha accettato/rifiutato.
        accepted (bool): Se l'intervento è stato accettato.
    """
    from app import db
    from models import AIAnalysisLog
    import json
    
    try:
        # Converti payload in JSON se fornito
        payload_json = json.dumps(payload) if payload else None
        
        # Crea il log
        ai_log = AIAnalysisLog(
            document_id=document_id,
            action_type=action_type,
            payload=payload_json,
            user_id=user_id,
            accepted_by_user=accepted
        )
        
        db.session.add(ai_log)
        db.session.commit()
        
        print(f"✅ Log AI registrato: {action_type} per documento {document_id}")
        
    except Exception as e:
        print(f"❌ Errore nel logging AI: {e}")
        db.session.rollback()

def get_ai_analysis_stats():
    """
    Restituisce statistiche sulle analisi AI.
    
    Returns:
        dict: Statistiche sulle analisi AI.
    """
    from models import AIAnalysisLog, Document
    from sqlalchemy import func
    
    try:
        # Conteggi per tipo di azione
        action_counts = db.session.query(
            AIAnalysisLog.action_type,
            func.count(AIAnalysisLog.id).label('count')
        ).group_by(AIAnalysisLog.action_type).all()
        
        # Conteggi per stato
        status_counts = db.session.query(
            AIAnalysisLog.accepted_by_user,
            func.count(AIAnalysisLog.id).label('count')
        ).group_by(AIAnalysisLog.accepted_by_user).all()
        
        # Documenti più analizzati
        top_documents = db.session.query(
            Document.title,
            func.count(AIAnalysisLog.id).label('analysis_count')
        ).join(AIAnalysisLog).group_by(Document.id, Document.title)\
         .order_by(func.count(AIAnalysisLog.id).desc()).limit(10).all()
        
        # Analisi recenti (ultimi 7 giorni)
        recent_analyses = db.session.query(func.count(AIAnalysisLog.id))\
            .filter(AIAnalysisLog.timestamp >= func.date('now', '-7 days')).scalar()
        
        return {
            'action_counts': dict(action_counts),
            'status_counts': dict(status_counts),
            'top_documents': top_documents,
            'recent_analyses': recent_analyses,
            'total_analyses': db.session.query(func.count(AIAnalysisLog.id)).scalar()
        }
        
    except Exception as e:
        print(f"❌ Errore nel calcolo statistiche AI: {e}")
        return {}

def export_ai_analysis_logs(filters=None):
    """
    Esporta i log delle analisi AI in formato CSV.
    
    Args:
        filters (dict, optional): Filtri da applicare.
        
    Returns:
        str: Contenuto CSV dei log.
    """
    from models import AIAnalysisLog, Document, User
    import csv
    import io
    
    try:
        # Query base
        query = db.session.query(
            AIAnalysisLog,
            Document.title.label('document_title'),
            User.username.label('user_username')
        ).join(Document).outerjoin(User)
        
        # Applica filtri
        if filters:
            if filters.get('document_id'):
                query = query.filter(AIAnalysisLog.document_id == filters['document_id'])
            if filters.get('action_type'):
                query = query.filter(AIAnalysisLog.action_type == filters['action_type'])
            if filters.get('accepted') is not None:
                query = query.filter(AIAnalysisLog.accepted_by_user == filters['accepted'])
            if filters.get('date_from'):
                query = query.filter(AIAnalysisLog.timestamp >= filters['date_from'])
            if filters.get('date_to'):
                query = query.filter(AIAnalysisLog.timestamp <= filters['date_to'])
        
        # Ordina per timestamp decrescente
        query = query.order_by(AIAnalysisLog.timestamp.desc())
        
        # Prepara il CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'ID', 'Documento', 'Tipo Azione', 'Timestamp', 'Stato', 'Utente',
            'Payload', 'Document ID', 'User ID'
        ])
        
        # Dati
        for log, doc_title, user_username in query.all():
            writer.writerow([
                log.id,
                doc_title or 'N/A',
                log.action_display,
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.status_display,
                user_username or 'N/A',
                log.payload or '',
                log.document_id,
                log.user_id or ''
            ])
        
        return output.getvalue()
        
    except Exception as e:
        print(f"❌ Errore nell'esportazione log AI: {e}")
        return ""
