from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
import io
import csv
from models import db, Feedback, User, Department

# Blueprint CEO
ceo_bp = Blueprint('ceo', __name__)

def ceo_required(f):
    """
    Decorator per verificare che l'utente sia CEO.
    
    Args:
        f: Funzione da decorare
        
    Returns:
        Funzione decorata con controllo ruolo CEO
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'ceo':
            flash('❌ Accesso negato. Solo il CEO può accedere a questa sezione.', 'error')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@ceo_bp.route("/ceo/brighter-overview")
@login_required
@ceo_required
def brighter_overview():
    """
    Dashboard CEO per visualizzare talenti emergenti, segnalazioni critiche e alert strategici.
    
    Returns:
        Template: Dashboard CEO con feedback e statistiche
    """
    # Parametri di filtro
    search = request.args.get('search', '')
    tipo = request.args.get('tipo', '')
    stato = request.args.get('stato', '')
    periodo = request.args.get('periodo', '')
    page = request.args.get('page', 1, type=int)
    
    # Query base
    query = Feedback.query
    
    # Applica filtri
    if search:
        query = query.filter(
            db.or_(
                Feedback.testo.ilike(f'%{search}%'),
                Feedback.dipendente_id.ilike(f'%{search}%'),
                Feedback.autore_id.ilike(f'%{search}%')
            )
        )
    
    if tipo:
        query = query.filter(Feedback.tipo == tipo)
    
    if stato:
        query = query.filter(Feedback.stato == stato)
    
    # Filtro periodo
    if periodo == 'oggi':
        query = query.filter(Feedback.data_creazione >= datetime.now().date())
    elif periodo == 'settimana':
        query = query.filter(Feedback.data_creazione >= datetime.now() - timedelta(days=7))
    elif periodo == 'mese':
        query = query.filter(Feedback.data_creazione >= datetime.now() - timedelta(days=30))
    
    # Ordina per data creazione (più recenti prima)
    query = query.order_by(Feedback.data_creazione.desc())
    
    # Paginazione
    per_page = 20
    feedback_paginated = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Calcola statistiche
    stats = calculate_ceo_stats()
    
    # Genera alert AI
    alert_talenti = generate_talent_alert()
    alert_criticita = generate_critical_alert()
    alert_idee = generate_idea_alert()
    
    return render_template('ceo/brighter_overview.html',
                         feedback_ceo=feedback_paginated,
                         stats=stats,
                         alert_talenti=alert_talenti,
                         alert_criticita=alert_criticita,
                         alert_idee=alert_idee)

def calculate_ceo_stats():
    """
    Calcola statistiche per la dashboard CEO.
    
    Returns:
        dict: Statistiche aggregate
    """
    # Conteggi per tipo
    talenti_emergenti = Feedback.query.filter(
        Feedback.tipo == 'talento',
        Feedback.stato == 'in_attesa'
    ).count()
    
    segnalazioni_critiche = Feedback.query.filter(
        Feedback.tipo == 'criticità',
        Feedback.stato == 'in_attesa'
    ).count()
    
    idee_innovative = Feedback.query.filter(
        Feedback.tipo == 'idea',
        Feedback.stato == 'in_attesa'
    ).count()
    
    in_attesa = Feedback.query.filter(
        Feedback.stato == 'in_attesa'
    ).count()
    
    return {
        'talenti_emergenti': talenti_emergenti,
        'segnalazioni_critiche': segnalazioni_critiche,
        'idee_innovative': idee_innovative,
        'in_attesa': in_attesa
    }

def generate_talent_alert():
    """
    Genera alert AI per talenti emergenti.
    
    Returns:
        str: Messaggio alert o None
    """
    count_talenti = Feedback.query.filter(
        Feedback.tipo == 'talento',
        Feedback.stato == 'in_attesa',
        Feedback.data_creazione >= datetime.now() - timedelta(days=7)
    ).count()
    
    if count_talenti >= 3:
        return f"🌟 {count_talenti} talenti emergenti rilevati questa settimana. Considera un follow-up strategico."
    elif count_talenti > 0:
        return f"💡 {count_talenti} nuovo talento identificato. Valuta opportunità di sviluppo."
    
    return None

def generate_critical_alert():
    """
    Genera alert AI per segnalazioni critiche.
    
    Returns:
        str: Messaggio alert o None
    """
    count_criticita = Feedback.query.filter(
        Feedback.tipo == 'criticità',
        Feedback.stato == 'in_attesa'
    ).count()
    
    if count_criticita >= 5:
        return f"🚨 ATTENZIONE: {count_criticita} segnalazioni critiche in attesa. Richiede intervento immediato."
    elif count_criticita > 0:
        return f"⚠️ {count_criticita} segnalazione critica da valutare. Priorità alta."
    
    return None

def generate_idea_alert():
    """
    Genera alert AI per idee innovative.
    
    Returns:
        str: Messaggio alert o None
    """
    count_idee = Feedback.query.filter(
        Feedback.tipo == 'idea',
        Feedback.stato == 'in_attesa',
        Feedback.data_creazione >= datetime.now() - timedelta(days=30)
    ).count()
    
    if count_idee >= 10:
        return f"💡 OPPORTUNITÀ: {count_idee} idee innovative raccolte questo mese. Considera un innovation workshop."
    elif count_idee >= 5:
        return f"✨ {count_idee} nuove idee da valutare. Potenziale di innovazione."
    
    return None

@ceo_bp.route("/ceo/export-feedback")
@login_required
@ceo_required
def export_feedback():
    """
    Export feedback CEO in vari formati.
    
    Returns:
        File: CSV, PDF o Excel con dati feedback
    """
    format_type = request.args.get('format', 'csv')
    
    # Applica stessi filtri della dashboard
    search = request.args.get('search', '')
    tipo = request.args.get('tipo', '')
    stato = request.args.get('stato', '')
    periodo = request.args.get('periodo', '')
    
    query = Feedback.query
    
    if search:
        query = query.filter(
            db.or_(
                Feedback.testo.ilike(f'%{search}%'),
                Feedback.dipendente_id.ilike(f'%{search}%'),
                Feedback.autore_id.ilike(f'%{search}%')
            )
        )
    
    if tipo:
        query = query.filter(Feedback.tipo == tipo)
    
    if stato:
        query = query.filter(Feedback.stato == stato)
    
    if periodo == 'oggi':
        query = query.filter(Feedback.data_creazione >= datetime.now().date())
    elif periodo == 'settimana':
        query = query.filter(Feedback.data_creazione >= datetime.now() - timedelta(days=7))
    elif periodo == 'mese':
        query = query.filter(Feedback.data_creazione >= datetime.now() - timedelta(days=30))
    
    feedback_list = query.order_by(Feedback.data_creazione.desc()).all()
    
    if format_type == 'csv':
        return export_csv(feedback_list)
    elif format_type == 'pdf':
        return export_pdf(feedback_list)
    elif format_type == 'excel':
        return export_excel(feedback_list)
    else:
        return jsonify({'error': 'Formato non supportato'}), 400

def export_csv(feedback_list):
    """
    Export feedback in formato CSV.
    
    Args:
        feedback_list: Lista di feedback da esportare
        
    Returns:
        Response: File CSV
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'ID', 'Dipendente', 'Tipo', 'Testo', 'Autore', 
        'Data Creazione', 'Stato', 'Note'
    ])
    
    # Dati
    for feedback in feedback_list:
        writer.writerow([
            feedback.id,
            feedback.dipendente_id,
            feedback.tipo,
            feedback.testo,
            feedback.autore_id,
            feedback.data_creazione.strftime('%d/%m/%Y %H:%M'),
            feedback.stato,
            feedback.note or ''
        ])
    
    output.seek(0)
    
    from flask import make_response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=feedback_ceo_{datetime.now().strftime("%Y%m%d")}.csv'
    
    return response

