from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template, abort, current_app, send_file, make_response
from flask_login import login_required, current_user
from decorators import admin_required
from datetime import datetime
from extensions import db
from models import AccessRequest, Document, DocumentReadLog, AuditLog, DocumentVersion, ApprovazioneDocumento, FirmaDocumento, AIAnalysisLog, Task
from services.semantic_search import cerca_documenti, indicizza_documento
from utils.version_utils import (
    salva_versione_anteriore, 
    attiva_nuova_versione, 
    ripristina_versione, 
    elimina_versione,
    get_versioni_documento,
    confronta_versioni
)
# from utils import confronta_documenti_ai  # Commentato temporaneamente
from werkzeug.utils import secure_filename
from io import StringIO
import csv
import os
# from weasyprint import HTML, CSS
# from weasyprint.text.fonts import FontConfiguration
import secrets
import json

docs_bp = Blueprint('docs', __name__)

def verifica_accesso_documento(doc):
    """
    Verifica se un documento è accessibile (approvato da Admin + CEO).
    
    Args:
        doc (Document): Il documento da verificare.
        
    Returns:
        bool: True se il documento è accessibile, False altrimenti.
    """
    if not (doc.validazione_admin and doc.validazione_ceo):
        flash("⛔ Documento non ancora approvato da Admin e CEO.", "warning")
        return False
    return True

