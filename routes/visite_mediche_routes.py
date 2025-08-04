from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, current_app, send_file, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
import os
from datetime import datetime, date, timedelta
from models import db, VisitaMedica, User
from utils.audit_logger import log_event
import uuid
import csv
import zipfile
from io import StringIO, BytesIO
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Message
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Blueprint per le visite mediche
visite_mediche_bp = Blueprint('visite_mediche', __name__, url_prefix='/visite_mediche')

# Configurazione upload
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
UPLOAD_FOLDER = 'uploads/certificati_visite'

# Scheduler per reminder automatici
scheduler = BackgroundScheduler()
scheduler.start()

def allowed_file(filename):
    """Verifica se l'estensione del file è consentita."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_upload_folder():
    """Crea la cartella upload se non esiste."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def roles_required(roles):
    """Decorator per verificare i ruoli dell'utente."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Non autorizzato'}), 401
            
            if current_user.role not in roles:
                return jsonify({'error': 'Accesso negato'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_visita_action(azione, visita_id=None, dettagli=None):
    """Log automatico per audit compliance."""
    try:
        from models import LogVisitaMedica
        import json
        
        log_entry = LogVisitaMedica(
            visita_id=visita_id,
            user_id=current_user.id,
            azione=azione,
            dettagli=json.dumps(dettagli) if dettagli else None
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Errore nel logging visita medica: {str(e)}")

def send_reminder_email(visita):
    """Invia email reminder per visita in scadenza."""
    try:
        from app import mail
        from flask_mail import Message
        
        subject = f"Reminder visita medica in scadenza - {visita.user.username}"
        body = f"""
        Gentile {visita.user.username},
        
        la tua visita medica "{visita.tipo_visita}" scadrà il {visita.scadenza.strftime('%d/%m/%Y')}.
        
        Contatta HR per il rinnovo.
        
        Cordiali saluti,
        Sistema Gestione Documenti
        """
        
        msg = Message(
            subject=subject,
            recipients=[visita.user.email],
            body=body
        )
        mail.send(msg)
        
        current_app.logger.info(f"Reminder inviato per visita {visita.id}")
    except Exception as e:
        current_app.logger.error(f"Errore invio reminder: {str(e)}")

@visite_mediche_bp.route('/', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def lista_visite():
    """
    Lista tutte le visite mediche con filtri opzionali.
    
    Query params:
        - user_id: Filtra per utente specifico
        - stato: Filtra per stato (valida, scaduta, in_scadenza)
        - ruolo: Filtra per ruolo
        - tipo_visita: Filtra per tipo visita
    """
    try:
        # Parametri di filtro
        user_id = request.args.get('user_id', type=int)
        stato = request.args.get('stato')
        ruolo = request.args.get('ruolo')
        tipo_visita = request.args.get('tipo_visita')
        
        # Query base
        query = VisitaMedica.query.join(User)
        
        # Applica filtri
        if user_id:
            query = query.filter(VisitaMedica.user_id == user_id)
        if ruolo:
            query = query.filter(VisitaMedica.ruolo.ilike(f'%{ruolo}%'))
        if tipo_visita:
            query = query.filter(VisitaMedica.tipo_visita.ilike(f'%{tipo_visita}%'))
        
        # Filtro per stato
        if stato:
            today = date.today()
            if stato == 'scaduta':
                query = query.filter(VisitaMedica.scadenza < today)
            elif stato == 'in_scadenza':
                query = query.filter(
                    VisitaMedica.scadenza >= today,
                    VisitaMedica.scadenza <= today + timedelta(days=30)
                )
            elif stato == 'valida':
                query = query.filter(VisitaMedica.scadenza > today + timedelta(days=30))
        
        # Ordinamento per scadenza
        visite = query.order_by(VisitaMedica.scadenza.asc()).all()
        
        # Statistiche
        totali = {
            'totali': len(visite),
            'scadute': len([v for v in visite if v.is_expired]),
            'in_scadenza': len([v for v in visite if not v.is_expired and v.days_until_expiry <= 30]),
            'valide': len([v for v in visite if not v.is_expired and v.days_until_expiry > 30])
        }
        
        # Ottieni lista utenti per il form
        users = User.query.all()
        
        return render_template(
            'visite_mediche/lista_visite.html',
            visite=visite,
            statistiche=totali,
            users=users,
            now=date.today()
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nel caricamento visite mediche: {str(e)}")
        flash('Errore nel caricamento delle visite mediche', 'error')
        return redirect(url_for('dashboard'))

@visite_mediche_bp.route('/', methods=['POST'])
@login_required
@roles_required(['admin', 'ceo'])
def crea_visita():
    """
    Crea una nuova visita medica.
    
    Form data:
        - user_id: ID utente
        - ruolo: Ruolo del dipendente
        - tipo_visita: Tipo di visita
        - data_visita: Data visita (YYYY-MM-DD)
        - scadenza: Data scadenza (YYYY-MM-DD)
        - esito: Esito visita
        - note: Note aggiuntive
        - certificato: File certificato (opzionale)
    """
    try:
        # Validazione dati
        user_id = request.form.get('user_id', type=int)
        ruolo = request.form.get('ruolo', '').strip()
        tipo_visita = request.form.get('tipo_visita', '').strip()
        data_visita_str = request.form.get('data_visita')
        scadenza_str = request.form.get('scadenza')
        esito = request.form.get('esito', '').strip()
        note = request.form.get('note', '').strip()
        
        # Validazioni
        if not all([user_id, ruolo, tipo_visita, data_visita_str, scadenza_str, esito]):
            flash('Tutti i campi obbligatori devono essere compilati', 'error')
            return redirect(url_for('visite_mediche.lista_visite'))
        
        # Verifica utente esiste
        user = User.query.get(user_id)
        if not user:
            flash('Utente non trovato', 'error')
            return redirect(url_for('visite_mediche.lista_visite'))
        
        # Parsing date
        try:
            data_visita = datetime.strptime(data_visita_str, '%Y-%m-%d').date()
            scadenza = datetime.strptime(scadenza_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Formato date non valido', 'error')
            return redirect(url_for('visite_mediche.lista_visite'))
        
        # Validazione date
        if data_visita > scadenza:
            flash('La data di scadenza deve essere successiva alla data visita', 'error')
            return redirect(url_for('visite_mediche.lista_visite'))
        
        # Gestione file certificato
        certificato_filename = None
        certificato_path = None
        
        if 'certificato' in request.files:
            file = request.files['certificato']
            if file and file.filename and allowed_file(file.filename):
                ensure_upload_folder()
                
                # Genera nome file unico
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                
                # Salva file
                file.save(file_path)
                certificato_filename = filename
                certificato_path = file_path
        
        # Crea visita medica
        nuova_visita = VisitaMedica(
            user_id=user_id,
            ruolo=ruolo,
            tipo_visita=tipo_visita,
            data_visita=data_visita,
            scadenza=scadenza,
            esito=esito,
            certificato_filename=certificato_filename,
            certificato_path=certificato_path,
            note=note
        )
        
        db.session.add(nuova_visita)
        db.session.commit()
        
        # Log audit compliance
        log_visita_action('Creazione', nuova_visita.id, {
            'user_id': user_id,
            'ruolo': ruolo,
            'tipo_visita': tipo_visita,
            'data_visita': data_visita_str,
            'scadenza': scadenza_str,
            'esito': esito
        })
        
        flash(f'Visita medica creata con successo per {user.username}', 'success')
        return redirect(url_for('visite_mediche.lista_visite'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nella creazione visita medica: {str(e)}")
        flash('Errore nella creazione della visita medica', 'error')
        return redirect(url_for('visite_mediche.lista_visite'))

@visite_mediche_bp.route('/<int:visita_id>', methods=['PATCH'])
@login_required
@roles_required(['admin', 'ceo'])
def modifica_visita(visita_id):
    """
    Modifica una visita medica esistente.
    
    Args:
        visita_id (int): ID della visita da modificare
    """
    try:
        visita = VisitaMedica.query.get_or_404(visita_id)
        
        # Ottieni dati JSON
        data = request.get_json()
        
        # Campi modificabili
        if 'ruolo' in data:
            visita.ruolo = data['ruolo'].strip()
        if 'tipo_visita' in data:
            visita.tipo_visita = data['tipo_visita'].strip()
        if 'data_visita' in data:
            visita.data_visita = datetime.strptime(data['data_visita'], '%Y-%m-%d').date()
        if 'scadenza' in data:
            visita.scadenza = datetime.strptime(data['scadenza'], '%Y-%m-%d').date()
        if 'esito' in data:
            visita.esito = data['esito'].strip()
        if 'note' in data:
            visita.note = data['note'].strip()
        
        db.session.commit()
        
        # Log audit compliance
        log_visita_action('Modifica', visita_id, {
            'campi_modificati': list(data.keys()),
            'valori_precedenti': {
                'ruolo': visita.ruolo,
                'tipo_visita': visita.tipo_visita,
                'esito': visita.esito
            }
        })
        
        return jsonify({
            'success': True,
            'message': 'Visita medica aggiornata con successo',
            'visita': {
                'id': visita.id,
                'ruolo': visita.ruolo,
                'tipo_visita': visita.tipo_visita,
                'data_visita': visita.data_visita.isoformat(),
                'scadenza': visita.scadenza.isoformat(),
                'esito': visita.esito,
                'note': visita.note,
                'status_display': visita.status_display,
                'badge_class': visita.badge_class
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nella modifica visita medica {visita_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nella modifica della visita medica'
        }), 500

@visite_mediche_bp.route('/<int:visita_id>', methods=['DELETE'])
@login_required
@roles_required(['admin', 'ceo'])
def elimina_visita(visita_id):
    """
    Elimina una visita medica.
    
    Args:
        visita_id (int): ID della visita da eliminare
    """
    try:
        visita = VisitaMedica.query.get_or_404(visita_id)
        
        # Elimina file certificato se presente
        if visita.certificato_path and os.path.exists(visita.certificato_path):
            os.remove(visita.certificato_path)
        
        # Log prima dell'eliminazione
        user_info = visita.user.username if visita.user else "N/A"
        
        # Log audit compliance
        log_visita_action('Eliminazione', visita_id, {
            'user_id': visita.user_id,
            'ruolo': visita.ruolo,
            'tipo_visita': visita.tipo_visita,
            'data_visita': visita.data_visita.isoformat(),
            'scadenza': visita.scadenza.isoformat(),
            'esito': visita.esito
        })
        
        db.session.delete(visita)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Visita medica eliminata con successo'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nell'eliminazione visita medica {visita_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nell\'eliminazione della visita medica'
        }), 500

@visite_mediche_bp.route('/<int:visita_id>/certificato', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def scarica_certificato(visita_id):
    """
    Scarica il certificato di una visita medica.
    
    Args:
        visita_id (int): ID della visita
    """
    try:
        visita = VisitaMedica.query.get_or_404(visita_id)
        
        if not visita.certificato_path or not os.path.exists(visita.certificato_path):
            flash('Certificato non trovato', 'error')
            return redirect(url_for('visite_mediche.lista_visite'))
        
        # Log download
        log_event(
            document_id=None,
            user_id=current_user.id,
            evento="certificato_scaricato",
            note_ai=f"Scaricato certificato visita medica ID {visita_id} per {visita.user.username}"
        )
        
        return send_file(
            visita.certificato_path,
            as_attachment=True,
            download_name=visita.certificato_filename
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nel download certificato {visita_id}: {str(e)}")
        flash('Errore nel download del certificato', 'error')
        return redirect(url_for('visite_mediche.lista_visite'))

@visite_mediche_bp.route('/statistiche', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def statistiche_visite():
    """
    Restituisce statistiche sulle visite mediche.
    """
    try:
        # Statistiche generali
        totali = VisitaMedica.query.count()
        scadute = VisitaMedica.query.filter(VisitaMedica.scadenza < date.today()).count()
        in_scadenza = VisitaMedica.query.filter(
            VisitaMedica.scadenza >= date.today(),
            VisitaMedica.scadenza <= date.today() + timedelta(days=30)
        ).count()
        
        # Statistiche per ruolo
        ruoli_stats = db.session.query(
            VisitaMedica.ruolo,
            db.func.count(VisitaMedica.id).label('count')
        ).group_by(VisitaMedica.ruolo).all()
        
        # Prossime scadenze (7 giorni)
        prossime_scadenze = VisitaMedica.query.filter(
            VisitaMedica.scadenza >= date.today(),
            VisitaMedica.scadenza <= date.today() + timedelta(days=7)
        ).order_by(VisitaMedica.scadenza.asc()).all()
        
        return jsonify({
            'success': True,
            'statistiche': {
                'totali': totali,
                'scadute': scadute,
                'in_scadenza': in_scadenza,
                'valide': totali - scadute - in_scadenza
            },
            'ruoli_stats': [{'ruolo': r.ruolo, 'count': r.count} for r in ruoli_stats],
            'prossime_scadenze': [
                {
                    'id': v.id,
                    'user': v.user.username if v.user else 'N/A',
                    'tipo_visita': v.tipo_visita,
                    'scadenza': v.scadenza.isoformat(),
                    'giorni_rimanenti': v.days_until_expiry
                }
                for v in prossime_scadenze
            ]
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nel calcolo statistiche visite: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nel calcolo delle statistiche'
        }), 500

@visite_mediche_bp.route('/export/csv', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def export_csv():
    """
    Export CSV di tutte le visite mediche per audit/report.
    Supporta filtri: tutte, scadenza, scadute
    """
    try:
        # Ottieni parametri di filtro
        filtro = request.args.get('filtro', 'tutte')  # "tutte", "scadenza", "scadute"
        
        # Query tutte le visite con join utente
        visite = VisitaMedica.query.join(User).order_by(VisitaMedica.scadenza.asc()).all()
        oggi = date.today()
        
        # Filtra visite se necessario
        if filtro == "scadenza":
            visite = [v for v in visite if v.scadenza and v.scadenza <= oggi + timedelta(days=30)]
        elif filtro == "scadute":
            visite = [v for v in visite if v.scadenza and v.scadenza < oggi]
        
        # Crea CSV in memoria
        si = StringIO()
        cw = csv.writer(si)
        
        # Header
        cw.writerow([
            'ID', 'Utente', 'Email', 'Ruolo', 'Tipo Visita', 
            'Data Visita', 'Scadenza', 'Esito', 'Stato', 
            'Giorni alla Scadenza', 'Certificato', 'Note', 'Data Creazione'
        ])
        
        # Dati
        for visita in visite:
            cw.writerow([
                visita.id,
                visita.user.username if visita.user else 'N/A',
                visita.user.email if visita.user else 'N/A',
                visita.ruolo,
                visita.tipo_visita,
                visita.data_visita.strftime('%d/%m/%Y'),
                visita.scadenza.strftime('%d/%m/%Y'),
                visita.esito,
                visita.status_display,
                visita.days_until_expiry,
                'Sì' if visita.certificato_filename else 'No',
                visita.note or '',
                visita.created_at.strftime('%d/%m/%Y %H:%M')
            ])
        
        # Log audit
        log_visita_action('Export CSV', None, {
            'num_visite_esportate': len(visite),
            'filtro': filtro,
            'timestamp_export': datetime.now().isoformat()
        })
        
        # Prepara response
        output = si.getvalue()
        si.close()
        
        return Response(
            output,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=visite_mediche_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'export CSV: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nell\'export CSV'
        }), 500

@visite_mediche_bp.route('/export/pdf', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def export_pdf():
    """
    Export PDF di tutte le visite mediche per audit/report.
    """
    try:
        # Ottieni parametri di filtro
        filtro = request.args.get('filtro', 'tutte')  # "tutte", "scadenza", "scadute"
        
        # Query visite con join utente
        visite = VisitaMedica.query.join(User).order_by(VisitaMedica.scadenza.asc()).all()
        oggi = date.today()
        
        # Filtra visite se necessario
        if filtro == "scadenza":
            visite = [v for v in visite if v.scadenza and v.scadenza <= oggi + timedelta(days=30)]
        elif filtro == "scadute":
            visite = [v for v in visite if v.scadenza and v.scadenza < oggi]
        
        # Crea PDF
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Header
        y = height - 50
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, y, "Archivio Visite Mediche")
        y -= 20
        
        p.setFont("Helvetica", 10)
        p.drawString(50, y, f"Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        y -= 20
        
        if filtro != "tutte":
            p.drawString(50, y, f"Filtro: {filtro.upper()}")
            y -= 20
        
        p.drawString(50, y, f"Totale visite: {len(visite)}")
        y -= 30
        
        # Intestazione tabella
        p.setFont("Helvetica-Bold", 9)
        intestazione = ["Utente", "Mansione", "Tipo Visita", "Data", "Scadenza", "Esito", "Certificato"]
        x_positions = [50, 120, 180, 250, 320, 390, 450]
        
        for i, col in enumerate(intestazione):
            p.drawString(x_positions[i], y, col)
        y -= 15
        
        # Separatore
        p.line(50, y, width-50, y)
        y -= 10
        
        # Dati
        p.setFont("Helvetica", 8)
        for visita in visite:
            if y < 80:  # Nuova pagina se necessario
                p.showPage()
                y = height - 50
                p.setFont("Helvetica", 8)
            
            dati = [
                visita.user.username if visita.user else 'N/A',
                visita.ruolo,
                visita.tipo_visita,
                visita.data_visita.strftime('%d/%m/%Y') if visita.data_visita else "",
                visita.scadenza.strftime('%d/%m/%Y') if visita.scadenza else "",
                visita.esito or "",
                "✓" if visita.certificato_filename else "✗"
            ]
            
            for i, campo in enumerate(dati):
                # Tronca testo se troppo lungo
                testo = str(campo)[:15] + "..." if len(str(campo)) > 15 else str(campo)
                p.drawString(x_positions[i], y, testo)
            
            y -= 12
        
        # Footer
        p.showPage()
        y = height - 50
        p.setFont("Helvetica-Oblique", 8)
        p.drawString(50, y, f"Documento generato da SYNTHIA DOCS - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        y -= 15
        p.drawString(50, y, "Sistema di Gestione Documentale Mercury S.r.l.")
        
        # Log audit
        log_visita_action('Export PDF', None, {
            'num_visite_esportate': len(visite),
            'filtro': filtro,
            'timestamp_export': datetime.now().isoformat()
        })
        
        p.save()
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"archivio_visite_mediche_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mimetype="application/pdf"
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'export PDF: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nell\'export PDF'
        }), 500

@visite_mediche_bp.route('/export/zip', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def export_zip_visite():
    """
    Export ZIP completo delle visite mediche con PDF, certificati e log.
    
    Query params:
        - mansione: Filtra per mansione
        - utente: Filtra per ID utente
        - dal: Data inizio (YYYY-MM-DD)
        - al: Data fine (YYYY-MM-DD)
    """
    try:
        # Ottieni parametri di filtro
        filtro_mansione = request.args.get('mansione')
        filtro_user = request.args.get('utente')
        dal = request.args.get('dal')  # "YYYY-MM-DD"
        al = request.args.get('al')    # "YYYY-MM-DD"
        stato = request.args.get('stato')  # "scadute", "in_scadenza", "valide"
        
        # Crea ZIP in memoria
        buffer = BytesIO()
        zipf = zipfile.ZipFile(buffer, "w")
        
        # Query tutte le visite con join utente
        visite = VisitaMedica.query.join(User).all()
        risultati = []
        
        # Applica filtri
        oggi = date.today()
        for v in visite:
            # Filtro mansione
            if filtro_mansione and getattr(v.utente, "mansione", "") != filtro_mansione:
                continue
            # Filtro utente
            if filtro_user and str(v.user_id) != filtro_user:
                continue
            # Filtro periodo
            if dal and v.data_visita and v.data_visita < datetime.strptime(dal, "%Y-%m-%d").date():
                continue
            if al and v.data_visita and v.data_visita > datetime.strptime(al, "%Y-%m-%d").date():
                continue
            # Filtro stato
            if stato:
                if stato == 'scadute' and (not v.scadenza or v.scadenza >= oggi):
                    continue
                elif stato == 'in_scadenza' and (not v.scadenza or v.scadenza < oggi or v.scadenza > oggi + timedelta(days=30)):
                    continue
                elif stato == 'valide' and (not v.scadenza or v.scadenza <= oggi + timedelta(days=30)):
                    continue
            risultati.append(v)
        
        # PDF per ogni visita
        for v in risultati:
            pdf_buffer = BytesIO()
            pdf = canvas.Canvas(pdf_buffer, pagesize=A4)
            width, height = A4
            y = height - 50
            
            # Header
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(50, y, f"Visita Medica - {v.utente.username if v.utente else 'N/A'}")
            y -= 30
            
            # Dati visita
            pdf.setFont("Helvetica", 12)
            pdf.drawString(50, y, f"Utente: {v.utente.username if v.utente else 'N/A'}")
            y -= 20
            pdf.drawString(50, y, f"Tipo Visita: {v.tipo_visita}")
            y -= 20
            pdf.drawString(50, y, f"Data Visita: {v.data_visita.strftime('%d/%m/%Y') if v.data_visita else 'N/A'}")
            y -= 20
            pdf.drawString(50, y, f"Scadenza: {v.scadenza.strftime('%d/%m/%Y') if v.scadenza else 'N/A'}")
            y -= 20
            pdf.drawString(50, y, f"Esito: {v.esito or 'N/A'}")
            y -= 20
            pdf.drawString(50, y, f"Ruolo: {v.ruolo}")
            y -= 20
            if v.note:
                pdf.drawString(50, y, f"Note: {v.note}")
                y -= 20
            
            # Footer
            y -= 30
            pdf.setFont("Helvetica-Oblique", 10)
            pdf.drawString(50, y, f"Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            y -= 15
            pdf.drawString(50, y, "SYNTHIA DOCS - Sistema di Gestione Documentale")
            
            pdf.save()
            pdf_buffer.seek(0)
            zipf.writestr(f"visita_{v.id}_{v.utente.username if v.utente else 'N/A'}.pdf", pdf_buffer.getvalue())
            
            # Certificato originale se presente
            if v.certificato_filename and v.allegato_certificato:
                zipf.writestr(f"certificato_{v.id}_{v.certificato_filename}", v.allegato_certificato)
        
        # CSV LOG REMINDER
        csv1 = StringIO()
        writer1 = csv.writer(csv1)
        writer1.writerow(["ID Visita", "Tipo", "Data Invio", "Destinatari"])
        
        try:
            from models import LogReminderVisita
            for r in LogReminderVisita.query.all():
                writer1.writerow([
                    r.visita_id, 
                    r.tipo, 
                    r.data_invio.strftime('%d/%m/%Y') if r.data_invio else 'N/A',
                    r.destinatari or 'N/A'
                ])
        except ImportError:
            # Se il modello non esiste, crea CSV vuoto
            writer1.writerow(["N/A", "N/A", "N/A", "N/A"])
        
        zipf.writestr("log_reminder.csv", csv1.getvalue())
        
        # CSV LOG EXPORT (se il modello esiste)
        csv2 = StringIO()
        writer2 = csv.writer(csv2)
        writer2.writerow(["Data Export", "Filtro", "Tipo", "Utente", "Numero Visite"])
        
        # Log dell'export corrente
        writer2.writerow([
            datetime.now().strftime('%d/%m/%Y %H:%M'),
            f"mansione={filtro_mansione or 'tutte'}, utente={filtro_user or 'tutti'}, dal={dal or 'tutte'}, al={al or 'tutte'}, stato={stato or 'tutti'}",
            "ZIP_COMPLETO",
            current_user.username,
            len(risultati)
        ])
        
        zipf.writestr("log_export.csv", csv2.getvalue())
        
        # File README con informazioni
        readme_content = f"""
