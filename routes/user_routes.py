from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Document, DownloadLog, Task, AccessRequest
from extensions import db
from sqlalchemy import and_, func
from datetime import datetime, timedelta
from utils.logging import log_request_created

# === Inizializza il Blueprint ===
user_bp = Blueprint('user', __name__, url_prefix='/user')

# === Visualizza i guest associati all'utente ===
@user_bp.route('/my_guests')
@login_required
def my_guests():
    if current_user.role != 'user':
        return "Accesso negato", 403

    return render_template('user/my_guests.html')

# === Visualizza i documenti personali dell'utente ===
@user_bp.route('/my_documents')
@login_required
def my_documents():
    if current_user.role != 'user':
        return "Accesso negato", 403

    # Filtri AI
    tag_filter = request.args.get('tag_filter')
    modulo_filter = request.args.get('modulo_filter')
    categoria_filter = request.args.get('categoria_filter')
    
    # Query base
    query = Document.query.filter_by(user_id=current_user.id)
    
    # Applica filtri
    if tag_filter:
        query = query.filter(Document.tag == tag_filter)
    
    if modulo_filter:
        query = query.filter(Document.collegato_a_modulo == modulo_filter)
    
    if categoria_filter:
        query = query.filter(Document.categoria_ai == categoria_filter)
    
    documents = query.all()
    return render_template('user/my_documents.html', documents=documents)


@user_bp.route('/my_downloads_chart')
@login_required
def my_downloads_chart():
    """
    Restituisce i dati dei download dell'utente per il grafico.
    
    Returns:
        json: Dati aggregati per giorno degli ultimi 30 giorni
    """
    try:
        # Calcola la data di 30 giorni fa
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Query per aggregare i download per giorno
        downloads_by_day = db.session.query(
            func.date(DownloadLog.timestamp).label('date'),
            func.count(DownloadLog.id).label('download_count')
        ).filter(
            DownloadLog.user_id == current_user.id,
            DownloadLog.timestamp >= thirty_days_ago
        ).group_by(
            func.date(DownloadLog.timestamp)
        ).order_by(
            func.date(DownloadLog.timestamp)
        ).all()
        
        # Prepara i dati per Chart.js
        dates = []
        counts = []
        
        # Crea un dizionario con tutti i giorni degli ultimi 30 giorni
        all_dates = {}
        for i in range(30):
            date = (datetime.utcnow() - timedelta(days=i)).date()
            all_dates[date] = 0
        
        # Popola con i dati reali
        for download in downloads_by_day:
            all_dates[download.date] = download.download_count
        
        # Ordina per data (più recente prima)
        sorted_dates = sorted(all_dates.items(), reverse=True)
        
        for date, count in sorted_dates:
            dates.append(date.strftime('%d/%m'))
            counts.append(count)
        
        # Statistiche aggiuntive
        total_downloads = sum(counts)
        avg_downloads = total_downloads / 30 if total_downloads > 0 else 0
        max_downloads = max(counts) if counts else 0
        
        # Trova il giorno con più download
        max_day = None
        if max_downloads > 0:
            for date, count in sorted_dates:
                if count == max_downloads:
                    max_day = date.strftime('%d/%m/%Y')
                    break
        
        return jsonify({
            'success': True,
            'data': {
                'labels': dates,
                'datasets': [{
                    'label': 'Download',
                    'data': counts,
                    'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'borderWidth': 2,
                    'tension': 0.1
                }]
            },
            'stats': {
                'total_downloads': total_downloads,
                'avg_downloads': round(avg_downloads, 1),
                'max_downloads': max_downloads,
                'max_day': max_day
            }
        })
        
    except Exception as e:
        print(f"Errore durante recupero dati download: {e}")
        return jsonify({
            'success': False,
            'message': 'Errore durante recupero dati',
            'data': {
                'labels': [],
                'datasets': [{
                    'label': 'Download',
                    'data': [],
                    'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'borderWidth': 2,
                    'tension': 0.1
                }]
            },
            'stats': {
                'total_downloads': 0,
                'avg_downloads': 0,
                'max_downloads': 0,
                'max_day': None
            }
        })