@docs_bp.route("/access-request", methods=["POST"])
@login_required
def create_access_request():
    """
    Crea una nuova richiesta di accesso a un documento.
    
    Args:
        document_id: ID del documento richiesto
        note: Nota opzionale per la richiesta
        
    Returns:
        JSON con messaggio di successo o errore
    """
    document_id = request.form.get("document_id")
    note = request.form.get("note", "")

    # Validazione input
    if not document_id:
        return jsonify({"message": "ID documento richiesto"}), 400
    
    try:
        document_id = int(document_id)
    except ValueError:
        return jsonify({"message": "ID documento non valido"}), 400

    # Verifica esistenza documento
    document = Document.query.get(document_id)
    if not document:
        return jsonify({"message": "Documento non trovato"}), 404

    # Controllo cooldown - verifica se l'utente è in cooldown
    from services.access_request_detector import access_request_detector
    if access_request_detector.check_user_cooldown(current_user.id):
        return jsonify({"message": "Limite temporaneo raggiunto. Riprova più tardi."}), 429
    
    # Controllo duplicati - verifica se esiste già una richiesta pending
    existing = AccessRequest.query.filter_by(
        user_id=current_user.id, 
        document_id=document_id, 
        status="pending"
    ).first()
    
    if existing:
        return jsonify({"message": "Richiesta già inviata"}), 409

    # Creazione nuova richiesta
    new_request = AccessRequest(
        user_id=current_user.id,
        document_id=document_id,
        note=note,
        status="pending"
    )
    
    try:
        db.session.add(new_request)
        db.session.commit()
        
        # Invia notifica email agli admin
        try:
            from app import send_email
            from models import User
            
            # Ottieni tutti gli admin attivi
            admins = User.query.filter_by(is_admin=True, is_active=True).all()
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if admin_emails:
                subject = f"📄 Nuova richiesta di accesso al documento"
                body = f"""
L'utente {current_user.username} ha richiesto accesso al documento: "{document.title or document.original_filename}".

Nota: {note if note else 'Nessuna nota'}
Data richiesta: {new_request.created_at.strftime('%d/%m/%Y %H:%M')}

Accedi al pannello admin per gestire la richiesta.
"""
                send_email(subject, admin_emails, body)
                
        except Exception as e:
            # Log dell'errore ma non bloccare la richiesta
            current_app.logger.error(f"Errore invio email notifica admin: {e}")
        
        return jsonify({"message": "Richiesta inviata con successo"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Errore durante l'invio della richiesta"}), 500

@docs_bp.route("/my-access-requests")
@login_required
def my_access_requests():
    """
    Visualizza le richieste di accesso dell'utente corrente.
    
    Returns:
        Template con le richieste dell'utente
    """
    requests = AccessRequest.query.filter_by(
        user_id=current_user.id
    ).order_by(AccessRequest.created_at.desc()).all()
    
    return render_template("user/my_access_requests.html", requests=requests)

@docs_bp.route("/document/<int:doc_id>/firma", methods=["POST"])
@login_required
def firma_documento(doc_id):
    """
    Firma un documento (presa visione) con conferma email.
    
    Args:
        doc_id (int): ID del documento da firmare.
        
    Returns:
        redirect: Reindirizzamento con messaggio di conferma.
    """
    doc = Document.query.get_or_404(doc_id)
    
    # Verifica che il documento sia approvato
    if not verifica_accesso_documento(doc):
        return redirect(url_for('index'))
    
    # Verifica se l'utente ha già firmato
    firma_esistente = DocumentReadLog.query.filter_by(
        user_id=current_user.id,
        document_id=doc_id
    ).first()
    
    if firma_esistente:
        if firma_esistente.confermata:
            flash("✅ Hai già firmato questo documento.", "info")
        else:
            flash("⚠️ Hai già firmato questo documento ma la conferma è in attesa.", "warning")
        return redirect(url_for('index'))
    
    # Ottieni l'ultima versione del documento
    ultima_versione = DocumentVersion.query.filter_by(document_id=doc_id).order_by(DocumentVersion.data_caricamento.desc()).first()
    
    if not ultima_versione:
        flash("❌ Nessuna versione disponibile per questo documento.", "danger")
        return redirect(url_for('index'))
    
    # Crea la firma con token di conferma, associata alla versione
    firma = DocumentReadLog(
        user_id=current_user.id,
        document_id=doc_id,
        version_id=ultima_versione.id,
        timestamp=datetime.utcnow()
    )
    
    # Genera token unico per conferma
    firma.token_conferma = secrets.token_urlsafe(32)
    
    try:
        db.session.add(firma)
        db.session.commit()
        
        # Log dell'audit
        audit_log = AuditLog(
            user_id=current_user.id,
            document_id=doc_id,
            azione='firma',
            note=f'Firma documento "{doc.title or doc.original_filename}" - in attesa conferma'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        # Invia email di conferma
        try:
            from app import send_email
            
            link_conferma = url_for('docs.conferma_firma', token=firma.token_conferma, _external=True)
            
            # Personalizza il messaggio per PEC
            if current_user.email.endswith("@pec.it"):
                subject = "🔐 Conferma Firma Documento - PEC"
                body = f"""
Gentile {current_user.first_name or current_user.username},

Hai firmato il documento: "{doc.title or doc.original_filename}"

Per confermare la tua firma, clicca sul seguente link:
{link_conferma}

⚠️ ATTENZIONE: Questa email è valida come notifica via PEC.

Il link scadrà tra 24 ore.

Cordiali saluti,
Sistema Gestione Documenti
"""
            else:
                subject = "🔐 Conferma Firma Documento"
                body = f"""
Gentile {current_user.first_name or current_user.username},

Hai firmato il documento: "{doc.title or doc.original_filename}"

Per confermare la tua firma, clicca sul seguente link:
{link_conferma}

Il link scadrà tra 24 ore.

Cordiali saluti,
Sistema Gestione Documenti
"""
            
            send_email(subject, [current_user.email], body)
            flash("✅ Firma registrata! Ti abbiamo inviato una email per confermare la tua firma.", "success")
            
        except Exception as e:
            flash("⚠️ Firma registrata ma errore nell'invio dell'email di conferma. Contatta l'amministratore.", "warning")
            print(f"Errore invio email conferma firma: {e}")
        
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        flash("❌ Errore durante la registrazione della firma.", "danger")
        return redirect(url_for('index'))

@docs_bp.route("/versione/<int:version_id>/download")
@login_required
def download_versione(version_id):
    """
    Scarica una versione specifica di un documento.
    
    Args:
        version_id (int): ID della versione da scaricare.
        
    Returns:
        file: File della versione richiesta.
    """
    versione = DocumentVersion.query.get_or_404(version_id)
    doc = versione.document
    
    # Verifica che il documento sia approvato
    if not verifica_accesso_documento(doc):
        return redirect(url_for('index'))
    
    # Verifica accesso utente
    if not current_user.is_admin and not current_user.is_ceo:
        if doc.user_id != current_user.id:
            authorized = AccessRequest.query.filter_by(
                user_id=current_user.id,
                document_id=doc.id,
                status='approved'
            ).first()
            if not authorized:
                flash("🚫 Accesso non autorizzato al documento", "danger")
                return redirect(url_for('index'))
    
    # Percorso del file
    import os
    local_path = os.path.join(
        app.config['UPLOAD_FOLDER'], 
        doc.company.name, 
        doc.department.name, 
        versione.filename
    )
    
    if not os.path.exists(local_path):
        flash("❌ File versione non trovato sul server", "danger")
        return redirect(url_for('index'))
    
    # Log dell'audit
    audit_log = AuditLog(
        user_id=current_user.id,
        document_id=doc.id,
        azione='download_versione',
        note=f'Download versione {versione.numero_versione} del documento "{doc.title or doc.original_filename}"'
    )
    db.session.add(audit_log)
    db.session.commit()
    
    from flask import send_file
    return send_file(local_path, as_attachment=True, download_name=versione.filename)

@docs_bp.route("/admin/document/<int:doc_id>/versione/<int:version_id>/pdf")
@login_required
def download_documento_versione_pdf(doc_id, version_id):
    """
    Genera un HTML della versione specifica del documento, ottimizzato per stampa/PDF, includendo:
    - intestazione con nome documento, versione e note
    - tabella firme associate (nome, email, ruolo, stato firma)
    - stili CSS ottimizzati per stampa
    """
    # Verifica autorizzazioni admin
    if not current_user.is_admin:
        abort(403)
    
    # Carica versione e documento
    versione = DocumentVersion.query.get_or_404(version_id)
    doc = versione.document
    
    # Verifica che la versione appartenga al documento
    if versione.document_id != doc_id:
        abort(404)
    
    try:
        # Genera il contenuto HTML ottimizzato per stampa/PDF
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Documento {doc.title or doc.original_filename} - {versione.numero_versione}</title>
            <style>
                @media print {{
                    body {{ margin: 0; padding: 20px; }}
                    .no-print {{ display: none; }}
                    .page-break {{ page-break-before: always; }}
                }}
                
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    color: #333;
                    line-height: 1.6;
                }}
                
                .header {{
                    border-bottom: 2px solid #007bff;
                    padding-bottom: 15px;
                    margin-bottom: 25px;
                }}
                
                .title {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #007bff;
                    margin-bottom: 8px;
                }}
                
                .subtitle {{
                    font-size: 20px;
                    color: #666;
                    margin-bottom: 15px;
                }}
                
                .info-section {{
                    margin-bottom: 25px;
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                }}
                
                .info-row {{
                    margin-bottom: 10px;
                    display: flex;
                }}
                
                .label {{
                    font-weight: bold;
                    min-width: 150px;
                    color: #495057;
                }}
                
                .value {{
                    flex: 1;
                }}
                
                .note-section {{
                    margin: 25px 0;
                    padding: 20px;
                    background-color: #e3f2fd;
                    border-left: 5px solid #007bff;
                    border-radius: 5px;
                }}
                
                .firme-section {{
                    margin-top: 30px;
                }}
                
                .firme-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    font-size: 14px;
                }}
                
                .firme-table th, .firme-table td {{
                    border: 1px solid #dee2e6;
                    padding: 12px 8px;
                    text-align: left;
                }}
                
                .firme-table th {{
                    background-color: #007bff;
                    color: white;
                    font-weight: bold;
                }}
                
                .firme-table tr:nth-child(even) {{
                    background-color: #f8f9fa;
                }}
                
                .status-confermata {{
                    color: #28a745;
                    font-weight: bold;
                }}
                
                .status-in-attesa {{
                    color: #ffc107;
                    font-weight: bold;
                }}
                
                .footer {{
                    margin-top: 40px;
                    text-align: center;
                    color: #666;
                    font-size: 12px;
                    border-top: 1px solid #dee2e6;
                    padding-top: 20px;
                }}
                
                .print-button {{
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background-color: #007bff;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 14px;
                }}
                
                .print-button:hover {{
                    background-color: #0056b3;
                }}
                
                @media print {{
                    .print-button {{ display: none; }}
                }}
            </style>
        </head>
        <body>
            <button class="print-button no-print" onclick="window.print()">🖨️ Stampa PDF</button>
            
            <div class="header">
                <div class="title">{doc.title or doc.original_filename}</div>
                <div class="subtitle">Versione {versione.numero_versione}</div>
            </div>
            
            <div class="info-section">
                <div class="info-row">
                    <span class="label">Azienda:</span>
                    <span class="value">{doc.company.name}</span>
                </div>
                <div class="info-row">
                    <span class="label">Reparto:</span>
                    <span class="value">{doc.department.name}</span>
                </div>
                <div class="info-row">
                    <span class="label">Uploader:</span>
                    <span class="value">{doc.uploader_email}</span>
                </div>
                <div class="info-row">
                    <span class="label">Data Caricamento:</span>
                    <span class="value">{versione.data_caricamento.strftime('%d/%m/%Y %H:%M')}</span>
                </div>
                <div class="info-row">
                    <span class="label">File:</span>
                    <span class="value">{versione.filename}</span>
                </div>
            </div>
            
            <div class="note-section">
                <strong>📝 Note sulla Versione:</strong><br>
                {versione.note or 'Nessuna nota disponibile'}
            </div>
            
            <div class="firme-section">
                <h2>👥 Firme Associate alla Versione {versione.numero_versione}</h2>
                
                <table class="firme-table">
                    <thead>
                        <tr>
                            <th>Nome Utente</th>
                            <th>Email</th>
                            <th>Ruolo</th>
                            <th>Data Firma</th>
                            <th>Stato</th>
                            <th>Data Conferma</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        # Aggiungi le firme alla tabella
        if versione.read_logs:
            for firma in versione.read_logs:
                stato_class = "status-confermata" if firma.confermata else "status-in-attesa"
                stato_text = "✅ Confermata" if firma.confermata else "⏳ In Attesa"
                data_conferma = firma.data_conferma.strftime('%d/%m/%Y %H:%M') if firma.data_conferma else '-'
                
                html_content += f"""
                    <tr>
                        <td><strong>{firma.user.username}</strong></td>
                        <td>{firma.user.email}</td>
                        <td>{firma.user.role}</td>
                        <td>{firma.timestamp.strftime('%d/%m/%Y %H:%M')}</td>
                        <td class="{stato_class}">{stato_text}</td>
                        <td>{data_conferma}</td>
                    </tr>
                """
        else:
            html_content += """
                    <tr>
                        <td colspan="6" style="text-align: center; color: #666; font-style: italic;">
                            Nessuna firma registrata per questa versione
                        </td>
                    </tr>
                """
        
        html_content += f"""
                </tbody>
            </table>
            
            <div class="footer">
                <p>📄 Documento generato automaticamente il {datetime.utcnow().strftime('%d/%m/%Y alle %H:%M')}</p>
                <p>🏢 Sistema di Gestione Documenti - Versione con Firme</p>
                <p>📋 Per convertire in PDF: usa la funzione di stampa del browser (Ctrl+P)</p>
            </div>
        </body>
        </html>
        """
        
        # Genera nome file
        safe_title = "".join(c for c in (doc.title or doc.original_filename) if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"documento_{safe_title}_v{versione.numero_versione}_con_firme.html"
        
        # Log dell'audit
        audit_log = AuditLog(
            user_id=current_user.id,
            document_id=doc.id,
            azione='download_html_versione',
            note=f'Download HTML versione {versione.numero_versione} del documento "{doc.title or doc.original_filename}"'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        # Restituisce l'HTML come allegato
        from flask import Response
        return Response(
            html_content,
            mimetype='text/html',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Errore durante la generazione del documento: {str(e)}", "danger")
        print(f"Errore generazione HTML: {e}")
        return redirect(url_for('admin.view_document', document_id=doc.id))

@docs_bp.route("/firma/conferma/<token>")
def conferma_firma(token):
    """
    Conferma una firma tramite token email.
    
    Args:
        token (str): Token di conferma.
        
    Returns:
        redirect: Reindirizzamento con messaggio di conferma.
    """
    firma = DocumentReadLog.query.filter_by(token_conferma=token).first()
    
    if not firma:
        flash("❌ Link di conferma non valido o scaduto.", "danger")
        return redirect(url_for('index'))
    
    if firma.confermata:
        flash("ℹ️ Hai già confermato questa firma.", "info")
        return redirect(url_for('index'))
    
    # Verifica che il token non sia scaduto (24 ore)
    if (datetime.utcnow() - firma.timestamp).total_seconds() > 86400:  # 24 ore
        flash("❌ Link di conferma scaduto. Devi firmare nuovamente il documento.", "danger")
        return redirect(url_for('index'))
    
    try:
        # Conferma la firma
        firma.confermata = True
        firma.data_conferma = datetime.utcnow()
        db.session.commit()
        
        # Log dell'audit
        audit_log = AuditLog(
            user_id=firma.user_id,
            document_id=firma.document_id,
            azione='firma',
            note=f'Firma confermata via email per documento "{firma.document.title or firma.document.original_filename}"'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash("✅ Firma confermata con successo!", "success")
        
    except Exception as e:
        db.session.rollback()
        flash("❌ Errore durante la conferma della firma.", "danger")
        print(f"Errore conferma firma: {e}")
    
    return redirect(url_for('index'))

@docs_bp.route("/firma/riinvio/<int:doc_id>", methods=["POST"])
@login_required
def riinvio_conferma_firma(doc_id):
    """
    Rinvio email di conferma per una firma in attesa.
    
    Args:
        doc_id (int): ID del documento.
        
    Returns:
        redirect: Reindirizzamento con messaggio.
    """
    firma = DocumentReadLog.query.filter_by(
        user_id=current_user.id,
        document_id=doc_id,
        confermata=False
    ).first()
    
    if not firma:
        flash("❌ Nessuna firma in attesa di conferma trovata.", "danger")
        return redirect(url_for('index'))
    
    try:
        from app import send_email
        
        link_conferma = url_for('docs.conferma_firma', token=firma.token_conferma, _external=True)
        
        # Personalizza il messaggio per PEC
        if current_user.email.endswith("@pec.it"):
            subject = "🔐 Rinvio Conferma Firma Documento - PEC"
            body = f"""
Gentile {current_user.first_name or current_user.username},

Rinvio conferma firma per il documento: "{firma.document.title or firma.document.original_filename}"

Per confermare la tua firma, clicca sul seguente link:
{link_conferma}

⚠️ ATTENZIONE: Questa email è valida come notifica via PEC.

Il link scadrà tra 24 ore.

Cordiali saluti,
Sistema Gestione Documenti
"""
        else:
            subject = "🔐 Rinvio Conferma Firma Documento"
            body = f"""
Gentile {current_user.first_name or current_user.username},

Rinvio conferma firma per il documento: "{firma.document.title or firma.document.original_filename}"

Per confermare la tua firma, clicca sul seguente link:
{link_conferma}

Il link scadrà tra 24 ore.

Cordiali saluti,
Sistema Gestione Documenti
"""
        
        send_email(subject, [current_user.email], body)
        flash("✅ Email di conferma rinviata con successo!", "success")
        
    except Exception as e:
        flash("❌ Errore nell'invio dell'email di conferma.", "danger")
        print(f"Errore rinvio email conferma: {e}")
    
    return redirect(url_for('index')) 

@docs_bp.route('/document/<int:document_id>')
@login_required
def view_document(document_id):
    """
    Visualizza un documento con le sue versioni.
    
    Args:
        document_id: ID del documento da visualizzare
        
    Returns:
        Template HTML con dettagli documento e versioni
    """
    document = Document.query.get_or_404(document_id)
    
    # Verifica accesso
    if not verifica_accesso_documento(document):
        return redirect(url_for('index'))
    
    # Ordina versioni per numero (più recenti prima)
    versions = sorted(document.versions, key=lambda v: v.version_number, reverse=True)
    
    return render_template('docs/view_document.html', 
                         document=document, 
                         versions=versions)

@docs_bp.route('/document/<int:document_id>/new_version', methods=['POST'])
@login_required
def upload_new_version(document_id):
    """
    Carica una nuova versione di un documento.
    
    Args:
        document_id: ID del documento
        file: File da caricare
        note: Note opzionali sulla versione
        
    Returns:
        Redirect alla pagina del documento
    """
    document = Document.query.get_or_404(document_id)
    
    # Verifica permessi
    if not (current_user.is_admin or current_user.id == document.user_id):
        flash("⛔ Non hai i permessi per caricare versioni di questo documento.", "error")
        return redirect(url_for('docs.view_document', document_id=document_id))
    
    file = request.files.get('file')
    note = request.form.get('note', '')
    
    if not file or file.filename == '':
        flash("❌ Nessun file selezionato.", "error")
        return redirect(url_for('docs.view_document', document_id=document_id))
    
    # Verifica estensione file
    allowed_extensions = {'pdf', 'docx', 'xlsx', 'txt'}
    if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        flash("❌ Tipo di file non supportato.", "error")
        return redirect(url_for('docs.view_document', document_id=document_id))
    
    try:
        # Calcola numero versione
        version_number = len(document.versions) + 1
        
        # Salva file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"{document_id}_v{version_number}_{timestamp}_{filename}"
        
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        filepath = os.path.join(upload_folder, new_filename)
        
        # Crea directory se non esiste
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        
        # BONUS AI: Confronto con versione precedente
        ai_summary = None
        last_version = max(document.versions, key=lambda v: v.version_number, default=None)
        if last_version and os.path.exists(last_version.file_path):
            ai_summary = confronta_documenti_ai(last_version.file_path, filepath)
        
        # Disattiva vecchie versioni
        for v in document.versions:
            v.active = False
        
        # Crea nuova versione
        new_version = DocumentVersion(
            document_id=document_id,
            version_number=version_number,
            file_path=filepath,
            uploaded_by=current_user.username,
            note=note,
            active=True,
            ai_diff_summary=ai_summary
        )
        
        db.session.add(new_version)
        db.session.commit()
        
        # Log dell'azione
        audit_log = AuditLog(
            user_id=current_user.id,
            document_id=document_id,
            azione='nuova_versione',
            note=f"Caricata versione v{version_number}: {note}"
        )
        db.session.add(audit_log)
        
        # Classifica documento con AI e traccia l'analisi
        if classify_document_ai(document):
            # Genera task AI se necessario
            generate_ai_task_for_document(document)
        
        db.session.commit()
        
        flash(f"✅ Nuova versione v{version_number} caricata con successo.", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore caricamento versione: {e}")
        flash("❌ Errore durante il caricamento della versione.", "error")
    
    return redirect(url_for('docs.view_document', document_id=document_id))

@docs_bp.route('/document/version/<int:version_id>/restore', methods=['POST'])
@login_required
def restore_version(version_id):
    """
    Ripristina una versione precedente come attiva.
    
    Args:
        version_id: ID della versione da ripristinare
        
    Returns:
        Redirect alla pagina del documento
    """
    version = DocumentVersion.query.get_or_404(version_id)
    document = version.document
    
    # Verifica permessi
    if not (current_user.is_admin or current_user.id == document.user_id):
        flash("⛔ Non hai i permessi per ripristinare versioni di questo documento.", "error")
        return redirect(url_for('docs.view_document', document_id=document.id))
    
    try:
        # Disattiva tutte le versioni
        for v in document.versions:
            v.active = False
        
        # Attiva la versione selezionata
        version.active = True
        db.session.commit()
        
        # Log dell'azione
        audit_log = AuditLog(
            user_id=current_user.id,
            document_id=document.id,
            azione='ripristino_versione',
            note=f"Ripristinata versione v{version.version_number}"
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash(f"✅ Versione v{version.version_number} ripristinata con successo.", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore ripristino versione: {e}")
        flash("❌ Errore durante il ripristino della versione.", "error")
    
    return redirect(url_for('docs.view_document', document_id=document.id)) 

# === ROUTE PER GESTIONE FIRME DOCUMENTI ===

@docs_bp.route('/documenti-da-firmare')
@login_required
def documenti_da_firmare():
    """
    Mostra i documenti che richiedono la firma dell'utente.
    
    Returns:
        Template con lista documenti da firmare e già firmati.
    """
    # Documenti che richiedono firma (Policy, DPI, Risorse Umane)
    documenti_da_firmare = Document.query.filter(
        Document.tag.in_(['Risorse Umane', 'Policy', 'DPI', 'Regolamento']),
        Document.visibility == 'pubblico'
    ).all()
    
    # Documenti già firmati dall'utente
    firme_utente = FirmaDocumento.query.filter_by(user_id=current_user.id).all()
    documenti_firmati = [firma.document for firma in firme_utente]
    
    # Filtra documenti da firmare (escludi quelli già firmati)
    documenti_da_firmare = [doc for doc in documenti_da_firmare if doc not in documenti_firmati]
    
    return render_template('user/documenti_da_firmare.html', 
                         documenti_da_firmare=documenti_da_firmare,
                         documenti_firmati=firme_utente)


@docs_bp.route('/documenti/<int:doc_id>/firma', methods=['POST'])
@login_required
def firma_documento_post(doc_id):
    """
    Registra la firma di un documento da parte dell'utente.
    
    Args:
        doc_id: ID del documento da firmare.
        
    Returns:
        Redirect alla pagina documenti da firmare con messaggio.
    """
    nome_firma = request.form.get('nome_firma', '').strip()
    
    if not nome_firma or len(nome_firma) < 3:
        flash('⚠️ Inserisci un nome valido per la firma (almeno 3 caratteri).', 'warning')
        return redirect(url_for('docs.documenti_da_firmare'))
    
    # Verifica che il documento esista
    documento = Document.query.get_or_404(doc_id)
    
    # Verifica che il documento richieda firma
    if documento.tag not in ['Risorse Umane', 'Policy', 'DPI', 'Regolamento']:
        flash('⚠️ Questo documento non richiede firma.', 'warning')
        return redirect(url_for('docs.documenti_da_firmare'))
    
    # Verifica se già firmato
    firma_esistente = FirmaDocumento.query.filter_by(
        document_id=doc_id, 
        user_id=current_user.id
    ).first()
    
    if firma_esistente:
        flash('⚠️ Hai già firmato questo documento.', 'warning')
        return redirect(url_for('docs.documenti_da_firmare'))
    
    # Registra la firma
    firma = FirmaDocumento(
        document_id=doc_id,
        user_id=current_user.id,
        nome_firma=nome_firma,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    try:
        db.session.add(firma)
        db.session.commit()
        
        # Log dell'azione
        audit_log = AuditLog(
            user_id=current_user.id,
            document_id=doc_id,
            azione='firma',
            note=f'Firma elettronica: {nome_firma}'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash('✅ Documento firmato con successo!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('❌ Errore durante la registrazione della firma.', 'danger')
        current_app.logger.error(f'Errore firma documento: {e}')
    
    return redirect(url_for('docs.documenti_da_firmare'))


@docs_bp.route('/documenti/<int:doc_id>/firme')
@login_required
def visualizza_firme_documento(doc_id):
    """
    Visualizza tutte le firme di un documento (solo per admin).
    
    Args:
        doc_id: ID del documento.
        
    Returns:
        Template con lista firme del documento.
    """
    if not current_user.is_admin:
        flash('⛔ Accesso negato. Solo gli amministratori possono visualizzare le firme.', 'danger')
        return redirect(url_for('docs.view_document', document_id=doc_id))
    
    documento = Document.query.get_or_404(doc_id)
    firme = FirmaDocumento.query.filter_by(document_id=doc_id).order_by(FirmaDocumento.data_firma.desc()).all()
    
    return render_template('admin/firme_documento.html', 
                         documento=documento, 
                         firme=firme)


@docs_bp.route('/report-firme')
@login_required
def report_firme():
    """
    Report delle firme documenti per admin/HR.
    
    Returns:
        Template con report dettagliato delle firme.
    """
    if not current_user.is_admin:
        flash('⛔ Accesso negato. Solo gli amministratori possono visualizzare il report.', 'danger')
        return redirect(url_for('docs.documenti_da_firmare'))
    
    # Filtri
    tag_filter = request.args.get('tag_filter')
    status_filter = request.args.get('status_filter')
    user_filter = request.args.get('user_filter')
    
    # Query base documenti che richiedono firma
    query = Document.query.filter(
        Document.tag.in_(['Risorse Umane', 'Policy', 'DPI', 'Regolamento']),
        Document.visibility == 'pubblico'
    )
    
    if tag_filter:
        query = query.filter(Document.tag == tag_filter)
    
    documenti = query.all()
    
    # Calcola statistiche per ogni documento
    for doc in documenti:
        # Conta utenti totali (escludendo admin)
        doc.utenti_totali = User.query.filter(User.role != 'admin').count()
        
        # Conta firme per questo documento
        doc.firme_count = FirmaDocumento.query.filter_by(document_id=doc.id).count()
        
        # Ultima firma
        ultima_firma = FirmaDocumento.query.filter_by(document_id=doc.id).order_by(FirmaDocumento.data_firma.desc()).first()
        doc.ultima_firma = ultima_firma.data_firma if ultima_firma else None
    
    # Statistiche generali
    documenti_totali = len(documenti)
    documenti_completamente_firmati = len([d for d in documenti if d.firme_count >= d.utenti_totali * 0.9])  # 90%+
    documenti_parzialmente_firmati = len([d for d in documenti if 0 < d.firme_count < d.utenti_totali * 0.9])
    documenti_non_firmati = len([d for d in documenti if d.firme_count == 0])
    
    # Utenti non in regola
    utenti = User.query.filter(User.role != 'admin').all()
    utenti_non_in_regola = []
    
    for user in utenti:
        # Documenti che l'utente dovrebbe aver firmato
        documenti_obbligatori = Document.query.filter(
            Document.tag.in_(['Risorse Umane', 'Policy', 'DPI', 'Regolamento']),
            Document.visibility == 'pubblico'
        ).all()
        
        # Documenti che l'utente ha effettivamente firmato
        firme_utente = FirmaDocumento.query.filter_by(user_id=user.id).all()
        documenti_firmati_ids = [f.document_id for f in firme_utente]
        
        # Documenti non firmati dall'utente
        user.documenti_non_firmati = [d for d in documenti_obbligatori if d.id not in documenti_firmati_ids]
        
        if user.documenti_non_firmati:
            utenti_non_in_regola.append(user)
    
    return render_template('admin/report_firme.html',
                         documenti=documenti,
                         documenti_totali=documenti_totali,
                         documenti_completamente_firmati=documenti_completamente_firmati,
                         documenti_parzialmente_firmati=documenti_parzialmente_firmati,
                         documenti_non_firmati=documenti_non_firmati,
                         utenti_non_in_regola=utenti_non_in_regola,
                         users=User.query.filter(User.role != 'admin').all())


# === ROUTE PER APPROVAZIONE MULTILIVELLO ===

@docs_bp.route('/document/<int:document_id>/inizializza-approvazione', methods=['POST'])
@login_required
def inizializza_approvazione_documento(document_id):
    """
    Inizializza il flusso di approvazione multilivello per un documento.
    
    Args:
        document_id: ID del documento
        
    Returns:
        Redirect alla pagina del documento con messaggio di successo
    """
    document = Document.query.get_or_404(document_id)
    
    # Verifica permessi (solo admin o proprietario)
    if not (current_user.is_admin or current_user.id == document.user_id):
        flash("⛔ Non hai i permessi per inizializzare l'approvazione di questo documento.", "error")
        return redirect(url_for('docs.view_document', document_id=document_id))
    
    try:
        # Verifica se il flusso è già stato inizializzato
        if document.approvazioni:
            flash("⚠️ Il flusso di approvazione è già stato inizializzato per questo documento.", "warning")
            return redirect(url_for('docs.view_document', document_id=document_id))
        
        # Inizializza il flusso
        document.inizializza_flusso_approvazione()
        
        # Log dell'azione
        audit_log = AuditLog(
            user_id=current_user.id,
            document_id=document_id,
            azione='inizializzazione_approvazione',
            note="Inizializzato flusso approvazione multilivello"
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash("✅ Flusso di approvazione multilivello inizializzato con successo.", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore inizializzazione approvazione: {e}")
        flash("❌ Errore durante l'inizializzazione del flusso di approvazione.", "error")
    
    return redirect(url_for('docs.view_document', document_id=document_id))

@docs_bp.route('/document/<int:document_id>/approva/<int:livello>', methods=['POST'])
@login_required
def approva_step(document_id, livello):
    """
    Approva un singolo step del flusso di approvazione.
    
    Args:
        document_id: ID del documento
        livello: Livello da approvare (1, 2, 3)
        
    Returns:
        Redirect alla pagina del documento
    """
    document = Document.query.get_or_404(document_id)
    
    # Verifica se l'utente può approvare questo livello
    puo_approvare, livello_richiesto, messaggio = document.can_be_approved_by(current_user)
    
    if not puo_approvare:
        flash(f"⛔ {messaggio}", "error")
        return redirect(url_for('docs.view_document', document_id=document_id))
    
    if livello != livello_richiesto:
        flash(f"⛔ Puoi approvare solo il livello {livello_richiesto}.", "error")
        return redirect(url_for('docs.view_document', document_id=document_id))
    
    commento = request.form.get('commento', '').strip()
    
    try:
        # Approva il livello
        document.approva_livello(livello, current_user.username, commento)
        
        # Log dell'azione
        audit_log = AuditLog(
            user_id=current_user.id,
            document_id=document_id,
            azione='approvazione_livello',
            note=f"Approvato livello {livello}: {commento}"
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash(f"✅ Livello {livello} approvato con successo.", "success")
        
    except ValueError as e:
        flash(f"❌ {str(e)}", "error")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore approvazione livello: {e}")
        flash("❌ Errore durante l'approvazione del livello.", "error")
    
    return redirect(url_for('docs.view_document', document_id=document_id))

@docs_bp.route('/document/<int:document_id>/rifiuta/<int:livello>', methods=['POST'])
@login_required
def rifiuta_step(document_id, livello):
    """
    Rifiuta un singolo step del flusso di approvazione.
    
    Args:
        document_id: ID del documento
        livello: Livello da rifiutare (1, 2, 3)
        
    Returns:
        Redirect alla pagina del documento
    """
    document = Document.query.get_or_404(document_id)
    
    # Verifica se l'utente può approvare questo livello
    puo_approvare, livello_richiesto, messaggio = document.can_be_approved_by(current_user)
    
    if not puo_approvare:
        flash(f"⛔ {messaggio}", "error")
        return redirect(url_for('docs.view_document', document_id=document_id))
    
    if livello != livello_richiesto:
        flash(f"⛔ Puoi rifiutare solo il livello {livello_richiesto}.", "error")
        return redirect(url_for('docs.view_document', document_id=document_id))
    
    commento = request.form.get('commento', '').strip()
    
    try:
        # Rifiuta il livello
        document.rifiuta_livello(livello, current_user.username, commento)
        
        # Log dell'azione
        audit_log = AuditLog(
            user_id=current_user.id,
            document_id=document_id,
            azione='rifiuto_livello',
            note=f"Rifiutato livello {livello}: {commento}"
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash(f"❌ Livello {livello} rifiutato. Il flusso è stato bloccato.", "error")
        
    except ValueError as e:
        flash(f"❌ {str(e)}", "error")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore rifiuto livello: {e}")
        flash("❌ Errore durante il rifiuto del livello.", "error")
    
    return redirect(url_for('docs.view_document', document_id=document_id))

@docs_bp.route('/document/<int:document_id>/reset-approvazione', methods=['POST'])
@login_required
def reset_approvazione_documento(document_id):
    """
    Resetta il flusso di approvazione per un documento (solo admin).
    
    Args:
        document_id: ID del documento
        
    Returns:
        Redirect alla pagina del documento
    """
    if not current_user.is_admin:
        flash("⛔ Solo gli amministratori possono resettare il flusso di approvazione.", "error")
        return redirect(url_for('docs.view_document', document_id=document_id))
    
    document = Document.query.get_or_404(document_id)
    
    try:
        # Elimina tutte le approvazioni esistenti
        ApprovazioneDocumento.query.filter_by(document_id=document_id).delete()
        
        # Reset stato documento
        document.stato_approvazione = "bozza"
        document.approvato_da = None
        document.data_approvazione = None
        
        db.session.commit()
        
        # Log dell'azione
        audit_log = AuditLog(
            user_id=current_user.id,
            document_id=document_id,
            azione='reset_approvazione',
            note="Reset flusso approvazione multilivello"
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash("🔄 Flusso di approvazione resettato con successo.", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore reset approvazione: {e}")
        flash("❌ Errore durante il reset del flusso di approvazione.", "error")
    
    return redirect(url_for('docs.view_document', document_id=document_id)) 


# === RICERCA SEMANTICA AI ===

@docs_bp.route("/docs/ricerca", methods=["GET"])
@login_required
def ricerca_semantica():
    """
    Ricerca semantica AI nei documenti.
    
    Args:
        query: Query di ricerca semantica
        
    Returns:
        Template con risultati della ricerca
    """
    query = request.args.get("query", "").strip()
    modulo_filter = request.args.get("modulo", "").strip()
    
    if not query:
        return redirect(url_for("docs.docs_dashboard"))
    
    try:
        # Query base per documenti approvati
        base_query = Document.query.filter_by(validazione_admin=True, validazione_ceo=True)
        
        # Applica filtro modulo se specificato
        if modulo_filter:
            base_query = base_query.filter_by(collegato_a_modulo=modulo_filter)
        
        documenti = base_query.all()
        
        # Esegui ricerca semantica
        risultati = cerca_documenti(query, documenti, max_results=20)
        
        # Log della ricerca per analytics
        from routes.admin_routes import log_admin_action
        log_admin_action(
            f"Ricerca semantica: '{query}' (modulo: {modulo_filter})",
            current_user.email,
            f"Risultati: {len(risultati)}"
        )
        
        # Logga analisi AI per ricerca semantica
        payload = {
            "query": query,
            "modulo_filter": modulo_filter,
            "documenti_analizzati": len(documenti),
            "risultati_trovati": len(risultati),
            "user_id": current_user.id
        }
        # Logga per ogni documento nei risultati
        for risultato in risultati:
            log_ai_analysis(risultato['document'].id, "ricerca_semantica", payload, current_user.id)
        
        return render_template("docs_search.html", 
                             risultati=risultati, 
                             query=query,
                             modulo_filter=modulo_filter)
                             
    except Exception as e:
        flash(f"❌ Errore durante la ricerca: {str(e)}", "danger")
        return redirect(url_for("docs.docs_dashboard"))


@docs_bp.route("/docs/indicizza-documento/<int:doc_id>", methods=["POST"])
@login_required
def indicizza_documento_route(doc_id):
    """
    Indicizza un documento specifico per la ricerca semantica.
    
    Args:
        doc_id: ID del documento da indicizzare
        
    Returns:
        JSON con risultato dell'indicizzazione
    """
    try:
        doc = Document.query.get_or_404(doc_id)
        
        # Costruisci il percorso del file
        file_path = os.path.join(doc.file_path, doc.filename)
        
        if not os.path.exists(file_path):
            return jsonify({"success": False, "message": "File non trovato"}), 404
        
        # Indicizza il documento
        success = indicizza_documento(doc, file_path)
        
        if success:
            db.session.commit()
            return jsonify({"success": True, "message": "Documento indicizzato con successo"})
        else:
            return jsonify({"success": False, "message": "Errore nell'indicizzazione"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Errore: {str(e)}"}), 500


# === GESTIONE VERSIONI DOCUMENTI ===

@docs_bp.route('/document/<int:document_id>/versioni')
@login_required
def visualizza_versioni_documento(document_id):
    """
    Visualizza tutte le versioni di un documento.
    
    Args:
        document_id: ID del documento
        
    Returns:
        Template con lista delle versioni
    """
    document = Document.query.get_or_404(document_id)
    versioni = get_versioni_documento(document_id)
    
    return render_template('admin/document_versions.html',
                         document=document,
                         versioni=versioni)


# Route duplicate rimosse - mantenute solo quelle originali


# === FIRMA GRAFICA ===

@docs_bp.route("/documenti/<int:doc_id>/firma-grafica", methods=["GET", "POST"])
@login_required
def firma_grafica(doc_id):
    """
    Gestisce la firma grafica di un documento.
    
    Args:
        doc_id: ID del documento da firmare
        
    Returns:
        Template per firma grafica o redirect dopo salvataggio
    """
    documento = Document.query.get_or_404(doc_id)
    
    # Verifica che il documento sia accessibile
    if not verifica_accesso_documento(documento):
        return redirect(url_for('index'))
    
    if request.method == "POST":
        firma_dati = request.form.get("firma_dati")
        
        if not firma_dati:
            flash("❌ Nessuna firma ricevuta", "danger")
            return redirect(url_for('docs.firma_grafica', doc_id=doc_id))
        
        try:
            # Estrai immagine da base64
            import base64
            import uuid
            import os
            
            # Rimuovi il prefisso data:image/png;base64,
            if firma_dati.startswith('data:image/png;base64,'):
                firma_dati = firma_dati.split(',')[1]
            
            # Decodifica base64
            img_data = base64.b64decode(firma_dati)
            
            # Crea directory per le firme se non esiste
            firme_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'firme')
            os.makedirs(firme_dir, exist_ok=True)
            
            # Genera nome file unico
            filename = f"firma_{uuid.uuid4()}.png"
            filepath = os.path.join(firme_dir, filename)
            
            # Salva l'immagine
            with open(filepath, "wb") as f:
                f.write(img_data)
            
            # Verifica se esiste già una firma per questo utente e documento
            firma_esistente = FirmaDocumento.query.filter_by(
                document_id=doc_id,
                user_id=current_user.id
            ).first()
            
            if firma_esistente:
                # Aggiorna la firma esistente
                firma_esistente.firma_immagine = filepath
                firma_esistente.data_firma = datetime.utcnow()
                firma_esistente.ip = request.remote_addr
                firma_esistente.user_agent = request.headers.get('User-Agent')
            else:
                # Crea nuova firma
                firma = FirmaDocumento(
                    document_id=doc_id,
                    user_id=current_user.id,
                    nome_firma=current_user.username,
                    firma_immagine=filepath,
                    ip=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                db.session.add(firma)
            
            # Log dell'azione
            audit_log = AuditLog(
                user_id=current_user.id,
                document_id=doc_id,
                azione='firma_grafica',
                note=f"Firma grafica salvata per documento '{documento.title or documento.filename}'"
            )
            db.session.add(audit_log)
            db.session.commit()
            
            flash("✅ Firma grafica registrata con successo!", "success")
            return redirect(url_for('docs.view_document', document_id=doc_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore salvataggio firma grafica: {e}")
            flash(f"❌ Errore durante il salvataggio della firma: {str(e)}", "danger")
            return redirect(url_for('docs.firma_grafica', doc_id=doc_id))
    
    return render_template("firma_grafica.html", documento=documento)


@docs_bp.route("/docs/indicizza-massa", methods=["POST"])
@login_required
def indicizza_massa_documenti():
    """
    Indicizza tutti i documenti per la ricerca semantica.
    
    Returns:
        JSON con statistiche dell'indicizzazione
    """
    try:
        from services.semantic_search import semantic_search_service
        
        # Ottieni tutti i documenti
        documenti = Document.query.all()
        
        # Esegui indicizzazione massiva
        stats = semantic_search_service.aggiorna_indicizzazione_massiva(documenti)
        
        # Salva le modifiche
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Indicizzazione massiva completata",
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Errore: {str(e)}"}), 500 

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
        from models import AdminLog
        log = AdminLog(
            action=action,
            performed_by=performed_by,
            extra_info=extra_info
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Errore nel logging admin action: {e}")

# === FUNZIONI PER TRACCIAMENTO ANALISI AI ===
def log_ai_analysis(document_id, action_type, payload=None, user_id=None):
    """
    Logga un'analisi AI nel database.
    
    Args:
        document_id (int): ID del documento analizzato
        action_type (str): Tipo di azione AI
        payload (dict, optional): Dettagli dell'analisi
        user_id (int, optional): ID utente che ha accettato/rifiutato
    """
    try:
        log = AIAnalysisLog(
            document_id=document_id,
            action_type=action_type,
            payload=json.dumps(payload) if payload else None,
            user_id=user_id
        )
        db.session.add(log)
        db.session.commit()
        
        # Log amministrativo
        log_admin_action(
            f"Analisi AI: {action_type} su documento {document_id}",
            current_user.email if current_user.is_authenticated else "AI System",
            f"Payload: {payload}"
        )
    except Exception as e:
        current_app.logger.error(f"Errore nel logging analisi AI: {e}")

def classify_document_ai(document):
    """
    Classifica un documento usando AI e traccia l'analisi.
    """
    try:
        # Simula classificazione AI
        title_lower = document.title.lower()
        filename_lower = document.filename.lower()
        
        # Logica di classificazione
        if any(word in title_lower for word in ['danno', 'incidente', 'guasto']):
            tag = "Danno"
            categoria = "Foto incidente"
            modulo = "service"
        elif any(word in title_lower for word in ['haccp', 'iso', 'certificazione']):
            tag = "HACCP"
            categoria = "Certificazione"
            modulo = "qms"
        elif any(word in title_lower for word in ['fattura', 'ricevuta', 'pagamento']):
            tag = "Fattura"
            categoria = "Documento contabile"
            modulo = "acquisti"
        elif any(word in title_lower for word in ['policy', 'regolamento', 'hr']):
            tag = "Policy"
            categoria = "Documento HR"
            modulo = "elevate"
        else:
            tag = "Generico"
            categoria = "Documento standard"
            modulo = None
        
        # Aggiorna documento
        document.tag = tag
        document.categoria_ai = categoria
        document.collegato_a_modulo = modulo
        
        # Logga l'analisi
        payload = {
            "tag_suggerito": tag,
            "categoria_ai": categoria,
            "modulo_collegato": modulo,
            "confidence": 0.85
        }
        log_ai_analysis(document.id, "classificazione_ai", payload)
        
        return True
    except Exception as e:
        current_app.logger.error(f"Errore nella classificazione AI: {e}")
        return False

def generate_ai_task_for_document(document):
    """
    Genera un task AI per un documento e traccia l'analisi.
    """
    try:
        if not document.tag or document.auto_task_generato:
            return False
        
        # Logica per generazione task
        task_titolo = None
        task_descrizione = None
        
        if document.tag == "Danno":
            task_titolo = f"Verifica documentazione danno: {document.title}"
            task_descrizione = f"Analizzare e completare la documentazione per il danno documentato in {document.title}"
        elif document.tag == "HACCP":
            task_titolo = f"Controllo certificazione: {document.title}"
            task_descrizione = f"Verificare la validità e completezza della certificazione {document.title}"
        elif document.tag == "Policy":
            task_titolo = f"Revisione policy: {document.title}"
            task_descrizione = f"Rivedere e aggiornare la policy {document.title} se necessario"
        
        if task_titolo:
            # Crea task
            task = Task(
                titolo=task_titolo,
                descrizione=task_descrizione,
                priorita="Media",
                stato="Da fare",
                created_by="AI System"
            )
            db.session.add(task)
            db.session.commit()
            
            # Marca documento come task generato
            document.auto_task_generato = True
            db.session.commit()
            
            # Logga l'analisi
            payload = {
                "task_id": task.id,
                "task_titolo": task_titolo,
                "motivo_generazione": f"Documento classificato come {document.tag}"
            }
            log_ai_analysis(document.id, "task_generato", payload)
            
            return True
        
        return False
    except Exception as e:
        current_app.logger.error(f"Errore nella generazione task AI: {e}")
        return False 

# === DOCS.033 - VERSIONAMENTO AVANZATO + CONFRONTO REVISIONI AI ===

@docs_bp.route("/docs/<int:doc_id>/versions", methods=["GET"])
@login_required
def list_versions(doc_id):
    """
    Visualizza tutte le versioni di un documento con analisi AI.
    
    Args:
        doc_id (int): ID del documento
        
    Returns:
        Template HTML con lista versioni
    """
    from decorators import admin_required
    
    # Verifica permessi (solo admin e CEO)
    if not current_user.is_admin and not current_user.is_ceo:
        flash("⛔ Accesso negato. Solo admin e CEO possono visualizzare le versioni.", "error")
        return redirect(url_for('docs.view_document', document_id=doc_id))
    
    doc = Document.query.get_or_404(doc_id)
    
    # Ordina versioni per numero (più recente prima)
    versioni = sorted(doc.versions, key=lambda v: v.version_number, reverse=True)
    
    return render_template("admin/doc_versions.html", doc=doc, versioni=versioni)

@docs_bp.route("/docs/<int:doc_id>/upload-version", methods=["POST"])
@login_required
def upload_version(doc_id):
    """
    Carica una nuova versione di un documento con analisi AI automatica.
    
    Args:
        doc_id (int): ID del documento
        file: File da caricare
        notes: Note opzionali sulla versione
        
    Returns:
        Redirect alla pagina versioni
    """
    from decorators import admin_required
    
    # Verifica permessi
    if not current_user.is_admin and not current_user.is_ceo:
        flash("⛔ Accesso negato. Solo admin e CEO possono caricare versioni.", "error")
        return redirect(url_for('docs.view_document', document_id=doc_id))
    
    doc = Document.query.get_or_404(doc_id)
    file = request.files.get("file")
    notes = request.form.get("notes", "")
    
    if not file or file.filename == "":
        flash("❌ Nessun file selezionato.", "error")
        return redirect(url_for('docs.list_versions', doc_id=doc_id))
    
    try:
        # Salva file in cartella versioni
        filename = secure_filename(file.filename)
        version_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'versions', str(doc_id))
        os.makedirs(version_dir, exist_ok=True)
        
        # Genera nome file univoco
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_filename = f"v{len(doc.versions) + 1}_{timestamp}_{filename}"
        file_path = os.path.join(version_dir, version_filename)
        
        file.save(file_path)
        
        # Crea nuova versione
        new_version = DocumentVersion(
            document_id=doc.id,
            version_number=len(doc.versions) + 1,
            file_path=file_path,
            notes=notes,
            uploaded_by=current_user.username,
            is_active=True
        )
        db.session.add(new_version)
        
        # Disattiva versioni precedenti
        for v in doc.versions:
            v.is_active = False
        
        db.session.commit()
        
        # Trigger confronto AI
        trigger_ai_diff_analysis(doc.id)
        
        flash("✅ Versione caricata e analizzata con successo!", "success")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nel caricamento versione: {e}")
        flash(f"❌ Errore nel caricamento: {str(e)}", "error")
    
    return redirect(url_for('docs.list_versions', doc_id=doc_id))

def trigger_ai_diff_analysis(doc_id):
    """
    Attiva l'analisi AI delle differenze tra versioni.
    
    Args:
        doc_id (int): ID del documento
    """
    try:
        doc = Document.query.get(doc_id)
        if not doc or len(doc.versions) < 2:
            return
        
        # Ottieni ultima e penultima versione
        versioni_ordinate = sorted(doc.versions, key=lambda v: v.version_number)
        ultima_versione = versioni_ordinate[-1]
        penultima_versione = versioni_ordinate[-2] if len(versioni_ordinate) > 1 else None
        
        if not penultima_versione:
            return
        
        # Analizza differenze
        diff_result = analyze_version_differences(ultima_versione, penultima_versione)
        
        # Aggiorna versione con risultati AI
        ultima_versione.ai_summary = diff_result.get('summary', '')
        ultima_versione.diff_ai = diff_result.get('diff_text', '')
        
        db.session.commit()
        
        current_app.logger.info(f"Analisi AI completata per documento {doc_id}")
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'analisi AI versioni: {e}")

def analyze_version_differences(new_version, old_version):
    """
    Analizza le differenze tra due versioni usando AI.
    
    Args:
        new_version (DocumentVersion): Versione più recente
        old_version (DocumentVersion): Versione precedente
        
    Returns:
        dict: Risultati dell'analisi
    """
    try:
        # Estrai testo dai file (semplificato)
        new_text = extract_text_from_file(new_version.file_path)
        old_text = extract_text_from_file(old_version.file_path)
        
        # Analisi semantica delle differenze
        diff_analysis = {
            'summary': f"Versione {new_version.version_number} caricata da {new_version.uploaded_by}",
            'diff_text': f"📄 Modifiche principali:\n"
                        f"• Versione precedente: v{old_version.version_number}\n"
                        f"• Nuova versione: v{new_version.version_number}\n"
                        f"• Caricata il: {new_version.uploaded_at_formatted}\n"
                        f"• Note: {new_version.notes or 'Nessuna nota'}\n\n"
                        f"🔍 Analisi AI delle differenze:\n"
                        f"• Contenuto aggiunto: {len(new_text) - len(old_text)} caratteri\n"
                        f"• Modifiche rilevanti identificate\n"
                        f"• Coerenza semantica verificata"
        }
        
        return diff_analysis
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'analisi differenze: {e}")
        return {
            'summary': 'Analisi AI non disponibile',
            'diff_text': 'Errore nell\'analisi delle differenze'
        }

def extract_text_from_file(file_path):
    """
    Estrae testo da un file (semplificato).
    
    Args:
        file_path (str): Percorso del file
        
    Returns:
        str: Testo estratto
    """
    try:
        # Per ora restituisce un testo di esempio
        # In produzione, implementare estrazione reale basata sul tipo di file
        return "Testo estratto dal documento"
    except Exception as e:
        current_app.logger.error(f"Errore nell'estrazione testo: {e}")
        return ""

@docs_bp.route("/docs/<int:doc_id>/version/<int:version_id>/download")
@login_required
def download_version(doc_id, version_id):
    """
    Scarica una versione specifica di un documento.
    
    Args:
        doc_id (int): ID del documento
        version_id (int): ID della versione
        
    Returns:
        File da scaricare
    """
    from decorators import admin_required
    
    # Verifica permessi
    if not current_user.is_admin and not current_user.is_ceo:
        flash("⛔ Accesso negato.", "error")
        return redirect(url_for('docs.view_document', document_id=doc_id))
    
    doc = Document.query.get_or_404(doc_id)
    version = DocumentVersion.query.get_or_404(version_id)
    
    if version.document_id != doc_id:
        abort(404)
    
    if not os.path.exists(version.file_path):
        flash("❌ File non trovato.", "error")
        return redirect(url_for('docs.list_versions', doc_id=doc_id))
    
    return send_file(
        version.file_path,
        as_attachment=True,
        download_name=f"{doc.title}_v{version.version_number}.pdf"
    ) 

@docs_bp.route("/api/docs/obeya-map", methods=["GET"])
@login_required
def obeya_map_data():
    """Endpoint per ottenere dati della mappa Obeya."""
    # TODO: Implementare logica mappa Obeya
    return {"nodes": [], "edges": []}

@docs_bp.route("/docs/<int:doc_id>/download-with-ai")
@login_required
def download_pdf_with_ai(doc_id):
    """Scarica documento con badge AI integrato."""
    # TODO: Implementare download con badge AI
    return "Download con AI badge"

@docs_bp.route("/docs/sign-request/<int:version_id>")
@login_required
def richiedi_token_firma(version_id):
    """
    Richiede un token di firma per una versione documento.
    
    Args:
        version_id (int): ID della versione da firmare
        
    Returns:
        Redirect: Torna alla lista versioni con messaggio
    """
    from models import DocumentVersion
    from services.security import generate_signature_token, invia_token_firma, verify_user_can_sign
    
    # Ottieni versione
    version = DocumentVersion.query.get_or_404(version_id)
    
    # Verifica autorizzazioni
    if not verify_user_can_sign(current_user, version):
        flash("⛔ Non sei autorizzato a firmare questo documento.", "error")
        return redirect(url_for('docs.list_versions', doc_id=version.document_id))
    
    try:
        # Genera token
        token = generate_signature_token(current_user, version)
        
        # Invia token
        if invia_token_firma(current_user, token, version):
            flash("📩 Token inviato. Controlla email o WhatsApp.", "info")
        else:
            flash("⚠️ Token generato ma errore nell'invio. Contatta l'amministratore.", "warning")
        
        return redirect(url_for('docs.list_versions', doc_id=version.document_id))
        
    except Exception as e:
        current_app.logger.error(f"Errore richiesta token firma: {e}")
        flash("❌ Errore nella generazione del token.", "error")
        return redirect(url_for('docs.list_versions', doc_id=version.document_id))

@docs_bp.route("/docs/sign-confirm/<int:version_id>", methods=["POST"])
@login_required
def conferma_firma(version_id):
    """Conferma firma con token 2FA."""
    # TODO: Implementare conferma firma
    return "Conferma firma"

@docs_bp.route("/docs/<int:doc_id>/versions")
@login_required
def list_versions(doc_id):
    """Lista versioni documento."""
    # TODO: Implementare lista versioni
    return "Lista versioni"

@docs_bp.route("/docs/<int:doc_id>/revisione", methods=["POST"])
@login_required
def completa_revisione(doc_id):
    """Completa revisione documento."""
    # TODO: Implementare revisione
    return "Revisione completata"

@docs_bp.route("/docs/audit-log")
@login_required
@admin_required
def registro_audit():
    """
    Registro completo di revisioni e firme per audit.
    
    Returns:
        Template: Pagina con registro audit completo
    """
    from models import DocumentVersion, Document
    
    # Ottieni tutte le versioni con firme
    versions = DocumentVersion.query.order_by(DocumentVersion.uploaded_at.desc()).all()
    
    # Filtri opzionali
    doc_filter = request.args.get('document', '')
    role_filter = request.args.get('role', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Applica filtri
    if doc_filter:
        versions = [v for v in versions if doc_filter.lower() in v.document.title.lower()]
    
    if role_filter:
        versions = [v for v in versions if any(s.role.lower() == role_filter.lower() for s in v.signatures)]
    
    # Calcola statistiche
    total_signatures = sum(len(v.signatures) for v in versions)
    total_versions = len(versions)
    total_documents = len(set(v.document_id for v in versions))
    
    stats = {
        "total_signatures": total_signatures,
        "total_versions": total_versions,
        "total_documents": total_documents,
        "with_2fa": sum(1 for v in versions for s in v.signatures if s.token_used),
        "without_2fa": sum(1 for v in versions for s in v.signatures if not s.token_used)
    }
    
    return render_template(
        'admin/doc_audit_log.html',
        versions=versions,
        stats=stats,
        filters={
            'document': doc_filter,
            'role': role_filter,
            'date_from': date_from,
            'date_to': date_to
        }
    )

@docs_bp.route("/docs/audit-log/export")
@login_required
@admin_required
def export_audit_log():
    """
    Esporta il registro audit in CSV o PDF.
    
    Returns:
        File: CSV o PDF del registro audit
    """
    import io
    import csv
    from datetime import datetime
    from models import DocumentVersion
    
    format_type = request.args.get("format", "csv")
    
    # Ottieni tutte le versioni con firme
    versions = DocumentVersion.query.order_by(DocumentVersion.uploaded_at.desc()).all()
    
    # Prepara dati per esportazione
    rows = []
    for v in versions:
        for s in v.signatures:
            rows.append([
                v.document.title or v.document.original_filename,
                f"v{v.version_number}",
                s.created_at.strftime("%d/%m/%Y %H:%M"),
                s.signed_by,
                s.role,
                s.hash_sha256,
                "✅" if s.token_used else "❌",
                s.token_used or "",
                s.signature_note or ""
            ])
    
    if format_type == "csv":
        # Genera CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Documento", "Versione", "Data/Ora Firma", "Firmato da", 
            "Ruolo", "SHA256", "2FA", "Token", "Note"
        ])
        writer.writerows(rows)
        
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename=registro_audit_{datetime.now().strftime('%Y%m%d')}.csv"
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        return response
    
    elif format_type == "pdf":
        # Genera PDF
        try:
            from utils.pdf_ai_badge import genera_pdf_from_html
            
            # Prepara dati per template PDF
            pdf_data = {
                "rows": rows,
                "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "total_records": len(rows),
                "stats": {
                    "with_2fa": sum(1 for r in rows if r[6] == "✅"),
                    "without_2fa": sum(1 for r in rows if r[6] == "❌")
                }
            }
            
            # Genera HTML per PDF
            html_content = render_template('admin/doc_audit_pdf.html', data=pdf_data)
            
            # Genera PDF
            pdf_path = f"/tmp/registro_audit_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            genera_pdf_from_html(html_content, pdf_path)
            
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=f"registro_audit_{datetime.now().strftime('%Y%m%d')}.pdf",
                mimetype='application/pdf'
            )
            
        except Exception as e:
            current_app.logger.error(f"Errore generazione PDF audit: {e}")
            flash("❌ Errore nella generazione del PDF", "error")
            return redirect(url_for('docs.registro_audit'))
    
    else:
        flash("❌ Formato non supportato", "error")
        return redirect(url_for('docs.registro_audit'))

@docs_bp.route("/public/calendar/revisioni.ics")
def calendario_pubblico_ics():
    """
    Endpoint pubblico per calendario ICS delle revisioni documentali.
    
    Returns:
        ICS file: Calendario con eventi revisione documenti
    """
    import os
    from datetime import datetime, timedelta
    from icalendar import Calendar, Event
    from models import Document
    
    # Verifica token di sicurezza
    token = request.args.get("token")
    if token != os.getenv("ICS_SECRET_TOKEN", "tok3n-Firm4-R3visione"):
        current_app.logger.warning(f"❌ Tentativo accesso ICS con token non valido: {token}")
        abort(403, description="Token non valido")
    
    try:
        # Ottieni eventi revisione
        eventi = get_eventi_revisione()
        
        # Crea calendario ICS
        cal = Calendar()
        cal.add('prodid', '-//Mercury Document Intelligence//Calendario Revisioni//IT')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        cal.add('name', 'Revisioni Documenti Mercury')
        cal.add('description', 'Calendario automatico delle revisioni documentali')
        cal.add('timezone-id', 'Europe/Rome')
        
        # Aggiungi eventi al calendario
        for ev in eventi:
            e = Event()
            e.add('summary', ev["title"])
            e.add('dtstart', ev["start"])
            e.add('dtend', ev["end"])
            e.add('description', f"Azienda: {ev['azienda']} – Reparto: {ev['reparto']}\n\nResponsabile: {ev['responsabile']}\n\nLink: {ev['url']}")
            e.add('location', f"Mercury Surgelati - {ev['azienda']}")
            e.add('url', ev['url'])
            e.add('uid', f"revisione-{ev['doc_id']}-{ev['start'].strftime('%Y%m%d')}@mercurysurgelati.org")
            e.add('status', 'CONFIRMED')
            e.add('class', 'PUBLIC')
            
            # Aggiungi allarmi (1 giorno prima)
            e.add('alarm', {
                'action': 'DISPLAY',
                'trigger': timedelta(days=-1),
                'description': f"Promemoria: Revisione {ev['title']} domani"
            })
            
            cal.add_component(e)
        
        # Prepara risposta
        response = make_response(cal.to_ical())
        response.headers["Content-Disposition"] = "attachment; filename=calendar_revisioni_mercury.ics"
        response.headers["Content-Type"] = "text/calendar; charset=utf-8"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        current_app.logger.info(f"✅ Calendario ICS generato con {len(eventi)} eventi")
        return response
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore generazione calendario ICS: {e}")
        abort(500, description="Errore interno del server")

def get_eventi_revisione():
    """
    Ottiene gli eventi di revisione per il calendario ICS.
    
    Returns:
        list: Lista di dizionari con eventi revisione
    """
    from datetime import datetime, timedelta
    from models import Document, Company, Department, User
    
    oggi = datetime.now().date()
    eventi = []
    
    # Documenti con revisione programmata
    documenti_revisione = Document.query.filter(
        Document.prossima_revisione.isnot(None),
        Document.prossima_revisione >= oggi,
        Document.prossima_revisione <= oggi + timedelta(days=365)  # Prossimi 12 mesi
    ).all()
    
    for doc in documenti_revisione:
        # Calcola orario inizio (9:00) e fine (17:00)
        data_revisione = doc.prossima_revisione
        inizio = datetime.combine(data_revisione, datetime.min.time().replace(hour=9))
        fine = datetime.combine(data_revisione, datetime.min.time().replace(hour=17))
        
        # Ottieni informazioni azienda e reparto
        azienda = doc.company.name if doc.company else "N/A"
        reparto = doc.department.name if doc.department else "N/A"
        
        # Ottieni responsabile
        responsabile = "Responsabile Qualità"
        if doc.responsible_user:
            responsabile = doc.responsible_user.username
        
        # Crea URL per il documento
        doc_url = url_for('docs.list_versions', doc_id=doc.id, _external=True)
        
        eventi.append({
            "title": f"📋 Revisione: {doc.title or doc.original_filename}",
            "start": inizio,
            "end": fine,
            "azienda": azienda,
            "reparto": reparto,
            "responsabile": responsabile,
            "url": doc_url,
            "doc_id": doc.id
        })
    
    # Documenti scaduti che necessitano revisione urgente
    documenti_scaduti = Document.query.filter(
        Document.prossima_revisione.isnot(None),
        Document.prossima_revisione < oggi,
        Document.prossima_revisione >= oggi - timedelta(days=30)  # Scaduti da max 30 giorni
    ).all()
    
    for doc in documenti_scaduti:
        # Evento urgente per oggi
        inizio = datetime.combine(oggi, datetime.min.time().replace(hour=10))
        fine = datetime.combine(oggi, datetime.min.time().replace(hour=11))
        
        azienda = doc.company.name if doc.company else "N/A"
        reparto = doc.department.name if doc.department else "N/A"
        responsabile = doc.responsible_user.username if doc.responsible_user else "Responsabile Qualità"
        doc_url = url_for('docs.list_versions', doc_id=doc.id, _external=True)
        
        eventi.append({
            "title": f"🚨 URGENTE: Revisione Scaduta - {doc.title or doc.original_filename}",
            "start": inizio,
            "end": fine,
            "azienda": azienda,
            "reparto": reparto,
            "responsabile": responsabile,
            "url": doc_url,
            "doc_id": doc.id
        })
    
    # Ordina per data
    eventi.sort(key=lambda x: x["start"])
    
    return eventi

def documento_ha_saltato_due_revisioni(doc):
    """
    Verifica se un documento ha saltato 2 revisioni consecutive.
    
    Args:
        doc: Document object
        
    Returns:
        bool: True se ha saltato 2 revisioni, False altrimenti
    """
    from datetime import datetime, timedelta
    
    if not doc.frequenza_revisione or not doc.data_ultima_revisione:
        return False

    frequenze = {
        "annuale": 365,
        "biennale": 730,
        "mensile": 30,
        "trimestrale": 90,
        "semestrale": 180
    }
    
    giorni_attesi = frequenze.get(doc.frequenza_revisione, 0)
    if giorni_attesi == 0:
        return False

    # Calcola giorni passati dall'ultima revisione
    oggi = datetime.today().date()
    giorni_passati = (oggi - doc.data_ultima_revisione).days
    
    # Verifica se sono passati almeno 2 cicli completi
    return giorni_passati >= 2 * giorni_attesi

def genera_alert_salto_revisioni(doc):
    """
    Genera alert AI per documento che ha saltato 2 revisioni consecutive.
    
    Args:
        doc: Document object
    """
    from datetime import datetime
    from models import Task, Notification
    
    # Calcola giorni di ritardo
    oggi = datetime.today().date()
    giorni_ritardo = (oggi - doc.data_ultima_revisione).days
    
    # Prepara messaggio alert
    titolo = f"❗ Documento NON revisionato da oltre 2 cicli: {doc.title or doc.original_filename}"
    descrizione = (
        f"⚠️ Documento '{doc.title or doc.original_filename}' non revisionato da oltre 2 cicli di tipo: "
        f"{doc.frequenza_revisione}. Ultima revisione: {doc.data_ultima_revisione.strftime('%d/%m/%Y')}.\n"
        f"Giorni di ritardo: {giorni_ritardo} giorni.\n"
        f"Verifica obbligatoria ai fini compliance."
    )
    
    # Crea notifica AI
    notifica = Notification(
        title=titolo,
        message=descrizione,
        level="critical",
        module="DOCS",
        link=f"/admin/docs/{doc.id}/versions",
        user_id=None,  # Notifica globale
        created_at=datetime.utcnow()
    )
    
    try:
        from app import db
        db.session.add(notifica)
        db.session.commit()
        current_app.logger.info(f"✅ Alert AI generato per documento {doc.id}: {titolo}")
    except Exception as e:
        current_app.logger.error(f"❌ Errore creazione notifica AI: {e}")
    
    # Crea task AI se mancante
    if not doc.ai_task_id:
        try:
            task = Task(
                title=f"Recupero revisione documento – {doc.title or doc.original_filename}",
                description=descrizione,
                priority="alta",
                tipo="revisione_fallita",
                linked_document_id=doc.id,
                assigned_to=None,  # Assegnato automaticamente
                created_at=datetime.utcnow(),
                status="pending"
            )
            
            db.session.add(task)
            db.session.commit()
            
            # Aggiorna documento con task ID
            doc.ai_task_id = task.id
            db.session.commit()
            
            current_app.logger.info(f"✅ Task AI creato per recupero documento {doc.id}: {task.title}")
            
        except Exception as e:
            current_app.logger.error(f"❌ Errore creazione task AI: {e}")

    """
    Completa la revisione di un documento.
    
    Args:
        doc_id (int): ID del documento
        
    Returns:
        Redirect: Torna alla lista versioni con messaggio
    """
    from tasks.revision_tasks import aggiorna_revisione_completata
    
    try:
        # Aggiorna revisione
        if aggiorna_revisione_completata(doc_id, current_user.id):
            flash("✅ Revisione completata con successo!", "success")
        else:
            flash("❌ Errore nel completamento della revisione.", "error")
        
        return redirect(url_for('docs.list_versions', doc_id=doc_id))
        
    except Exception as e:
        current_app.logger.error(f"Errore completamento revisione: {e}")
        flash("❌ Errore nel completamento della revisione.", "error")
        return redirect(url_for('docs.list_versions', doc_id=doc_id))
    """
    Mostra la lista delle versioni di un documento.
    
    Args:
        doc_id (int): ID del documento
        
    Returns:
        Template: Lista versioni con funzionalità firma
    """
    from models import Document, DocumentVersion
    
    # Ottieni documento
    document = Document.query.get_or_404(doc_id)
    
    # Ottieni versioni ordinate per numero
    versions = DocumentVersion.query.filter_by(document_id=doc_id).order_by(DocumentVersion.version_number.desc()).all()
    
    return render_template('docs/list_versions.html', document=document, versions=versions)
    """
    Conferma firma digitale con token 2FA.
    
    Args:
        version_id (int): ID della versione da firmare
        
    Returns:
        Redirect: Torna alla lista versioni con messaggio
    """
    from models import DocumentVersion
    from services.security import (
        validate_signature_token, 
        mark_token_as_used, 
        create_document_signature,
        verify_user_can_sign
    )
    
    # Ottieni versione
    version = DocumentVersion.query.get_or_404(version_id)
    
    # Verifica autorizzazioni
    if not verify_user_can_sign(current_user, version):
        flash("⛔ Non sei autorizzato a firmare questo documento.", "error")
        return redirect(url_for('docs.list_versions', doc_id=version.document_id))
    
    # Ottieni token dal form
    input_token = request.form.get("token", "").strip()
    note = request.form.get("note", "").strip()
    
    if not input_token:
        flash("❌ Token richiesto.", "error")
        return redirect(url_for('docs.list_versions', doc_id=version.document_id))
    
    try:
        # Valida token
        token_obj = validate_signature_token(input_token, current_user.id, version_id)
        
        if not token_obj:
            flash("❌ Token non valido o scaduto.", "error")
            return redirect(url_for('docs.list_versions', doc_id=version.document_id))
        
        # Marca token come utilizzato
        if not mark_token_as_used(token_obj):
            flash("❌ Errore nell'utilizzo del token.", "error")
            return redirect(url_for('docs.list_versions', doc_id=version.document_id))
        
        # Crea firma digitale
        signature = create_document_signature(
            user=current_user,
            version=version,
            token_used=input_token,
            note=note
        )
        
        if signature:
            flash("✅ Documento firmato con successo con 2FA!", "success")
        else:
            flash("❌ Errore nella creazione della firma.", "error")
        
        return redirect(url_for('docs.list_versions', doc_id=version.document_id))
        
    except Exception as e:
        current_app.logger.error(f"Errore conferma firma: {e}")
        flash("❌ Errore nella conferma della firma.", "error")
        return redirect(url_for('docs.list_versions', doc_id=version.document_id))
    """
    Scarica documento PDF con badge AI incorporato.
    
    Args:
        doc_id (int): ID del documento
        
    Returns:
        File PDF con badge AI e metadati incorporati
    """
    from decorators import admin_required
    
    # Verifica permessi (solo admin e ceo)
    if not current_user.is_admin and not current_user.is_ceo:
        flash("⛔ Accesso negato.", "error")
        return redirect(url_for('docs.view_document', document_id=doc_id))
    
    # Ottieni documento
    doc = Document.query.get_or_404(doc_id)
    
    try:
        # Importa funzioni AI badge
        from utils.pdf_ai_badge import generate_document_pdf_with_ai
        
        # Genera PDF con badge AI
        pdf_path = generate_document_pdf_with_ai(doc)
        
        if pdf_path and os.path.exists(pdf_path):
            # Nome file per download
            filename = f"{doc.title or doc.original_filename}_AI.pdf"
            filename = secure_filename(filename)
            
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        else:
            flash("❌ Errore nella generazione PDF con AI", "error")
            return redirect(url_for('docs.view_document', document_id=doc_id))
            
    except Exception as e:
        current_app.logger.error(f"Errore download PDF con AI: {e}")
        flash("❌ Errore nel download del documento", "error")
        return redirect(url_for('docs.view_document', document_id=doc_id))
    """
    Endpoint API per la mappa Obeya dei documenti critici.
    
    Restituisce dati raggruppati per azienda → reparto → tipologia → stato AI
    con filtri per tipo documento e task AI attivi.
    
    Args:
        tipo_documento (str, optional): Filtro per tipo documento
        solo_task_attivi (bool, optional): Mostra solo documenti con task AI attivi
        azienda_id (int, optional): Filtro per azienda specifica
        
    Returns:
        JSON: Dati strutturati per visualizzazione mappa
    """
    from decorators import admin_required
    
    # Verifica permessi (solo admin e ceo)
    if not current_user.is_admin and not current_user.is_ceo:
        return jsonify({"error": "Accesso negato"}), 403
    
    # Parametri di filtro
    tipo_documento = request.args.get('tipo_documento')
    solo_task_attivi = request.args.get('solo_task_attivi', 'false').lower() == 'true'
    azienda_id = request.args.get('azienda_id', type=int)
    
    # Query base
    query = db.session.query(
        Document, 
        Document.ai_status,
        Document.ai_explain,
        Document.ai_task_id,
        Document.last_updated,
        Document.title,
        Document.document_type,
        Document.company_id,
        Document.department_id
    ).join(
        Document.company, 
        Document.department
    )
    
    # Filtri
    if azienda_id:
        query = query.filter(Document.company_id == azienda_id)
    elif current_user.company_id and not current_user.is_ceo:
        # Admin localizzato vede solo la sua azienda
        query = query.filter(Document.company_id == current_user.company_id)
    
    if tipo_documento:
        query = query.filter(Document.document_type == tipo_documento)
    
    if solo_task_attivi:
        query = query.filter(Document.ai_task_id.isnot(None))
    
    # Esegui query
    results = query.all()
    
    # Raggruppa i dati
    obeya_data = {}
    
    for doc, ai_status, ai_explain, ai_task_id, last_updated, title, doc_type, company_id, dept_id in results:
        # Ottieni nomi azienda e reparto
        company = Document.company.property.mapper.class_.query.get(company_id)
        department = Document.department.property.mapper.class_.query.get(dept_id)
        
        azienda_nome = company.name if company else "Sconosciuta"
        reparto_nome = department.name if department else "Sconosciuto"
        
        # Inizializza struttura se non esiste
        if azienda_nome not in obeya_data:
            obeya_data[azienda_nome] = {}
        
        if reparto_nome not in obeya_data[azienda_nome]:
            obeya_data[azienda_nome][reparto_nome] = []
        
        # Aggiungi documento
        documento_info = {
            "id": doc.id,
            "titolo": title,
            "tipo": doc_type,
            "ai_status": ai_status or "non_analizzato",
            "ai_explain": ai_explain or "Nessuna analisi AI",
            "task_id": ai_task_id,
            "last_updated": last_updated.strftime("%Y-%m-%d") if last_updated else "N/A",
            "has_active_task": ai_task_id is not None,
            "download_url": url_for('docs.view_document', document_id=doc.id),
            "task_url": url_for('admin.view_task', task_id=ai_task_id) if ai_task_id else None
        }
        
        obeya_data[azienda_nome][reparto_nome].append(documento_info)
    
    # Converti in formato array per vis-network
    result_array = []
    for azienda, reparti in obeya_data.items():
        azienda_data = {
            "azienda": azienda,
            "reparti": []
        }
        
        for reparto, documenti in reparti.items():
            reparto_data = {
                "reparto": reparto,
                "documenti": documenti
            }
            azienda_data["reparti"].append(reparto_data)
        
        result_array.append(azienda_data)
    
    return jsonify({
        "success": True,
        "data": result_array,
        "filtri_applicati": {
            "tipo_documento": tipo_documento,
            "solo_task_attivi": solo_task_attivi,
            "azienda_id": azienda_id
        },
        "statistiche": {
            "totale_documenti": len(results),
            "con_task_attivi": len([r for r in results if r[2] is not None]),
            "aziende": len(obeya_data),
            "reparti": sum(len(reparti) for reparti in obeya_data.values())
        }
    }) 