ARCHIVIO VISITE MEDICHE - SYNTHIA DOCS
=======================================

Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Utente: {current_user.username}
Filtri applicati:
- Mansione: {filtro_mansione or 'Tutte'}
- Utente: {filtro_user or 'Tutti'}
- Periodo: {dal or 'Tutte'} - {al or 'Tutte'}
- Stato: {stato or 'Tutti'}

Contenuto:
- PDF per ogni visita (riassunto)
- Certificati originali (se presenti)
- log_reminder.csv (log reminder inviati)
- log_export.csv (log export effettuati)

Totale visite incluse: {len(risultati)}

---
SYNTHIA DOCS - Sistema di Gestione Documentale
Mercury S.r.l.
        """
        
        zipf.writestr("README.txt", readme_content)
        
        zipf.close()
        buffer.seek(0)
        
        # Log audit
        log_visita_action('Export ZIP', None, {
            'num_visite_esportate': len(risultati),
            'filtro_mansione': filtro_mansione,
            'filtro_user': filtro_user,
            'periodo_dal': dal,
            'periodo_al': al,
            'filtro_stato': stato,
            'timestamp_export': datetime.now().isoformat()
        })
        
        return send_file(
            buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"archivio_visite_completo_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
        )
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'export ZIP: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nell\'export ZIP'
        }), 500

@visite_mediche_bp.route('/<int:visita_id>', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def get_visita(visita_id):
    """
    Ottiene i dati di una singola visita medica.
    
    Args:
        visita_id (int): ID della visita
    """
    try:
        visita = VisitaMedica.query.get_or_404(visita_id)
        
        return jsonify({
            'success': True,
            'visita': {
                'id': visita.id,
                'user_id': visita.user_id,
                'user': {
                    'username': visita.user.username if visita.user else 'N/A',
                    'email': visita.user.email if visita.user else 'N/A'
                },
                'ruolo': visita.ruolo,
                'tipo_visita': visita.tipo_visita,
                'data_visita': visita.data_visita.isoformat(),
                'scadenza': visita.scadenza.isoformat(),
                'esito': visita.esito,
                'note': visita.note,
                'certificato_filename': visita.certificato_filename,
                'status_display': visita.status_display,
                'badge_class': visita.badge_class,
                'days_until_expiry': visita.days_until_expiry,
                'is_expired': visita.is_expired
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nel recupero visita {visita_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nel recupero della visita'
        }), 500

def setup_reminder_jobs():
    """Configura i job per i reminder automatici."""
    try:
        # Job per reminder 30 giorni prima
        scheduler.add_job(
            func=check_visite_scadenza_30_giorni,
            trigger='cron',
            hour=9,
            minute=0,
            id='reminder_30_giorni'
        )
        
        # Job per reminder 7 giorni prima
        scheduler.add_job(
            func=check_visite_scadenza_7_giorni,
            trigger='cron',
            hour=9,
            minute=0,
            id='reminder_7_giorni'
        )
        
        # Job per reminder giorno stesso
        scheduler.add_job(
            func=check_visite_scadenza_oggi,
            trigger='cron',
            hour=9,
            minute=0,
            id='reminder_oggi'
        )
        
        current_app.logger.info("Job reminder visite mediche configurati")
    except Exception as e:
        current_app.logger.error(f"Errore configurazione job reminder: {str(e)}")

def check_visite_scadenza_30_giorni():
    """Controlla visite che scadono tra 30 giorni."""
    try:
        from datetime import date
        data_limite = date.today() + timedelta(days=30)
        
        visite = VisitaMedica.query.filter(
            VisitaMedica.scadenza == data_limite
        ).all()
        
        for visita in visite:
            send_reminder_email(visita)
            
    except Exception as e:
        current_app.logger.error(f"Errore controllo visite 30 giorni: {str(e)}")

def check_visite_scadenza_7_giorni():
    """Controlla visite che scadono tra 7 giorni."""
    try:
        from datetime import date
        data_limite = date.today() + timedelta(days=7)
        
        visite = VisitaMedica.query.filter(
            VisitaMedica.scadenza == data_limite
        ).all()
        
        for visita in visite:
            send_reminder_email(visita)
            
    except Exception as e:
        current_app.logger.error(f"Errore controllo visite 7 giorni: {str(e)}")

def check_visite_scadenza_oggi():
    """Controlla visite che scadono oggi."""
    try:
        from datetime import date
        oggi = date.today()
        
        visite = VisitaMedica.query.filter(
            VisitaMedica.scadenza == oggi
        ).all()
        
        for visita in visite:
            send_reminder_email(visita)
            
    except Exception as e:
        current_app.logger.error(f"Errore controllo visite oggi: {str(e)}")

# Configura i job al caricamento del modulo
# setup_reminder_jobs()  # Commentato per evitare errori di context 