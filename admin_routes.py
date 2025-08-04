from flask import Blueprint, render_template, abort, request, redirect, url_for, flash, jsonify, send_file, current_app, Response
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from extensions import db, bcrypt, mail
from models import Document, User, Department, GuestActivity, AuditLog, DocumentReadLog, DocumentVersion, Task, DocumentoAIInsight, AIAlert, DownloadLog, Company
import csv
import io
from weasyprint import HTML
import json
from flask_mail import Message
from services.ai_monitoring import get_recent_alerts, get_alert_statistics, create_ai_alert, analizza_download_sospetti

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def invia_notifica_nuova_versione(document, new_ver):
    """
    Invia notifica email al team quando viene caricata una nuova versione
    """
    try:
        # Ottieni utenti del reparto del documento
        destinatari = []
        if document.department and document.department.users:
            for user in document.department.users:
                if user.role in ['user', 'admin'] and user.email:
                    destinatari.append(user.email)
        
        if not destinatari:
            return
        
        msg = Message(
            subject=f"[Docs] Nuova versione caricata: {document.title or document.original_filename} - {new_ver.numero_versione}",
            recipients=destinatari,
            body=f"""
Ciao, è stata caricata una nuova versione del documento:

📄 Titolo: {document.title or document.original_filename}
📁 Versione: {new_ver.numero_versione}
👤 Caricato da: {new_ver.uploader or 'Sistema'}
📝 Note: {new_ver.note or 'Nessuna'}

Accedi per visualizzare: https://docs.mercurysurgelati.org/admin/document/{document.id}
            """
        )
        mail.send(msg)
    except Exception as e:
        print(f"Errore invio email notifica nuova versione: {e}")

@admin_bp.before_request
@login_required
def restrict_to_admins():
    if not current_user.is_authenticated or current_user.role != 'admin':
        abort(403)

@admin_bp.route('/users')
def user_list():
    return render_template('admin/users.html')

@admin_bp.route('/documents_overview')
def documents_overview():
    obsolete_docs = Document.query.filter(Document.expiry_date < datetime.utcnow()).all()
    protected_docs = Document.query.filter(Document.password != None).all()
    return render_template('admin/documents_overview.html',
                           obsolete_docs=obsolete_docs,
                           protected_docs=protected_docs)

@admin_bp.route('/documents_overview')
def documents_overview():
    obsolete_docs = Document.query.filter(Document.expiry_date < datetime.utcnow()).all()
    protected_docs = Document.query.filter(Document.password != None).all()
    return render_template('admin/documents_overview.html',
                           obsolete_docs=obsolete_docs,
                           protected_docs=protected_docs)

@admin_bp.route('/document/<int:document_id>')
def view_document(document_id):
    doc = Document.query.get_or_404(document_id)
    return render_template('admin/view_document.html', document=doc)

@admin_bp.route('/document/<int:document_id>/edit_password', methods=['GET', 'POST'])
def edit_document_password(document_id):
    doc = Document.query.get_or_404(document_id)
    if request.method == 'POST':
        new_password = request.form.get('password')
        if new_password:
            hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
            doc.password = hashed_pw
            db.session.commit()
            flash('Password aggiornata con successo.', 'success')
            return redirect(url_for('admin.documents_overview'))
        else:
            flash('Inserisci una password valida.', 'danger')
    return render_template('admin/edit_document_password.html', document=doc)

@admin_bp.route('/guest_logs')
def guest_logs():
    logs = GuestActivity.query.order_by(GuestActivity.timestamp.desc()).all()
    return render_template('admin/guest_logs.html', logs=logs)

@admin_bp.route('/audit_logs')
@login_required
def audit_logs():
    """
    Visualizza tutti i log di audit per le azioni critiche.
    
    Returns:
        template: Pagina con tutti i log di audit.
    """
    if not current_user.is_admin:
        abort(403)
    
    # Filtri per tipo di azione
    filter_azione = request.args.get('azione', 'all')
    filter_user = request.args.get('user', 'all')
    
    query = AuditLog.query
    
    if filter_azione != 'all':
        query = query.filter(AuditLog.azione == filter_azione)
    
    if filter_user != 'all':
        query = query.filter(AuditLog.user_id == filter_user)
    
    logs = query.order_by(AuditLog.timestamp.desc()).all()
    
    # Ottieni lista utenti per il filtro
    users = User.query.all()
    
    return render_template('admin/audit_logs.html', 
                         logs=logs, 
                         filter_azione=filter_azione,
                         filter_user=filter_user,
                         users=users)

