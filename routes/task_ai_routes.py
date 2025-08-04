"""
Route CRUD per TaskAI - Prompt 26 FASE 2
Implementazione delle API per gestione task AI personali.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import TaskAI, OrigineTask, PrioritaTask
from extensions import db as database # Renamed to avoid conflict with sqlalchemy.db

task_ai_bp = Blueprint('task_ai', __name__, url_prefix='/api/tasks')

@task_ai_bp.route("/my", methods=['GET'])
@login_required
def get_my_tasks():
    """
    Restituisce tutti i task personali dell'utente loggato.
    
    Returns:
        json: Lista dei task con success status
    """
    try:
        # Recupera tutti i task dell'utente
        tasks = TaskAI.query.filter_by(user_id=current_user.id).order_by(TaskAI.data_creazione.desc()).all()
        
        # Serializza i task
        tasks_data = []
        for task in tasks:
            task_data = {
                'id': task.id,
                'titolo': task.titolo,
                'descrizione': task.descrizione,
                'data_scadenza': task.data_scadenza.isoformat() if task.data_scadenza else None,
                'priorita': task.priorita.value,
                'origine': task.origine.value,
                'stato': task.stato,
                'data_creazione': task.data_creazione.isoformat(),
                'is_completed': task.is_completed,
                'is_overdue': task.is_overdue,
                'days_until_deadline': task.days_until_deadline,
                'priority_color': task.priority_color,
                'status_color': task.status_color,
                'origine_badge_class': task.origine_badge_class,
                'origine_display': task.origine_display
            }
            tasks_data.append(task_data)
        
        return jsonify({
            'success': True,
            'data': tasks_data,
            'count': len(tasks_data)
        })
        
    except Exception as e:
        database.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore nel recupero dei task: {str(e)}'
        }), 500

@task_ai_bp.route("/", methods=['POST'])
@login_required
def create_task():
    """
    Crea un nuovo task per l'utente loggato.
    
    Returns:
        json: Task creato con success status
    """
    try:
        data = request.get_json()
        
        # Validazione dati
        if not data or 'titolo' not in data:
            return jsonify({
                'success': False,
                'error': 'Titolo obbligatorio'
            }), 400
        
        # Crea il nuovo task
        new_task = TaskAI(
            user_id=current_user.id,
            titolo=data['titolo'],
            descrizione=data.get('descrizione'),
            data_scadenza=datetime.fromisoformat(data['data_scadenza']) if data.get('data_scadenza') else None,
            priorita=PrioritaTask(data.get('priorita', 'Medium')),
            origine=OrigineTask(data.get('origine', 'Manuale'))
        )
        
        database.session.add(new_task)
        database.session.commit()
        
        # Serializza il task creato
        task_data = {
            'id': new_task.id,
            'titolo': new_task.titolo,
            'descrizione': new_task.descrizione,
            'data_scadenza': new_task.data_scadenza.isoformat() if new_task.data_scadenza else None,
            'priorita': new_task.priorita.value,
            'origine': new_task.origine.value,
            'stato': new_task.stato,
            'data_creazione': new_task.data_creazione.isoformat(),
            'is_completed': new_task.is_completed,
            'is_overdue': new_task.is_overdue,
            'days_until_deadline': new_task.days_until_deadline,
            'priority_color': new_task.priority_color,
            'status_color': new_task.status_color,
            'origine_badge_class': new_task.origine_badge_class,
            'origine_display': new_task.origine_display
        }
        
        return jsonify({
            'success': True,
            'data': task_data,
            'message': 'Task creato con successo'
        }), 201
        
    except Exception as e:
        database.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore nella creazione del task: {str(e)}'
        }), 500

@task_ai_bp.route("/<int:task_id>/complete", methods=['PATCH'])
@login_required
def complete_task(task_id):
    """
    Segna un task come completato.
    
    Args:
        task_id (int): ID del task da completare
        
    Returns:
        json: Task aggiornato con success status
    """
    try:
        # Trova il task dell'utente
        task = TaskAI.query.filter_by(id=task_id, user_id=current_user.id).first()
        
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task non trovato'
            }), 404
        
        # Marca come completato
        task.stato = True
        
        database.session.commit()
        
        # Serializza il task aggiornato
        task_data = {
            'id': task.id,
            'titolo': task.titolo,
            'descrizione': task.descrizione,
            'data_scadenza': task.data_scadenza.isoformat() if task.data_scadenza else None,
            'priorita': task.priorita.value,
            'origine': task.origine.value,
            'stato': task.stato,
            'data_creazione': task.data_creazione.isoformat(),
            'is_completed': task.is_completed,
            'is_overdue': task.is_overdue,
            'days_until_deadline': task.days_until_deadline,
            'priority_color': task.priority_color,
            'status_color': task.status_color,
            'origine_badge_class': task.origine_badge_class,
            'origine_display': task.origine_display
        }
        
        return jsonify({
            'success': True,
            'data': task_data,
            'message': 'Task completato con successo'
        })
        
    except Exception as e:
        database.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore nel completamento del task: {str(e)}'
        }), 500

@task_ai_bp.route("/<int:task_id>", methods=['DELETE'])
@login_required
def delete_task(task_id):
    """
    Elimina un task dell'utente.
    
    Args:
        task_id (int): ID del task da eliminare
        
    Returns:
        json: Conferma eliminazione con success status
    """
    try:
        # Trova il task dell'utente
        task = TaskAI.query.filter_by(id=task_id, user_id=current_user.id).first()
        
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task non trovato'
            }), 404
        
        # Elimina il task
        database.session.delete(task)
        database.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task eliminato con successo'
        })
        
    except Exception as e:
        database.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore nell\'eliminazione del task: {str(e)}'
        }), 500

@task_ai_bp.route("/<int:task_id>", methods=['PUT'])
@login_required
def update_task(task_id):
    """
    Aggiorna un task esistente.
    
    Args:
        task_id (int): ID del task da aggiornare
        
    Returns:
        json: Task aggiornato con success status
    """
    try:
        data = request.get_json()
        
        # Trova il task dell'utente
        task = TaskAI.query.filter_by(id=task_id, user_id=current_user.id).first()
        
        if not task:
            return jsonify({
                'success': False,
                'error': 'Task non trovato'
            }), 404
        
        # Aggiorna i campi
        if 'titolo' in data:
            task.titolo = data['titolo']
        if 'descrizione' in data:
            task.descrizione = data['descrizione']
        if 'data_scadenza' in data:
            task.data_scadenza = datetime.fromisoformat(data['data_scadenza']) if data['data_scadenza'] else None
        if 'priorita' in data:
            task.priorita = PrioritaTask(data['priorita'])
        if 'origine' in data:
            task.origine = OrigineTask(data['origine'])
        if 'stato' in data:
            task.stato = data['stato']
        
        database.session.commit()
        
        # Serializza il task aggiornato
        task_data = {
            'id': task.id,
            'titolo': task.titolo,
            'descrizione': task.descrizione,
            'data_scadenza': task.data_scadenza.isoformat() if task.data_scadenza else None,
            'priorita': task.priorita.value,
            'origine': task.origine.value,
            'stato': task.stato,
            'data_creazione': task.data_creazione.isoformat(),
            'is_completed': task.is_completed,
            'is_overdue': task.is_overdue,
            'days_until_deadline': task.days_until_deadline,
            'priority_color': task.priority_color,
            'status_color': task.status_color,
            'origine_badge_class': task.origine_badge_class,
            'origine_display': task.origine_display
        }
        
        return jsonify({
            'success': True,
            'data': task_data,
            'message': 'Task aggiornato con successo'
        })
        
    except Exception as e:
        database.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore nell\'aggiornamento del task: {str(e)}'
        }), 500

@task_ai_bp.route("/my/stats", methods=['GET'])
@login_required
def get_my_task_stats():
    """
    Restituisce statistiche sui task personali dell'utente.
    
    Returns:
        json: Statistiche dettagliate con success status
    """
    try:
        # Recupera tutti i task dell'utente
        tasks = TaskAI.query.filter_by(user_id=current_user.id).all()
        
        # Calcola statistiche
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.stato])
        pending_tasks = total_tasks - completed_tasks
        overdue_tasks = len([t for t in tasks if t.is_overdue])
        
        # Distribuzione per priorità
        priority_stats = {}
        for task in tasks:
            priority = task.priorita.value
            if priority not in priority_stats:
                priority_stats[priority] = {'total': 0, 'completed': 0}
            priority_stats[priority]['total'] += 1
            if task.stato:
                priority_stats[priority]['completed'] += 1
        
        # Distribuzione per origine
        origin_stats = {}
        for task in tasks:
            origin = task.origine.value
            if origin not in origin_stats:
                origin_stats[origin] = {'total': 0, 'completed': 0}
            origin_stats[origin]['total'] += 1
            if task.stato:
                origin_stats[origin]['completed'] += 1
        
        # Task in scadenza (prossimi 3 giorni)
        upcoming_deadlines = []
        for task in tasks:
            if task.data_scadenza and not task.stato:
                days_until = task.days_until_deadline
                if days_until is not None and 0 <= days_until <= 3:
                    upcoming_deadlines.append({
                        'id': task.id,
                        'titolo': task.titolo,
                        'days_until': days_until,
                        'priorita': task.priorita.value
                    })
        
        # Ordina per scadenza
        upcoming_deadlines.sort(key=lambda x: x['days_until'])
        
        stats = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'overdue_tasks': overdue_tasks,
            'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            'priority_stats': priority_stats,
            'origin_stats': origin_stats,
            'upcoming_deadlines': upcoming_deadlines[:5]  # Top 5
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        database.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore nel calcolo delle statistiche: {str(e)}'
        }), 500

@task_ai_bp.route("/my/filter", methods=['POST'])
@login_required
def filter_my_tasks():
    """
    Filtra i task personali dell'utente con criteri avanzati.
    
    Returns:
        json: Task filtrati con success status
    """
    try:
        data = request.get_json() or {}
        
        # Query base
        query = TaskAI.query.filter_by(user_id=current_user.id)
        
        # Applica filtri
        if 'stato' in data:
            query = query.filter(TaskAI.stato == data['stato'])
        
        if 'priorita' in data:
            query = query.filter(TaskAI.priorita == PrioritaTask(data['priorita']))
        
        if 'origine' in data:
            query = query.filter(TaskAI.origine == OrigineTask(data['origine']))
        
        if 'search' in data and data['search']:
            search_term = f"%{data['search']}%"
            query = query.filter(
                (TaskAI.titolo.ilike(search_term)) |
                (TaskAI.descrizione.ilike(search_term))
            )
        
        # Ordinamento
        sort_by = data.get('sort_by', 'data_creazione')
        sort_order = data.get('sort_order', 'desc')
        
        if sort_by == 'data_creazione':
            if sort_order == 'desc':
                query = query.order_by(TaskAI.data_creazione.desc())
            else:
                query = query.order_by(TaskAI.data_creazione.asc())
        elif sort_by == 'data_scadenza':
            if sort_order == 'desc':
                query = query.order_by(TaskAI.data_scadenza.desc())
            else:
                query = query.order_by(TaskAI.data_scadenza.asc())
        elif sort_by == 'priorita':
            if sort_order == 'desc':
                query = query.order_by(TaskAI.priorita.desc())
            else:
                query = query.order_by(TaskAI.priorita.asc())
        
        # Esegui query
        tasks = query.all()
        
        # Serializza i task
        tasks_data = []
        for task in tasks:
            task_data = {
                'id': task.id,
                'titolo': task.titolo,
                'descrizione': task.descrizione,
                'data_scadenza': task.data_scadenza.isoformat() if task.data_scadenza else None,
                'priorita': task.priorita.value,
                'origine': task.origine.value,
                'stato': task.stato,
                'data_creazione': task.data_creazione.isoformat(),
                'is_completed': task.is_completed,
                'is_overdue': task.is_overdue,
                'days_until_deadline': task.days_until_deadline,
                'priority_color': task.priority_color,
                'status_color': task.status_color,
                'origine_badge_class': task.origine_badge_class,
                'origine_display': task.origine_display
            }
            tasks_data.append(task_data)
        
        return jsonify({
            'success': True,
            'data': tasks_data,
            'count': len(tasks_data),
            'filters_applied': data
        })
        
    except Exception as e:
        database.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore nel filtraggio dei task: {str(e)}'
        }), 500

@task_ai_bp.route("/ai/notifications/me", methods=['GET'])
@login_required
def get_ai_notifications():
    """
    Restituisce notifiche AI personalizzate per l'utente loggato.
    
    Returns:
        json: Lista di notifiche AI con success status
    """
    try:
        # Recupera i task dell'utente per analisi
        tasks = TaskAI.query.filter_by(user_id=current_user.id).all()
        
        # Analizza i task per generare notifiche intelligenti
        notifications = []
        
        # 1. Task scaduti
        overdue_tasks = [t for t in tasks if t.is_overdue]
        if overdue_tasks:
            overdue_count = len(overdue_tasks)
            notifications.append({
                'id': f'overdue_{overdue_count}',
                'title': '⚠️ Task Scaduti',
                'message': f'Hai {overdue_count} task scaduto{"i" if overdue_count > 1 else ""}. Completa al più presto per mantenere la produttività.',
                'priority': 'high',
                'type': 'warning',
                'timestamp': datetime.utcnow().isoformat(),
                'action_url': '/user/my_tasks_ai'
            })
        
        # 2. Task in scadenza (prossimi 3 giorni)
        upcoming_tasks = [t for t in tasks if t.days_until_deadline is not None and 0 <= t.days_until_deadline <= 3 and not t.stato]
        if upcoming_tasks:
            urgent_tasks = [t for t in upcoming_tasks if t.days_until_deadline <= 1]
            if urgent_tasks:
                notifications.append({
                    'id': f'urgent_{len(urgent_tasks)}',
                    'title': '🚨 Scadenze Urgenti',
                    'message': f'Hai {len(urgent_tasks)} task che scade{"no" if len(urgent_tasks) > 1 else ""} entro domani. Priorità massima!',
                    'priority': 'high',
                    'type': 'urgent',
                    'timestamp': datetime.utcnow().isoformat(),
                    'action_url': '/user/my_tasks_ai'
                })
            else:
                notifications.append({
                    'id': f'upcoming_{len(upcoming_tasks)}',
                    'title': '📅 Scadenze Imminenti',
                    'message': f'Hai {len(upcoming_tasks)} task che scade{"no" if len(upcoming_tasks) > 1 else ""} nei prossimi giorni.',
                    'priority': 'medium',
                    'type': 'info',
                    'timestamp': datetime.utcnow().isoformat(),
                    'action_url': '/user/my_tasks_ai'
                })
        
        # 3. Suggerimenti AI basati sui pattern
        completed_tasks = [t for t in tasks if t.stato]
        if completed_tasks:
            completion_rate = len(completed_tasks) / len(tasks) * 100 if tasks else 0
            
            if completion_rate >= 80:
                notifications.append({
                    'id': 'excellent_progress',
                    'title': '🎉 Eccellente Progresso',
                    'message': f'Hai completato l\'{completion_rate:.0f}% dei tuoi task! Continua così per raggiungere i tuoi obiettivi.',
                    'priority': 'low',
                    'type': 'success',
                    'timestamp': datetime.utcnow().isoformat(),
                    'action_url': '/user/my_tasks_ai'
                })
            elif completion_rate >= 60:
                notifications.append({
                    'id': 'good_progress',
                    'title': '👍 Buon Progresso',
                    'message': f'Hai completato il {completion_rate:.0f}% dei tuoi task. Mantieni questo ritmo!',
                    'priority': 'medium',
                    'type': 'info',
                    'timestamp': datetime.utcnow().isoformat(),
                    'action_url': '/user/my_tasks_ai'
                })
            else:
                notifications.append({
                    'id': 'need_improvement',
                    'title': '💡 Suggerimento AI',
                    'message': f'Hai completato solo il {completion_rate:.0f}% dei task. Considera di rivedere le priorità o chiedere aiuto.',
                    'priority': 'medium',
                    'type': 'suggestion',
                    'timestamp': datetime.utcnow().isoformat(),
                    'action_url': '/user/my_tasks_ai'
                })
        
        # 4. Suggerimenti per task vuoti
        if not tasks:
            notifications.append({
                'id': 'no_tasks',
                'title': '🤖 Suggerimento AI',
                'message': 'Non hai ancora creato nessun task. Inizia ora per organizzare meglio il tuo lavoro!',
                'priority': 'medium',
                'type': 'suggestion',
                'timestamp': datetime.utcnow().isoformat(),
                'action_url': '/user/my_tasks_ai'
            })
        
        # 5. Analisi pattern di produttività
        if len(tasks) >= 5:
            high_priority_tasks = [t for t in tasks if t.priorita == PrioritaTask.HIGH and not t.stato]
            if high_priority_tasks:
                notifications.append({
                    'id': 'high_priority_reminder',
                    'title': '🎯 Task Alta Priorità',
                    'message': f'Hai {len(high_priority_tasks)} task ad alta priorità in attesa. Concentrati su questi per massimizzare l\'impatto.',
                    'priority': 'high',
                    'type': 'reminder',
                    'timestamp': datetime.utcnow().isoformat(),
                    'action_url': '/user/my_tasks_ai'
                })
        
        # Ordina per priorità e timestamp (più recenti prima)
        notifications.sort(key=lambda x: (
            {'high': 0, 'medium': 1, 'low': 2}[x['priority']],
            -datetime.fromisoformat(x['timestamp']).timestamp()
        ))
        
        # Limita a 5 notifiche
        notifications = notifications[:5]
        
        return jsonify({
            'success': True,
            'data': notifications,
            'count': len(notifications)
        })
        
    except Exception as e:
        database.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore nel recupero delle notifiche AI: {str(e)}'
        }), 500

@task_ai_bp.route("/ai/suggestions", methods=['GET'])
@login_required
def get_ai_suggestions():
    """
    Restituisce suggerimenti AI intelligenti per l'utente loggato.
    
    Returns:
        json: Lista di suggerimenti AI con success status
    """
    try:
        # Recupera i task dell'utente per analisi
        tasks = TaskAI.query.filter_by(user_id=current_user.id).all()
        
        # Analizza i task per generare suggerimenti intelligenti
        suggestions = []
        
        # 1. Task critici in scadenza oggi
        today = datetime.utcnow().date()
        critical_tasks = [t for t in tasks if t.data_scadenza and t.data_scadenza.date() == today and not t.stato]
        if critical_tasks:
            suggestions.append({
                'id': f'critical_today_{len(critical_tasks)}',
                'type': 'critico',
                'message': f'📅 Hai {len(critical_tasks)} task in scadenza oggi. Completa almeno 1 entro le 14.',
                'priority': 'high',
                'action_url': '/user/my_tasks_ai',
                'icon': 'fas fa-exclamation-triangle',
                'color': 'danger'
            })
        
        # 2. Task vecchi non aggiornati (> 7 giorni)
        week_ago = datetime.utcnow() - timedelta(days=7)
        old_tasks = [t for t in tasks if t.data_creazione < week_ago and not t.stato]
        if old_tasks:
            suggestions.append({
                'id': f'old_tasks_{len(old_tasks)}',
                'type': 'operativo',
                'message': f'📅 Hai {len(old_tasks)} task creati più di 7 giorni fa. Rivedi se sono ancora rilevanti.',
                'priority': 'medium',
                'action_url': '/user/my_tasks_ai',
                'icon': 'fas fa-clock',
                'color': 'warning'
            })
        
        # 3. Mancanza di task completati di recente
        recent_completed = [t for t in tasks if t.stato and t.data_creazione > datetime.utcnow() - timedelta(days=3)]
        if len(recent_completed) == 0 and len(tasks) > 0:
            suggestions.append({
                'id': 'no_recent_completion',
                'type': 'motivazionale',
                'message': '🧠 Nessun task completato da 3 giorni. Una sessione Deep Work può aiutarti.',
                'priority': 'medium',
                'action_url': '/user/deep-work',
                'icon': 'fas fa-brain',
                'color': 'info'
            })
        
        # 4. Eccesso di task aperti senza priorità
        unprioritized_tasks = [t for t in tasks if t.priorita == PrioritaTask.LOW and not t.stato]
        if len(unprioritized_tasks) >= 5:
            suggestions.append({
                'id': f'unprioritized_{len(unprioritized_tasks)}',
                'type': 'operativo',
                'message': f'🗂 Hai {len(unprioritized_tasks)} task aperti senza priorità: rivedi la pianificazione settimanale.',
                'priority': 'medium',
                'action_url': '/user/my_tasks_ai',
                'icon': 'fas fa-list',
                'color': 'warning'
            })
        
        # 5. Task scaduti da completare
        overdue_tasks = [t for t in tasks if t.is_overdue]
        if overdue_tasks:
            suggestions.append({
                'id': f'overdue_suggestion_{len(overdue_tasks)}',
                'type': 'critico',
                'message': f'🚨 Hai {len(overdue_tasks)} task scaduti. Completa al più presto per evitare accumuli.',
                'priority': 'high',
                'action_url': '/user/my_tasks_ai',
                'icon': 'fas fa-fire',
                'color': 'danger'
            })
        
        # 6. Suggerimento per task vuoti
        if not tasks:
            suggestions.append({
                'id': 'empty_tasks',
                'type': 'motivazionale',
                'message': '🤖 Inizia a creare i tuoi primi task per organizzare meglio il lavoro!',
                'priority': 'low',
                'action_url': '/user/my_tasks_ai',
                'icon': 'fas fa-plus',
                'color': 'primary'
            })
        
        # 7. Suggerimento per produttività
        if len(tasks) >= 3:
            completion_rate = len([t for t in tasks if t.stato]) / len(tasks) * 100
            if completion_rate < 50:
                suggestions.append({
                    'id': 'productivity_tip',
                    'type': 'motivazionale',
                    'message': f'📈 Hai completato solo il {completion_rate:.0f}% dei task. Concentrati su 1-2 task al giorno.',
                    'priority': 'medium',
                    'action_url': '/user/my_tasks_ai',
                    'icon': 'fas fa-chart-line',
                    'color': 'info'
                })
        
        # 8. Suggerimento per task alta priorità
        high_priority_pending = [t for t in tasks if t.priorita == PrioritaTask.HIGH and not t.stato]
        if high_priority_pending:
            suggestions.append({
                'id': f'high_priority_suggestion_{len(high_priority_pending)}',
                'type': 'operativo',
                'message': f'🎯 Hai {len(high_priority_pending)} task ad alta priorità. Inizia da quello più urgente.',
                'priority': 'high',
                'action_url': '/user/my_tasks_ai',
                'icon': 'fas fa-star',
                'color': 'warning'
            })
        
        # Ordina per priorità e tipo
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        type_order = {'critico': 0, 'operativo': 1, 'motivazionale': 2}
        
        suggestions.sort(key=lambda x: (
            priority_order[x['priority']],
            type_order[x['type']]
        ))
        
        # Limita a 5 suggerimenti
        suggestions = suggestions[:5]
        
        return jsonify({
            'success': True,
            'data': suggestions,
            'count': len(suggestions)
        })
        
    except Exception as e:
        database.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Errore nel recupero dei suggerimenti AI: {str(e)}'
        }), 500 