def export_pdf(feedback_list):
    """
    Export feedback in formato PDF.
    
    Args:
        feedback_list: Lista di feedback da esportare
        
    Returns:
        Response: File PDF
    """
    # Usa la funzione esistente per generare PDF
    from utils.pdf_ai_badge import genera_pdf_from_html
    
    # Genera HTML per il PDF
    html_content = generate_pdf_html(feedback_list)
    
    # Genera PDF
    pdf_content = genera_pdf_from_html(html_content)
    
    from flask import make_response
    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=feedback_ceo_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response

def export_excel(feedback_list):
    """
    Export feedback in formato Excel.
    
    Args:
        feedback_list: Lista di feedback da esportare
        
    Returns:
        Response: File Excel
    """
    # Per ora restituisce CSV (Excel-compatible)
    return export_csv(feedback_list)

def generate_pdf_html(feedback_list):
    """
    Genera HTML per il PDF di export.
    
    Args:
        feedback_list: Lista di feedback
        
    Returns:
        str: HTML formattato per PDF
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Feedback CEO - {datetime.now().strftime('%d/%m/%Y')}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #2c3e50; text-align: center; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f8f9fa; font-weight: bold; }}
            .badge {{ padding: 4px 8px; border-radius: 4px; color: white; font-size: 12px; }}
            .talento {{ background-color: #28a745; }}
            .criticita {{ background-color: #dc3545; }}
            .idea {{ background-color: #007bff; }}
        </style>
    </head>
    <body>
        <h1>🌟 Feedback CEO - Brighter Overview</h1>
        <p><strong>Data Export:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        <p><strong>Totale Record:</strong> {len(feedback_list)}</p>
        
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Dipendente</th>
                    <th>Tipo</th>
                    <th>Testo</th>
                    <th>Autore</th>
                    <th>Data</th>
                    <th>Stato</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for feedback in feedback_list:
        tipo_class = feedback.tipo.replace('à', 'a').replace(' ', '')
        html += f"""
                <tr>
                    <td>{feedback.id}</td>
                    <td>{feedback.dipendente_id}</td>
                    <td><span class="badge {tipo_class}">{feedback.tipo}</span></td>
                    <td>{feedback.testo[:100]}{'...' if len(feedback.testo) > 100 else ''}</td>
                    <td>{feedback.autore_id}</td>
                    <td>{feedback.data_creazione.strftime('%d/%m/%Y')}</td>
                    <td>{feedback.stato}</td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    return html