@admin_bp.route('/audit_logs/export')
@login_required
def export_audit_csv():
    """
    Esporta i log di audit in formato CSV.
    
    Returns:
        file: File CSV con tutti i log di audit.
    """
    if not current_user.is_admin:
        abort(403)
    
    import io
    import csv
    from flask import Response
    
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Utente", "Azione", "Documento", "Data/Ora", "Note"
    ])
    
    for log in logs:
        writer.writerow([
            log.id,
            log.user.username if log.user else 'N/A',
            log.azione_display,
            log.document.title if log.document else 'N/A',
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            log.note or ''
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=audit_logs.csv'}
    )

@admin_bp.route('/firme')
@login_required
def visualizza_firme():
    """
    Visualizza tutte le firme dei documenti con stato di conferma.
    
    Returns:
        template: Pagina con tutte le firme e il loro stato.
    """
    if not current_user.is_admin:
        abort(403)
    
    # Filtri per stato firma
    filter_stato = request.args.get('stato', 'all')
    
    query = DocumentReadLog.query
    
    if filter_stato == 'confermate':
        query = query.filter(DocumentReadLog.confermata == True)
    elif filter_stato == 'in_attesa':
        query = query.filter(DocumentReadLog.confermata == False)
    
    firme = query.order_by(DocumentReadLog.timestamp.desc()).all()
    
    return render_template('admin/firme.html', 
                         firme=firme, 
                         filter_stato=filter_stato)

@admin_bp.route("/document/<int:doc_id>/nuova_versione", methods=["POST"])
@login_required
def carica_nuova_versione(doc_id):
    """
    Carica una nuova versione di un documento.
    
    Args:
        doc_id (int): ID del documento.
        
    Returns:
        redirect: Reindirizzamento alla pagina del documento.
    """
    if not current_user.is_admin:
        abort(403)
    
    doc = Document.query.get_or_404(doc_id)
    
    # Verifica se è stato caricato un file
    if 'file' not in request.files:
        flash("❌ Nessun file selezionato.", "danger")
        return redirect(url_for("admin.view_document", document_id=doc.id))
    
    file = request.files['file']
    if file.filename == '':
        flash("❌ Nessun file selezionato.", "danger")
        return redirect(url_for("admin.view_document", document_id=doc.id))
    
    if file:
        try:
            import os
            from werkzeug.utils import secure_filename
            
            # Calcola il numero della nuova versione
            n_versioni = len(doc.versioni)
            numero_versione = f"v{n_versioni + 1}"
            
            # Genera nome file sicuro
            filename = secure_filename(file.filename)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{numero_versione}_{timestamp}_{filename}"
            
            # Percorso di salvataggio
            upload_path = os.path.join(
                app.config['UPLOAD_FOLDER'], 
                doc.company.name, 
                doc.department.name
            )
            os.makedirs(upload_path, exist_ok=True)
            file_path = os.path.join(upload_path, new_filename)
            
            # Salva il file
            file.save(file_path)
            
            # Crea la nuova versione
            nuova_versione = DocumentVersion(
                document_id=doc.id,
                numero_versione=numero_versione,
                filename=new_filename,
                note=request.form.get("note", ""),
                uploader=current_user.email
            )
            
            db.session.add(nuova_versione)
            db.session.commit()
            
            # Log dell'audit
            audit_log = AuditLog(
                user_id=current_user.id,
                document_id=doc.id,
                azione='nuova_versione',
                note=f'Caricata nuova versione {numero_versione} del documento "{doc.title or doc.original_filename}"'
            )
            db.session.add(audit_log)
            db.session.commit()
            
            # 🔔 1. Notifica Email al Team alla Nuova Versione
            try:
                invia_notifica_nuova_versione(doc, nuova_versione)
            except Exception as e:
                print(f"Errore invio email notifica: {e}")
            
            # ⛓️ 2. Collegamento Automatico al Task Manager
            try:
                task = Task(
                    titolo=f"Verifica nuova versione di '{doc.title or doc.original_filename}'",
                    descrizione=f"È stata caricata la nuova versione {numero_versione} del documento '{doc.title or doc.original_filename}'.\n\nNote: {request.form.get('note', 'Nessuna nota')}\nCaricato da: {current_user.email}",
                    stato="Da fare",
                    assegnato_a="admin@example.com",  # o una logica per team specifici
                    priorita="Media",
                    documento_id=doc.id
                )
                db.session.add(task)
                db.session.commit()
            except Exception as e:
                print(f"Errore creazione task automatico: {e}")
            
            flash(f"✅ Nuova versione {numero_versione} caricata con successo.", "success")
            
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Errore durante il caricamento: {str(e)}", "danger")
            print(f"Errore caricamento versione: {e}")
    
    return redirect(url_for("admin.view_document", document_id=doc.id))

@admin_bp.route("/document/<int:document_id>/versions/export")
@login_required
def export_versions_csv(document_id):
    """
    Esporta lo storico delle versioni di un documento in CSV
    """
    if not current_user.is_admin:
        abort(403)
    
    document = Document.query.get_or_404(document_id)
    versions = document.versioni
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Versione", "Data Upload", "Utente", "Note", "Attiva"])
    
    for v in versions:
        writer.writerow([
            v.numero_versione,
            v.upload_date.strftime("%Y-%m-%d %H:%M") if v.upload_date else "N/A",
            v.uploader or "N/A",
            v.note or "",
            "Sì" if v.is_active else "No"
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment; filename=storico_{document.title or document.original_filename}.csv"}
    )

@admin_bp.route("/document/<int:doc_id>/versioni")
@login_required
def visualizza_versioni(doc_id):
    """
    Visualizza tutte le versioni di un documento.
    
    Args:
        doc_id (int): ID del documento.
        
    Returns:
        template: Pagina con tutte le versioni del documento.
    """
    if not current_user.is_admin:
        abort(403)
    
    doc = Document.query.get_or_404(doc_id)
    versioni = DocumentVersion.query.filter_by(document_id=doc_id).order_by(DocumentVersion.data_caricamento.desc()).all()
    
    return render_template('admin/versioni_documento.html', 
                         document=doc, 
                         versioni=versioni)

@admin_bp.route("/document/<int:doc_id>/approva", methods=["POST"])
@login_required
def approva_documento_admin(doc_id):
    """
    Approva un documento come Admin.
    
    Args:
        doc_id (int): ID del documento da approvare.
        
    Returns:
        redirect: Reindirizzamento alla pagina del documento.
    """
    if current_user.role != 'admin':
        abort(403)

    doc = Document.query.get_or_404(doc_id)
    doc.validazione_admin = True
    
    # Log dell'approvazione admin
    audit_log = AuditLog(
        user_id=current_user.id,
        document_id=doc.id,
        azione='approvazione_admin',
        note=f'Documento "{doc.title or doc.original_filename}" approvato da Admin'
    )
    db.session.add(audit_log)
    db.session.commit()
    
    flash("✅ Documento approvato da Admin.", "success")
    return redirect(url_for("admin.view_document", document_id=doc.id))

# === ROUTE AI DOCUMENTALE ===

@admin_bp.route('/ai/insights')
@login_required
def ai_insights():
    """
    Dashboard AI per gli insight sui documenti.
    
    Returns:
        template: Dashboard AI con gli insight attivi.
    """
    if not current_user.is_admin:
        abort(403)
    
    # Recupera tutti gli insight AI attivi
    insights = DocumentoAIInsight.query.filter_by(status='attivo').order_by(DocumentoAIInsight.timestamp.desc()).all()
    
    return render_template("docs/dashboard_ai.html", insights=insights)


@admin_bp.route('/ai/analyze', methods=['POST'])
@login_required
def esegui_analisi_ai():
    """
    Esegue l'analisi AI su tutti i documenti.
    
    Returns:
        json: Risultato dell'analisi.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accesso negato'})
    
    try:
        # Importa le funzioni AI
        from ai.document_ai_scheduler import esegui_analisi_completa
        
        # Esegui l'analisi
        esegui_analisi_completa()
        
        return jsonify({
            'success': True, 
            'message': 'Analisi AI completata con successo'
        })
        
    except Exception as e:
        print(f"Errore durante l'analisi AI: {e}")
        return jsonify({
            'success': False, 
            'message': f'Errore durante l\'analisi: {str(e)}'
        })


@admin_bp.route('/ai/insight/<int:insight_id>/resolve', methods=['POST'])
@login_required
def resolve_insight(insight_id):
    """
    Segna un insight come risolto.
    
    Args:
        insight_id (int): ID dell'insight da risolvere.
        
    Returns:
        json: Risultato dell'operazione.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accesso negato'})
    
    try:
        insight = DocumentoAIInsight.query.get_or_404(insight_id)
        insight.status = 'risolto'
        insight.valore = f'Risolto da {current_user.email} il {datetime.utcnow().strftime("%d/%m/%Y %H:%M")}'
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Errore durante la risoluzione dell'insight: {e}")
        return jsonify({'success': False, 'message': str(e)})