@user_bp.route('/my_downloads_csv')
@login_required
def export_my_downloads_csv():
    """
    Esporta i download personali dell'utente in formato CSV.
    
    Returns:
        csv: File CSV con i download personali
    """
    try:
        import csv
        import io
        from flask import Response
        
        # Recupera tutti i download dell'utente
        downloads = DownloadLog.query.filter_by(
            user_id=current_user.id
        ).join(Document).order_by(
            DownloadLog.timestamp.desc()
        ).all()
        
        # Crea CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Data e Ora", "File Scaricato", "Azienda", "Reparto", "IP Accesso"
        ])
        
        # Dati
        for download in downloads:
            document = download.document
            company = document.company if document else None
            department = document.department if document else None
            
            writer.writerow([
                download.timestamp.strftime("%Y-%m-%d %H:%M:%S") if download.timestamp else 'N/A',
                document.title if document else 'N/A',
                company.name if company else 'N/A',
                department.name if department else 'N/A',
                getattr(download, 'ip_address', 'N/A') or 'N/A'
            ])
        
        output.seek(0)
        
        # Nome file con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"miei_download_{timestamp}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        print(f"Errore durante esportazione download personali: {e}")
        return jsonify({'success': False, 'message': 'Errore durante esportazione'})


@user_bp.route('/my_tasks')
@login_required
def my_tasks():
    """
    Visualizza la pagina dei task personali dell'utente.
    
    Returns:
        template: Pagina con i task personali.
    """
    try:
        # Recupera tutti i task dell'utente
        tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
        
        # Statistiche
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.is_completed])
        pending_tasks = total_tasks - completed_tasks
        overdue_tasks = len([t for t in tasks if t.is_overdue])
        
        # Distribuzione per origine
        origin_stats = {}
        for task in tasks:
            origin = task.origine
            if origin not in origin_stats:
                origin_stats[origin] = 0
            origin_stats[origin] += 1
        
        stats = {
            'total': total_tasks,
            'completed': completed_tasks,
            'pending': pending_tasks,
            'overdue': overdue_tasks,
            'origin_stats': origin_stats
        }
        
        return render_template('user/user_tasks.html', tasks=tasks, stats=stats)
        
    except Exception as e:
        print(f"Errore durante caricamento task personali: {e}")
        flash('Errore durante caricamento task', 'danger')
        return render_template('user/user_tasks.html', tasks=[], stats={})


@user_bp.route('/my_tasks_ai')
@login_required
def my_tasks_ai():
    """
    Visualizza la pagina dei Task AI personali dell'utente.
    
    Returns:
        template: Pagina user_tasks.html per Task AI
    """
    if current_user.role != 'user':
        return "Accesso negato", 403
    
    return render_template('user/user_tasks.html')


@user_bp.route('/my_tasks/data')
@login_required
def my_tasks_data():
    """
    Restituisce i dati dei task personali in formato JSON.
    
    Returns:
        json: Dati dei task personali.
    """
    try:
        # Recupera tutti i task dell'utente
        tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
        
        # Prepara i dati per JSON
        tasks_data = []
        for task in tasks:
            task_data = {
                'id': task.id,
                'titolo': task.titolo,
                'descrizione': task.descrizione,
                'priorita': task.priorita,
                'stato': task.stato,
                'origine': task.origine,
                'origine_display': task.origine_display,
                'scadenza': task.scadenza.strftime('%Y-%m-%d %H:%M') if task.scadenza else None,
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M'),
                'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M') if task.completed_at else None,
                'is_completed': task.is_completed,
                'is_overdue': task.is_overdue,
                'days_until_deadline': task.days_until_deadline,
                'priority_color': task.priority_color,
                'status_color': task.status_color,
                'origine_badge_class': task.origine_badge_class
            }
            tasks_data.append(task_data)
        
        return jsonify({
            'success': True,
            'tasks': tasks_data
        })
        
    except Exception as e:
        print(f"Errore durante recupero dati task: {e}")
        return jsonify({
            'success': False,
            'message': 'Errore durante recupero dati',
            'tasks': []
        })