@ceo_bp.route("/ceo/feedback/<int:feedback_id>/valuta", methods=['POST'])
@login_required
@ceo_required
def valuta_feedback(feedback_id):
    """
    Valuta un feedback (segna come valutato).
    
    Args:
        feedback_id: ID del feedback da valutare
        
    Returns:
        JSON: Risultato operazione
    """
    feedback = Feedback.query.get_or_404(feedback_id)
    
    try:
        feedback.stato = 'valutato'
        feedback.data_valutazione = datetime.now()
        feedback.valutato_da = current_user.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Feedback valutato con successo'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'❌ Errore durante la valutazione: {str(e)}'
        }), 500

@ceo_bp.route("/ceo/feedback/<int:feedback_id>/commenta", methods=['POST'])
@login_required
@ceo_required
def commenta_feedback(feedback_id):
    """
    Aggiunge un commento CEO a un feedback.
    
    Args:
        feedback_id: ID del feedback
        
    Returns:
        JSON: Risultato operazione
    """
    feedback = Feedback.query.get_or_404(feedback_id)
    commento = request.json.get('commento', '')
    
    if not commento:
        return jsonify({
            'success': False,
            'message': '❌ Commento richiesto'
        }), 400
    
    try:
        feedback.commento_ceo = commento
        feedback.data_commento_ceo = datetime.now()
        feedback.commentato_da_ceo = current_user.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '✅ Commento CEO aggiunto con successo'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'❌ Errore durante l\'aggiunta del commento: {str(e)}'
        }), 500 