@admin_bp.route('/ai/insight/<int:insight_id>/ignore', methods=['POST'])
@login_required
def ignore_insight(insight_id):
    """
    Ignora un insight.
    
    Args:
        insight_id (int): ID dell'insight da ignorare.
        
    Returns:
        json: Risultato dell'operazione.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accesso negato'})
    
    try:
        insight = DocumentoAIInsight.query.get_or_404(insight_id)
        insight.status = 'ignorato'
        insight.valore = f'Ignorato da {current_user.email} il {datetime.utcnow().strftime("%d/%m/%Y %H:%M")}'
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Errore durante l'ignoramento dell'insight: {e}")
        return jsonify({'success': False, 'message': str(e)})


@admin_bp.route('/ai/insight/<int:insight_id>/create-task', methods=['POST'])
@login_required
def create_task_from_insight(insight_id):
    """
    Crea un task automatico da un insight AI.
    
    Args:
        insight_id (int): ID dell'insight.
        
    Returns:
        json: Risultato dell'operazione.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accesso negato'})
    
    try:
        insight = DocumentoAIInsight.query.get_or_404(insight_id)
        
        # Genera il task basato sul tipo di insight
        task_titolo = ""
        task_descrizione = ""
        task_priorita = "Media"
        
        if insight.tipo == 'duplicato':
            task_titolo = f"Verifica duplicati - {insight.document.title}"
            task_descrizione = f"Verificare se il documento '{insight.document.title}' è effettivamente duplicato e decidere quale mantenere."
            task_priorita = "Alta"
        elif insight.tipo == 'obsoleto':
            task_titolo = f"Aggiornamento documento scaduto - {insight.document.title}"
            task_descrizione = f"Il documento '{insight.document.title}' è scaduto e necessita di aggiornamento o sostituzione."
            task_priorita = "Critica"
        elif insight.tipo == 'vecchio':
            task_titolo = f"Revisione documento antico - {insight.document.title}"
            task_descrizione = f"Verificare se il documento '{insight.document.title}' è ancora aggiornato e rilevante."
            task_priorita = "Media"
        elif insight.tipo == 'inutilizzato':
            task_titolo = f"Verifica documento inutilizzato - {insight.document.title}"
            task_descrizione = f"Verificare se il documento '{insight.document.title}' è ancora necessario o può essere archiviato."
            task_priorita = "Bassa"
        
        # Crea il task
        task = Task(
            titolo=task_titolo,
            descrizione=task_descrizione,
            priorita=task_priorita,
            stato="Da fare",
            created_by=current_user.email,
            scadenza=datetime.utcnow() + timedelta(days=7)
        )
        
        db.session.add(task)
        db.session.commit()
        
        # Segna l'insight come risolto
        insight.status = 'risolto'
        insight.valore = f'Task creato da {current_user.email} il {datetime.utcnow().strftime("%d/%m/%Y %H:%M")}'
        db.session.commit()
        
        return jsonify({'success': True, 'task_id': task.id})
        
    except Exception as e:
        print(f"Errore durante la creazione del task: {e}")
        return jsonify({'success': False, 'message': str(e)})