@user_bp.route('/my_tasks/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    """
    Segna un task come completato.
    
    Args:
        task_id: ID del task da completare
        
    Returns:
        json: Risultato dell'operazione.
    """
    try:
        # Recupera il task
        task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
        
        if not task:
            return jsonify({'success': False, 'message': 'Task non trovato'})
        
        # Aggiorna il task
        task.stato = "Completato"
        task.completed_at = datetime.utcnow()
        
        # Salva nel database
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task completato con successo',
            'task_id': task_id
        })
        
    except Exception as e:
        print(f"Errore durante completamento task: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Errore durante completamento task'})


@user_bp.route('/my_tasks/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    """
    Elimina un task personale.
    
    Args:
        task_id: ID del task da eliminare
        
    Returns:
        json: Risultato dell'operazione.
    """
    try:
        # Recupera il task
        task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
        
        if not task:
            return jsonify({'success': False, 'message': 'Task non trovato'})
        
        # Elimina il task
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task eliminato con successo',
            'task_id': task_id
        })
        
    except Exception as e:
        print(f"Errore durante eliminazione task: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Errore durante eliminazione task'})


@user_bp.route('/my_tasks/add', methods=['POST'])
@login_required
def add_task():
    """
    Aggiunge un nuovo task personale.
    
    Returns:
        json: Risultato dell'operazione.
    """
    try:
        # Recupera i dati dal form
        titolo = request.form.get('titolo')
        descrizione = request.form.get('descrizione', '')
        priorita = request.form.get('priorita', 'Media')
        scadenza_str = request.form.get('scadenza', '')
        origine = request.form.get('origine', 'Manuale')
        
        # Validazione
        if not titolo:
            return jsonify({'success': False, 'message': 'Titolo obbligatorio'})
        
        # Parsing della scadenza
        scadenza = None
        if scadenza_str:
            try:
                scadenza = datetime.strptime(scadenza_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                return jsonify({'success': False, 'message': 'Formato data non valido'})
        
        # Crea il nuovo task
        new_task = Task(
            user_id=current_user.id,
            titolo=titolo,
            descrizione=descrizione,
            priorita=priorita,
            scadenza=scadenza,
            origine=origine,
            created_by=current_user.email
        )
        
        # Salva nel database
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task creato con successo',
            'task_id': new_task.id
        })
        
    except Exception as e:
        print(f"Errore durante creazione task: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Errore durante creazione task'})


@user_bp.route('/my_tasks/export')
@login_required
def export_my_tasks():
    """
    Esporta i task personali in formato CSV.
    
    Returns:
        csv: File CSV con i task personali.
    """
    try:
        import csv
        import io
        from flask import Response
        
        # Recupera tutti i task dell'utente
        tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.created_at.desc()).all()
        
        # Crea CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "ID", "Titolo", "Descrizione", "Priorità", "Stato", "Origine", 
            "Scadenza", "Data Creazione", "Data Completamento"
        ])
        
        # Dati
        for task in tasks:
            writer.writerow([
                task.id,
                task.titolo,
                task.descrizione or '',
                task.priorita,
                task.stato,
                task.origine,
                task.scadenza.strftime("%Y-%m-%d %H:%M") if task.scadenza else 'N/A',
                task.created_at.strftime("%Y-%m-%d %H:%M"),
                task.completed_at.strftime("%Y-%m-%d %H:%M") if task.completed_at else 'N/A'
            ])
        
        output.seek(0)
        
        # Nome file con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"miei_task_{timestamp}.csv"
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        print(f"Errore durante esportazione task personali: {e}")
        return jsonify({'success': False, 'message': 'Errore durante esportazione'})


@user_bp.route('/request_access', methods=['POST'])
@login_required
def request_access():
    """
    Gestisce la richiesta di accesso con applicazione automatica delle policy e risk scoring.
    """
    try:
        document_id = request.form.get('file_id')
        reason = request.form.get('reason', '').strip()

        # Controllo validità
        if not document_id or not reason:
            flash("Devi specificare un motivo per la richiesta.", "danger")
            return redirect(request.referrer or url_for('main.home'))

        # Recupero documento
        document = Document.query.get_or_404(document_id)

        # Processa richiesta con policy automatiche
        from utils.policies import process_access_request_with_policies
        
        result = process_access_request_with_policies(
            user=current_user,
            document=document,
            note=reason
        )

        if not result['success']:
            flash(result['error'], "warning")
            return redirect(request.referrer or url_for('main.home'))

        # Applica risk scoring alla richiesta creata
        if result.get('request_id'):
            from utils.risk_scoring import apply_risk_score_to_request
            apply_risk_score_to_request(result['request_id'])

        # Gestisci risultato
        if result['auto_decision']:
            # Decisione automatica
            action = result['action']
            policy_name = result['policy_name']
            
            if action == 'approve':
                flash(f"✅ Accesso approvato automaticamente tramite regola: {policy_name}", "success")
            else:
                flash(f"❌ Accesso negato automaticamente tramite regola: {policy_name}", "warning")
        else:
            # Richiesta in attesa di approvazione
            flash("📋 Richiesta inviata con successo. In attesa di approvazione.", "info")

        return redirect(request.referrer or url_for('main.home'))

    except Exception as e:
        flash(f"Errore durante la richiesta di accesso: {str(e)}", "error")
        return redirect(request.referrer or url_for('main.home'))

@user_bp.route('/my_access_requests', methods=['GET'])
@login_required
def my_access_requests():
    """
    Visualizza lo storico delle richieste di accesso dell'utente corrente.
    """
    # Query semplificata come richiesto
    access_requests = AccessRequest.query \
        .filter_by(user_id=current_user.id) \
        .order_by(AccessRequest.created_at.desc()) \
        .all()
    
    return render_template("user/my_access_requests.html", requests=access_requests)
