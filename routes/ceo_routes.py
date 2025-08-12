from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
import io
import csv
import json
from models import db, Feedback, User, Department, DiarioEntry, PrincipioPersonale, TaskAI, OrigineTask

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

# === API PRINCIPI PERSONALI ===
@ceo_bp.route("/api/principi/attivi", methods=['GET'])
@login_required
@ceo_required
def get_principi_attivi():
    """
    API per ottenere l'elenco dei principi attivi.
    
    Returns:
        JSON: Lista dei principi attivi
    """
    try:
        principi = PrincipioPersonale.query.filter_by(
            user_id=current_user.id,
            attiva=True
        ).order_by(PrincipioPersonale.priorita.desc()).all()
        
        principi_list = []
        for principio in principi:
            principi_list.append({
                'id': principio.id,
                'titolo': principio.titolo,
                'descrizione': principio.descrizione,
                'categoria': principio.categoria,
                'priorita': principio.priorita,
                'colore': principio.colore
            })
        
        return jsonify({
            'success': True,
            'principi': principi_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# === API DIARIO CEO ===
@ceo_bp.route("/api/diario/<int:diario_id>/genera_task", methods=['POST'])
@login_required
@ceo_required
def genera_task_da_diario(diario_id):
    """
    API per generare task AI da un'entrata del diario.
    
    Args:
        diario_id (int): ID dell'entrata del diario
        
    Returns:
        JSON: Risultato dell'analisi e task generati
    """
    try:
        # Trova l'entrata del diario
        diario_entry = DiarioEntry.query.filter_by(
            id=diario_id,
            user_id=current_user.id
        ).first()
        
        if not diario_entry:
            return jsonify({
                'success': False,
                'error': 'Entrata diario non trovata'
            }), 404
        
        # Ottieni i principi attivi
        principi_attivi = PrincipioPersonale.query.filter_by(
            user_id=current_user.id,
            attiva=True
        ).all()
        
        # Analizza il contenuto del diario con AI
        analisi_result = analizza_diario_con_ai(diario_entry, principi_attivi)
        
        # Salva l'analisi nel diario
        diario_entry.analisi_ai = json.dumps(analisi_result)
        
        # Genera task se necessario
        task_generati = []
        if analisi_result.get('task_suggeriti'):
            for task_sugg in analisi_result['task_suggeriti']:
                task_ai = TaskAI(
                    user_id=current_user.id,
                    titolo=task_sugg['titolo'],
                    descrizione=task_sugg['descrizione'],
                    priorita=task_sugg.get('priorita', PrioritaTask.MEDIUM),
                    origine=OrigineTask.DIARIO,
                    data_scadenza=task_sugg.get('data_scadenza')
                )
                db.session.add(task_ai)
                db.session.flush()  # Per ottenere l'ID
                task_generati.append(task_ai.id)
                
                # Collega il task al diario
                diario_entry.aggiungi_task_generato(task_ai.id)
        
        # Collega i principi rilevanti
        if analisi_result.get('principi_rilevanti'):
            for principio_id in analisi_result['principi_rilevanti']:
                diario_entry.aggiungi_principio_collegato(principio_id)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'analisi': analisi_result,
            'task_generati': task_generati
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ceo_bp.route("/api/task/crea_da_diario", methods=['POST'])
@login_required
@ceo_required
def crea_task_da_diario():
    """
    API per creare un task partendo dal suggerimento del diario.
    
    Returns:
        JSON: Task creato
    """
    try:
        data = request.get_json()
        
        if not data or 'titolo' not in data:
            return jsonify({
                'success': False,
                'error': 'Titolo obbligatorio'
            }), 400
        
        # Crea il task
        task_ai = TaskAI(
            user_id=current_user.id,
            titolo=data['titolo'],
            descrizione=data.get('descrizione', ''),
            priorita=data.get('priorita', PrioritaTask.MEDIUM),
            origine=OrigineTask.DIARIO,
            data_scadenza=datetime.fromisoformat(data['data_scadenza']) if data.get('data_scadenza') else None
        )
        
        db.session.add(task_ai)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'task': {
                'id': task_ai.id,
                'titolo': task_ai.titolo,
                'descrizione': task_ai.descrizione,
                'priorita': task_ai.priorita.value,
                'origine': task_ai.origine.value
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def analizza_diario_con_ai(diario_entry, principi_attivi):
    """
    Analizza il contenuto del diario con AI e confronta con i principi attivi.
    
    Args:
        diario_entry (DiarioEntry): Entrata del diario
        principi_attivi (list): Lista principi attivi
        
    Returns:
        dict: Risultato dell'analisi
    """
    # Contenuto da analizzare
    contenuto_analisi = f"""
    Titolo: {diario_entry.titolo}
    Contenuto: {diario_entry.contenuto}
    Umore: {diario_entry.umore}/10
    Energia: {diario_entry.energia}/10
    Gratitudine: {diario_entry.gratitudine}
    Sfide: {diario_entry.sfide}
    Obiettivi: {diario_entry.obiettivi}
    Riflessioni: {diario_entry.riflessioni}
    """
    
    # Principi attivi per confronto
    principi_testo = []
    for principio in principi_attivi:
        principi_testo.append(f"Principio {principio.id}: {principio.titolo} - {principio.descrizione}")
    
    # Simula analisi AI (in produzione usare un servizio AI reale)
    analisi_result = {
        'principi_rilevanti': [],
        'task_suggeriti': [],
        'insights': []
    }
    
    # Analisi semantica semplificata
    contenuto_lower = contenuto_analisi.lower()
    
    # Trova principi rilevanti
    for principio in principi_attivi:
        if any(keyword in contenuto_lower for keyword in principio.titolo.lower().split()):
            analisi_result['principi_rilevanti'].append(principio.id)
    
    # Genera task suggeriti basati sul contenuto
    if 'stress' in contenuto_lower or 'stanco' in contenuto_lower:
        analisi_result['task_suggeriti'].append({
            'titolo': 'Pianifica tempo di recupero',
            'descrizione': 'Organizza 30 minuti di tempo profondo per recuperare energia',
            'priorita': PrioritaTask.HIGH,
            'data_scadenza': (datetime.now() + timedelta(days=1)).isoformat()
        })
    
    if 'obiettivi' in contenuto_lower:
        analisi_result['task_suggeriti'].append({
            'titolo': 'Rivedi obiettivi settimanali',
            'descrizione': 'Dedica tempo a pianificare e prioritizzare gli obiettivi',
            'priorita': PrioritaTask.MEDIUM,
            'data_scadenza': (datetime.now() + timedelta(days=3)).isoformat()
        })
    
    if 'gratitudine' in contenuto_lower:
        analisi_result['insights'].append('Ottimo lavoro nel praticare gratitudine!')
    
    return analisi_result

# === ROUTE DIARIO CEO ===
@ceo_bp.route("/ceo/diario")
@login_required
@ceo_required
def diario_ceo():
    """
    Dashboard del diario CEO.
    
    Returns:
        Template: Dashboard diario CEO
    """
    # Ottieni le entrate del diario ordinate per data
    diario_entries = DiarioEntry.query.filter_by(
        user_id=current_user.id
    ).order_by(DiarioEntry.data.desc()).all()
    
    # Ottieni i principi attivi
    principi_attivi = PrincipioPersonale.query.filter_by(
        user_id=current_user.id,
        attiva=True
    ).order_by(PrincipioPersonale.priorita.desc()).all()
    
    return render_template('ceo/diario_ceo.html',
                         diario_entries=diario_entries,
                         principi_attivi=principi_attivi)

@ceo_bp.route("/ceo/diario/nuovo", methods=['GET', 'POST'])
@login_required
@ceo_required
def nuovo_diario_entry():
    """
    Crea una nuova entrata del diario.
    
    Returns:
        Template: Form nuova entrata o redirect
    """
    if request.method == 'POST':
        try:
            # Crea nuova entrata
            diario_entry = DiarioEntry(
                user_id=current_user.id,
                data=datetime.strptime(request.form['data'], '%Y-%m-%d').date(),
                titolo=request.form['titolo'],
                contenuto=request.form.get('contenuto', ''),
                umore=int(request.form.get('umore', 5)),
                energia=int(request.form.get('energia', 5)),
                gratitudine=request.form.get('gratitudine', ''),
                sfide=request.form.get('sfide', ''),
                obiettivi=request.form.get('obiettivi', ''),
                riflessioni=request.form.get('riflessioni', '')
            )
            
            db.session.add(diario_entry)
            db.session.commit()
            
            flash('✅ Entrata diario creata con successo!', 'success')
            return redirect(url_for('ceo.diario_ceo'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Errore durante la creazione: {str(e)}', 'danger')
    
    return render_template('ceo/nuovo_diario_entry.html', today=datetime.now().strftime('%Y-%m-%d'))

@ceo_bp.route("/ceo/diario/<int:entry_id>")
@login_required
@ceo_required
def visualizza_diario_entry(entry_id):
    """
    Visualizza un'entrata specifica del diario.
    
    Args:
        entry_id (int): ID dell'entrata
        
    Returns:
        Template: Dettagli entrata diario
    """
    diario_entry = DiarioEntry.query.filter_by(
        id=entry_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Ottieni i principi collegati
    principi_collegati = []
    if diario_entry.principi_collegati_list:
        principi_collegati = PrincipioPersonale.query.filter(
            PrincipioPersonale.id.in_(diario_entry.principi_collegati_list)
        ).all()
    
    # Ottieni i task generati
    task_generati = []
    if diario_entry.task_generati_list:
        task_generati = TaskAI.query.filter(
            TaskAI.id.in_(diario_entry.task_generati_list)
        ).all()
    
    return render_template('ceo/visualizza_diario_entry.html',
                         entry=diario_entry,
                         principi_collegati=principi_collegati,
                         task_generati=task_generati)

# === ROUTE PRINCIPI PERSONALI ===
@ceo_bp.route("/ceo/principi")
@login_required
@ceo_required
def principi_personali():
    """
    Dashboard dei principi personali.
    
    Returns:
        Template: Dashboard principi personali
    """
    principi = PrincipioPersonale.query.filter_by(
        user_id=current_user.id
    ).order_by(PrincipioPersonale.priorita.desc()).all()
    
    return render_template('ceo/principi_personali.html', principi=principi)

@ceo_bp.route("/ceo/principi/nuovo", methods=['GET', 'POST'])
@login_required
@ceo_required
def nuovo_principio():
    """
    Crea un nuovo principio personale.
    
    Returns:
        Template: Form nuovo principio o redirect
    """
    if request.method == 'POST':
        try:
            principio = PrincipioPersonale(
                user_id=current_user.id,
                titolo=request.form['titolo'],
                descrizione=request.form.get('descrizione', ''),
                categoria=request.form.get('categoria', ''),
                priorita=int(request.form.get('priorita', 5)),
                colore=request.form.get('colore', 'primary'),
                attiva=request.form.get('attiva', 'on') == 'on'
            )
            
            db.session.add(principio)
            db.session.commit()
            
            flash('✅ Principio personale creato con successo!', 'success')
            return redirect(url_for('ceo.principi_personali'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Errore durante la creazione: {str(e)}', 'danger')
    
    return render_template('ceo/nuovo_principio.html')

@ceo_bp.route("/ceo/principi/<int:principio_id>/edit", methods=['GET', 'POST'])
@login_required
@ceo_required
def edit_principio(principio_id):
    """
    Modifica un principio personale.
    
    Args:
        principio_id (int): ID del principio
        
    Returns:
        Template: Form modifica principio o redirect
    """
    principio = PrincipioPersonale.query.filter_by(
        id=principio_id,
        user_id=current_user.id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            principio.titolo = request.form['titolo']
            principio.descrizione = request.form.get('descrizione', '')
            principio.categoria = request.form.get('categoria', '')
            principio.priorita = int(request.form.get('priorita', 5))
            principio.colore = request.form.get('colore', 'primary')
            principio.attiva = request.form.get('attiva', 'on') == 'on'
            
            db.session.commit()
            
            flash('✅ Principio personale aggiornato con successo!', 'success')
            return redirect(url_for('ceo.principi_personali'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Errore durante l\'aggiornamento: {str(e)}', 'danger')
    
    return render_template('ceo/edit_principio.html', principio=principio)

# === ROUTE BRIGHTER OVERVIEW (MANTENUTA PER COMPATIBILITÀ) ===
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