@admin_bp.route('/ai/insights/export')
@login_required
def export_ai_insights():
    """
    Esporta gli insight AI in formato CSV.
    
    Returns:
        csv: File CSV con gli insight.
    """
    if not current_user.is_admin:
        abort(403)
    
    insights = DocumentoAIInsight.query.order_by(DocumentoAIInsight.timestamp.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Documento", "Tipo", "Dettagli", "Severità", "Stato", "Data Analisi"])
    
    for insight in insights:
        writer.writerow([
            insight.id,
            insight.document.title if insight.document else "N/A",
            insight.tipo,
            insight.valore or "",
            insight.severity,
            insight.status,
            insight.timestamp.strftime("%Y-%m-%d %H:%M") if insight.timestamp else "N/A"
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=ai_insights.csv"}
    )


# === ROUTE TASK AI ===

@admin_bp.route('/ai/tasks')
@login_required
def ai_tasks():
    """
    Dashboard per la gestione dei task AI generati automaticamente.
    
    Returns:
        html: Template con la lista dei task AI.
    """
    if not current_user.is_admin:
        abort(403)
    
    # Recupera tutti i task generati dall'AI
    tasks = Task.query.filter_by(created_by='AI System').order_by(Task.created_at.desc()).all()
    
    # Statistiche
    stats = {
        'totali': len(tasks),
        'da_fare': len([t for t in tasks if t.stato == 'Da fare']),
        'in_corso': len([t for t in tasks if t.stato == 'In corso']),
        'completati': len([t for t in tasks if t.stato == 'Completato']),
        'critici': len([t for t in tasks if t.priorita == 'Critica']),
        'scaduti': len([t for t in tasks if t.is_overdue])
    }
    
    return render_template('admin/ai_tasks.html', tasks=tasks, stats=stats)


@admin_bp.route('/ai/tasks/<int:task_id>/update', methods=['POST'])
@login_required
def update_ai_task(task_id):
    """
    Aggiorna lo stato di un task AI.
    
    Args:
        task_id (int): ID del task.
        
    Returns:
        json: Risultato dell'operazione.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accesso negato'})
    
    try:
        task = Task.query.get_or_404(task_id)
        nuovo_stato = request.form.get('stato')
        note = request.form.get('note', '')
        
        if nuovo_stato not in ['Da fare', 'In corso', 'Completato', 'Annullato']:
            return jsonify({'success': False, 'message': 'Stato non valido'})
        
        task.stato = nuovo_stato
        if nuovo_stato == 'Completato':
            task.completed_at = datetime.utcnow()
        
        if note:
            task.descrizione += f"\n\n📝 Note aggiuntive ({datetime.utcnow().strftime('%d/%m/%Y %H:%M')}): {note}"
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Task aggiornato con successo'})
        
    except Exception as e:
        print(f"Errore durante l'aggiornamento del task: {e}")
        return jsonify({'success': False, 'message': str(e)})


@admin_bp.route('/ai/tasks/export')
@login_required
def export_ai_tasks():
    """
    Esporta i task AI in formato CSV.
    
    Returns:
        csv: File CSV con i task AI.
    """
    if not current_user.is_admin:
        abort(403)
    
    tasks = Task.query.filter_by(created_by='AI System').order_by(Task.created_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Titolo", "Priorità", "Stato", "Assegnato a", "Scadenza", "Creato il", "Completato il"])
    
    for task in tasks:
        writer.writerow([
            task.id,
            task.titolo,
            task.priorita,
            task.stato,
            task.assegnato_a or "N/A",
            task.scadenza.strftime("%Y-%m-%d") if task.scadenza else "N/A",
            task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else "N/A",
            task.completed_at.strftime("%Y-%m-%d %H:%M") if task.completed_at else "N/A"
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=ai_tasks.csv"}
    )


@admin_bp.route('/ai/tasks/cleanup', methods=['POST'])
@login_required
def cleanup_ai_tasks():
    """
    Pulisce i task AI obsoleti.
    
    Returns:
        json: Risultato dell'operazione.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accesso negato'})
    
    try:
        from ai.task_generator import pulisci_task_obsoleti
        count = pulisci_task_obsoleti()
        
        return jsonify({'success': True, 'message': f'Eliminati {count} task obsoleti'})
        
    except Exception as e:
        print(f"Errore durante la pulizia dei task: {e}")
        return jsonify({'success': False, 'message': str(e)})


@admin_bp.route('/ai/tasks/stats')
@login_required
def ai_tasks_stats():
    """
    Restituisce statistiche sui task AI.
    
    Returns:
        json: Statistiche sui task AI.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accesso negato'})
    
    try:
        tasks = Task.query.filter_by(created_by='AI System').all()
        
        # Statistiche per modulo
        qms_tasks = [t for t in tasks if 'QMS' in t.descrizione]
        focusme_tasks = [t for t in tasks if 'FocusMe' in t.descrizione]
        
        stats = {
            'totali': len(tasks),
            'qms': len(qms_tasks),
            'focusme': len(focusme_tasks),
            'da_fare': len([t for t in tasks if t.stato == 'Da fare']),
            'in_corso': len([t for t in tasks if t.stato == 'In corso']),
            'completati': len([t for t in tasks if t.stato == 'Completato']),
            'critici': len([t for t in tasks if t.priorita == 'Critica']),
            'scaduti': len([t for t in tasks if t.is_overdue])
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        print(f"Errore durante il calcolo delle statistiche: {e}")
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/ai/alerts')
@login_required
def ai_alerts():
    """
    Visualizza gli alert AI per comportamenti sospetti.
    
    Returns:
        template: Pagina con gli alert AI.
    """
    if not current_user.is_admin:
        abort(403)
    
    try:
        # Recupera alert recenti (ultime 24 ore)
        alerts = get_recent_alerts(24)
        
        # Recupera statistiche
        stats = get_alert_statistics()
        
        # Filtri
        severity_filter = request.args.get('severity', '')
        type_filter = request.args.get('type', '')
        resolved_filter = request.args.get('resolved', '')
        
        # Applica filtri
        if severity_filter:
            alerts = [a for a in alerts if a.severity == severity_filter]
        if type_filter:
            alerts = [a for a in alerts if a.alert_type == type_filter]
        if resolved_filter == 'true':
            alerts = [a for a in alerts if a.resolved]
        elif resolved_filter == 'false':
            alerts = [a for a in alerts if not a.resolved]
        
        return render_template('admin/ai_alerts.html', 
                             alerts=alerts, 
                             stats=stats,
                             severity_filter=severity_filter,
                             type_filter=type_filter,
                             resolved_filter=resolved_filter)
                             
    except Exception as e:
        print(f"Errore durante caricamento alert AI: {e}")
        flash('Errore durante caricamento alert AI', 'danger')
        return render_template('admin/ai_alerts.html', alerts=[], stats={})


@admin_bp.route('/ai/alerts/analyze', methods=['POST'])
@login_required
def analyze_suspicious_downloads():
    """
    Esegue analisi manuale dei download sospetti.
    
    Returns:
        json: Risultato dell'analisi.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accesso negato'})
    
    try:
        # Esegue analisi
        alerts = analizza_download_sospetti()
        
        # Crea alert nel database
        created_alerts = []
        for alert_data in alerts:
            alert = create_ai_alert(alert_data)
            if alert:
                created_alerts.append(alert)
        
        return jsonify({
            'success': True, 
            'message': f'Analisi completata: {len(created_alerts)} alert generati',
            'alerts_count': len(created_alerts)
        })
        
    except Exception as e:
        print(f"Errore durante analisi download sospetti: {e}")
        return jsonify({'success': False, 'message': str(e)})


@admin_bp.route('/ai/alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
def resolve_ai_alert(alert_id):
    """
    Marca un alert AI come risolto.
    
    Args:
        alert_id: ID dell'alert da risolvere
        
    Returns:
        json: Risultato dell'operazione.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accesso negato'})
    
    try:
        from services.ai_monitoring import ai_monitoring_service
        
        success = ai_monitoring_service.resolve_alert(alert_id, current_user.username)
        
        if success:
            return jsonify({'success': True, 'message': 'Alert risolto con successo'})
        else:
            return jsonify({'success': False, 'message': 'Alert non trovato'})
            
    except Exception as e:
        print(f"Errore durante risoluzione alert: {e}")
        return jsonify({'success': False, 'message': str(e)})


@admin_bp.route('/ai/alerts/export')
@login_required
def export_ai_alerts():
    """
    Esporta gli alert AI in formato CSV.
    
    Returns:
        csv: File CSV con gli alert AI.
    """
    if not current_user.is_admin:
        abort(403)
    
    try:
        alerts = AIAlert.query.order_by(AIAlert.created_at.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Tipo Alert", "Utente", "Documento", "Severità", 
            "Descrizione", "IP", "Risolto", "Risolto da", "Data Creazione", "Data Risoluzione"
        ])
        
        for alert in alerts:
            user = User.query.get(alert.user_id)
            document = Document.query.get(alert.document_id) if alert.document_id else None
            
            writer.writerow([
                alert.id,
                alert.alert_type_display,
                user.username if user else 'N/A',
                document.title if document else 'N/A',
                alert.severity,
                alert.description,
                alert.ip_address or 'N/A',
                'Sì' if alert.resolved else 'No',
                alert.resolved_by or 'N/A',
                alert.created_at.strftime("%Y-%m-%d %H:%M") if alert.created_at else 'N/A',
                alert.resolved_at.strftime("%Y-%m-%d %H:%M") if alert.resolved_at else 'N/A'
            ])
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={"Content-Disposition": "attachment; filename=ai_alerts.csv"}
        )
        
    except Exception as e:
        print(f"Errore durante esportazione alert AI: {e}")
        flash('Errore durante esportazione', 'danger')
        return redirect(url_for('admin.ai_alerts'))


@admin_bp.route('/ai/alerts/stats')
@login_required
def ai_alerts_stats():
    """
    Restituisce statistiche sugli alert AI.
    
    Returns:
        json: Statistiche sugli alert AI.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accesso negato'})
    
    try:
        stats = get_alert_statistics()
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        print(f"Errore durante calcolo statistiche alert: {e}")
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/download_logs')
@login_required
def download_logs():
    """
    Visualizza i log dei download con filtri avanzati.
    
    Returns:
        template: Pagina con i log dei download.
    """
    if not current_user.is_admin:
        abort(403)
    
    try:
        # Recupera tutti i log di download con relazioni
        query = DownloadLog.query.join(User).join(Document).join(Company)
        
        # Filtri
        user_filter = request.args.get('user_id', '')
        document_filter = request.args.get('document_id', '')
        company_filter = request.args.get('company_id', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Applica filtri
        if user_filter:
            query = query.filter(DownloadLog.user_id == user_filter)
        if document_filter:
            query = query.filter(DownloadLog.document_id == document_filter)
        if company_filter:
            query = query.filter(Document.company_id == company_filter)
        if date_from:
            query = query.filter(DownloadLog.timestamp >= datetime.strptime(date_from, '%Y-%m-%d'))
        if date_to:
            query = query.filter(DownloadLog.timestamp <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        
        # Ordina per timestamp decrescente
        logs = query.order_by(DownloadLog.timestamp.desc()).all()
        
        # Recupera dati per filtri
        users = User.query.filter(User.role.in_(['user', 'admin'])).order_by(User.username).all()
        documents = Document.query.order_by(Document.title).all()
        companies = Company.query.order_by(Company.name).all()
        
        # Statistiche
        total_downloads = len(logs)
        unique_users = len(set(log.user_id for log in logs))
        unique_documents = len(set(log.document_id for log in logs))
        
        # Download per periodo (ultimi 30 giorni)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_downloads = DownloadLog.query.filter(DownloadLog.timestamp >= thirty_days_ago).count()
        
        stats = {
            'total': total_downloads,
            'unique_users': unique_users,
            'unique_documents': unique_documents,
            'recent_30_days': recent_downloads
        }
        
        return render_template('admin/download_logs.html', 
                             logs=logs,
                             users=users,
                             documents=documents,
                             companies=companies,
                             stats=stats,
                             user_filter=user_filter,
                             document_filter=document_filter,
                             company_filter=company_filter,
                             date_from=date_from,
                             date_to=date_to)
                             
    except Exception as e:
        print(f"Errore durante caricamento log download: {e}")
        flash('Errore durante caricamento log download', 'danger')
        return render_template('admin/download_logs.html', logs=[], stats={})


@admin_bp.route('/download_logs/export')
@login_required
def export_download_logs():
    """
    Esporta i log dei download in formato CSV.
    
    Returns:
        csv: File CSV con i log dei download.
    """
    if not current_user.is_admin:
        abort(403)
    
    try:
        # Recupera tutti i log con relazioni
        query = DownloadLog.query.join(User).join(Document).join(Company)
        
        # Applica stessi filtri della pagina
        user_filter = request.args.get('user_id', '')
        document_filter = request.args.get('document_id', '')
        company_filter = request.args.get('company_id', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        if user_filter:
            query = query.filter(DownloadLog.user_id == user_filter)
        if document_filter:
            query = query.filter(DownloadLog.document_id == document_filter)
        if company_filter:
            query = query.filter(Document.company_id == company_filter)
        if date_from:
            query = query.filter(DownloadLog.timestamp >= datetime.strptime(date_from, '%Y-%m-%d'))
        if date_to:
            query = query.filter(DownloadLog.timestamp <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        
        logs = query.order_by(DownloadLog.timestamp.desc()).all()
        
        # Crea CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "ID", "Data e Ora", "Utente", "Email Utente", "File Scaricato", 
            "Azienda", "Reparto", "IP Accesso", "Metodo", "Note"
        ])
        
        # Dati
        for log in logs:
            # Recupera dati relazionati
            user = log.user
            document = log.document
            company = document.company if document else None
            department = document.department if document else None
            
            # Determina metodo di accesso (per ora placeholder)
            method = "Web"  # In futuro si può estendere con più dettagli
            
            writer.writerow([
                log.id,
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else 'N/A',
                user.username if user else 'N/A',
                user.email if user else 'N/A',
                document.title if document else 'N/A',
                company.name if company else 'N/A',
                department.name if department else 'N/A',
                getattr(log, 'ip_address', 'N/A') or 'N/A',
                method,
                getattr(log, 'note', '') or ''
            ])
        
        output.seek(0)
        
        # Nome file con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"download_logs_{timestamp}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        print(f"Errore durante esportazione log download: {e}")
        flash('Errore durante esportazione', 'danger')
        return redirect(url_for('admin.download_logs'))


@admin_bp.route('/download_logs/stats')
@login_required
def download_logs_stats():
    """
    Restituisce statistiche sui log dei download.
    
    Returns:
        json: Statistiche sui log dei download.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Accesso negato'})
    
    try:
        from sqlalchemy import func
        
        # Statistiche generali
        total_downloads = DownloadLog.query.count()
        
        # Download ultimi 30 giorni
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_downloads = DownloadLog.query.filter(DownloadLog.timestamp >= thirty_days_ago).count()
        
        # Download ultimi 7 giorni
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        weekly_downloads = DownloadLog.query.filter(DownloadLog.timestamp >= seven_days_ago).count()
        
        # Download oggi
        today = datetime.utcnow().date()
        today_downloads = DownloadLog.query.filter(
            func.date(DownloadLog.timestamp) == today
        ).count()
        
        # Top utenti (ultimi 30 giorni)
        top_users = db.session.query(
            User.username,
            func.count(DownloadLog.id).label('download_count')
        ).join(DownloadLog).filter(
            DownloadLog.timestamp >= thirty_days_ago
        ).group_by(User.id, User.username).order_by(
            func.count(DownloadLog.id).desc()
        ).limit(5).all()
        
        # Top documenti (ultimi 30 giorni)
        top_documents = db.session.query(
            Document.title,
            func.count(DownloadLog.id).label('download_count')
        ).join(DownloadLog).filter(
            DownloadLog.timestamp >= thirty_days_ago
        ).group_by(Document.id, Document.title).order_by(
            func.count(DownloadLog.id).desc()
        ).limit(5).all()
        
        stats = {
            'total_downloads': total_downloads,
            'recent_30_days': recent_downloads,
            'weekly_downloads': weekly_downloads,
            'today_downloads': today_downloads,
            'top_users': [{'username': u.username, 'count': u.download_count} for u in top_users],
            'top_documents': [{'title': d.title, 'count': d.download_count} for d in top_documents]
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        print(f"Errore durante calcolo statistiche log download: {e}")
        return jsonify({'success': False, 'message': str(e)})
