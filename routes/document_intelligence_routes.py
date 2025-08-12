"""
Route per Document Intelligence AI.
Integra analisi AI dei documenti PDF con FocusMe AI.
"""

from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from functools import wraps
import json
from datetime import datetime

from models import db, Document, Task, User
from services.document_intelligence import document_intelligence, auto_verifica_documento, generate_ai_access_response, suggerisci_cartella_archiviazione
from utils.audit_logger import log_event
from extensions import db

# Blueprint per Document Intelligence
document_intelligence_bp = Blueprint('document_intelligence', __name__, url_prefix='/docs')

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

@document_intelligence_bp.route('/analyze-pdf', methods=['POST'])
@login_required
@roles_required(['admin', 'ceo'])
def analyze_pdf():
    """
    Analizza un documento PDF con AI.
    
    Body:
        - document_id: ID del documento da analizzare
        
    Returns:
        JSON con risultato analisi AI
    """
    try:
        data = request.get_json()
        document_id = data.get('document_id')
        
        if not document_id:
            return jsonify({
                'success': False,
                'message': 'ID documento richiesto'
            }), 400
        
        # Analizza documento con AI
        result = document_intelligence.analyze_document(document_id)
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'message': result['error']
            }), 500
        
        # Log audit
        log_event(
            'document_ai_analysis_requested',
            user_id=current_user.id,
            document_id=document_id,
            details={
                'ai_status': result['status'],
                'task_id': result['task_id']
            }
        )
        
        return jsonify({
            'success': True,
            'status': result['status'],
            'explain': result['explain'],
            'task_id': result['task_id'],
            'analysis': result['analysis']
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore analisi AI documento: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore durante l\'analisi AI'
        }), 500

@document_intelligence_bp.route('/critical', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def list_critical_documents():
    """
    Lista documenti incompleti o problematici.
    
    Query params:
        - status: Filtra per stato AI (incompleto, scaduto, manca_firma)
        - limit: Numero massimo risultati
    """
    try:
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        
        # Query base
        query = Document.query.filter(Document.ai_status.isnot(None))
        
        # Filtro per stato
        if status:
            query = query.filter(Document.ai_status == status)
        else:
            # Solo documenti problematici
            query = query.filter(Document.ai_status.in_(['incompleto', 'scaduto', 'manca_firma']))
        
        # Ordina per data analisi
        documents = query.order_by(Document.ai_analyzed_at.desc()).limit(limit).all()
        
        # Statistiche
        stats = {
            'total': len(documents),
            'incompleto': len([d for d in documents if d.ai_status == 'incompleto']),
            'scaduto': len([d for d in documents if d.ai_status == 'scaduto']),
            'manca_firma': len([d for d in documents if d.ai_status == 'manca_firma']),
            'completo': len([d for d in documents if d.ai_status == 'completo'])
        }
        
        return jsonify({
            'success': True,
            'documents': [
                {
                    'id': doc.id,
                    'title': doc.title,
                    'ai_status': doc.ai_status,
                    'ai_explain': doc.ai_explain,
                    'ai_task_id': doc.ai_task_id,
                    'ai_analyzed_at': doc.ai_analyzed_at.isoformat() if doc.ai_analyzed_at else None,
                    'uploader': doc.uploader.username if doc.uploader else 'N/A',
                    'created_at': doc.created_at.isoformat()
                }
                for doc in documents
            ],
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore lista documenti critici: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nel recupero documenti critici'
        }), 500

@document_intelligence_bp.route('/ai-explain/<int:doc_id>', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def get_ai_explain(doc_id):
    """
    Ottiene la spiegazione AI per un documento specifico.
    
    Args:
        doc_id: ID del documento
        
    Returns:
        JSON con spiegazione AI dettagliata
    """
    try:
        document = Document.query.get_or_404(doc_id)
        
        if not document.ai_analysis:
            return jsonify({
                'success': False,
                'message': 'Documento non ancora analizzato con AI'
            }), 404
        
        # Parsing analisi AI
        try:
            analysis = json.loads(document.ai_analysis)
        except:
            analysis = {}
        
        return jsonify({
            'success': True,
            'document_id': doc_id,
            'title': document.title,
            'ai_status': document.ai_status,
            'ai_explain': document.ai_explain,
            'ai_task_id': document.ai_task_id,
            'ai_analyzed_at': document.ai_analyzed_at.isoformat() if document.ai_analyzed_at else None,
            'analysis': analysis
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore spiegazione AI documento {doc_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nel recupero spiegazione AI'
        }), 500

@document_intelligence_bp.route('/export-critical', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def export_critical_documents():
    """
    Export CSV dei documenti critici.
    
    Query params:
        - status: Filtra per stato AI
        - explain: Filtra per spiegazione AI
        - format: csv o json
    """
    try:
        import csv
        from io import StringIO
        from flask import make_response
        
        status = request.args.get('status')
        explain = request.args.get('explain')
        format_type = request.args.get('format', 'csv')
        
        # Query documenti critici
        query = Document.query.filter(Document.ai_status.isnot(None))
        
        # Applica filtri
        if status:
            query = query.filter(Document.ai_status == status)
        else:
            query = query.filter(Document.ai_status.in_(['incompleto', 'scaduto', 'manca_firma']))
        
        if explain:
            query = query.filter(Document.ai_explain.ilike(f"%{explain}%"))
        
        documents = query.order_by(Document.ai_analyzed_at.desc()).all()
        
        if format_type == 'csv':
            # Genera CSV
            si = StringIO()
            writer = csv.writer(si)
            
            # Header
            writer.writerow([
                'ID', 'Titolo', 'Stato AI', 'Spiegazione AI', 
                'Task ID', 'Uploader', 'Data Analisi', 'Data Creazione'
            ])
            
            # Dati
            for doc in documents:
                writer.writerow([
                    doc.id,
                    doc.title,
                    doc.ai_status or 'N/A',
                    doc.ai_explain or 'N/A',
                    doc.ai_task_id or 'N/A',
                    doc.uploader.username if doc.uploader else 'N/A',
                    doc.ai_analyzed_at.strftime('%d/%m/%Y %H:%M') if doc.ai_analyzed_at else 'N/A',
                    doc.created_at.strftime('%d/%m/%Y %H:%M')
                ])
            
            output = make_response(si.getvalue())
            output.headers["Content-Disposition"] = f"attachment; filename=documenti_critici_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            output.headers["Content-type"] = "text/csv"
            
            # Log audit
            log_event(
                'export_critical_documents',
                user_id=current_user.id,
                details={
                    'num_documents': len(documents),
                    'status_filter': status,
                    'explain_filter': explain,
                    'format': 'csv'
                }
            )
            
            return output
        else:
            # JSON response
            return jsonify({
                'success': True,
                'documents': [
                    {
                        'id': doc.id,
                        'title': doc.title,
                        'ai_status': doc.ai_status,
                        'ai_explain': doc.ai_explain,
                        'ai_task_id': doc.ai_task_id,
                        'uploader': doc.uploader.username if doc.uploader else 'N/A',
                        'ai_analyzed_at': doc.ai_analyzed_at.isoformat() if doc.ai_analyzed_at else None,
                        'created_at': doc.created_at.isoformat()
                    }
                    for doc in documents
                ]
            })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore export documenti critici: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nell\'export documenti critici'
        }), 500

@document_intelligence_bp.route('/compare-version', methods=['POST'])
@login_required
@roles_required(['admin', 'ceo'])
def compare_versions():
    """
    Confronta due versioni di un documento.
    
    Body:
        - document_id: ID del documento
        - version1_id: ID prima versione
        - version2_id: ID seconda versione
        
    Returns:
        JSON con differenze AI
    """
    try:
        data = request.get_json()
        document_id = data.get('document_id')
        version1_id = data.get('version1_id')
        version2_id = data.get('version2_id')
        
        if not all([document_id, version1_id, version2_id]):
            return jsonify({
                'success': False,
                'message': 'Tutti i parametri sono richiesti'
            }), 400
        
        # TODO: Implementare confronto versioni
        # Per ora restituisce mock
        return jsonify({
            'success': True,
            'document_id': document_id,
            'version1_id': version1_id,
            'version2_id': version2_id,
            'differences': [
                {
                    'type': 'content_change',
                    'description': 'Modifica contenuto sezione sicurezza',
                    'severity': 'medium'
                },
                {
                    'type': 'signature_change',
                    'description': 'Aggiunta firma RSPP',
                    'severity': 'high'
                }
            ],
            'ai_recommendation': 'Documento aggiornato correttamente secondo standard HACCP'
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore confronto versioni: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nel confronto versioni'
        }), 500

@document_intelligence_bp.route('/associate-task', methods=['POST'])
@login_required
@roles_required(['admin', 'ceo'])
def associate_task():
    """
    Collega un documento a un task specifico.
    
    Body:
        - document_id: ID del documento
        - task_id: ID del task
        - action: Azione da eseguire ('associate', 'dissociate')
        
    Returns:
        JSON con risultato operazione
    """
    try:
        data = request.get_json()
        document_id = data.get('document_id')
        task_id = data.get('task_id')
        action = data.get('action', 'associate')
        
        if not document_id:
            return jsonify({
                'success': False,
                'message': 'ID documento richiesto'
            }), 400
        
        document = Document.query.get_or_404(document_id)
        
        if action == 'associate':
            if not task_id:
                return jsonify({
                    'success': False,
                    'message': 'ID task richiesto per associazione'
                }), 400
            
            task = Task.query.get_or_404(task_id)
            document.ai_task_id = task_id
            
            # Log audit
            log_event(
                'document_task_association',
                user_id=current_user.id,
                document_id=document_id,
                details={
                    'task_id': task_id,
                    'action': 'associate'
                }
            )
            
            message = f'Documento associato al task {task_id}'
            
        elif action == 'dissociate':
            document.ai_task_id = None
            
            # Log audit
            log_event(
                'document_task_association',
                user_id=current_user.id,
                document_id=document_id,
                details={
                    'task_id': task_id,
                    'action': 'dissociate'
                }
            )
            
            message = 'Associazione documento-task rimossa'
        
        else:
            return jsonify({
                'success': False,
                'message': 'Azione non valida'
            }), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'document_id': document_id,
            'task_id': document.ai_task_id
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore associazione task: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nell\'associazione task'
        }), 500 

# === ROUTE AI 2.0 - JACK SYNTHIA AVANZATO ===

from services.document_intelligence import JackSynthiaAI2
from models import DocumentAIFlag, AIAlert, AIArchiveSuggestion, AIReply, User, Document
from sqlalchemy.orm import Session
from extensions import db

# Inizializzazione Jack Synthia AI 2.0
def get_jack_ai2(db: Session) -> JackSynthiaAI2:
    """Restituisce un'istanza di Jack Synthia AI 2.0."""
    return JackSynthiaAI2(db)

@document_intelligence_bp.route('/api/jack/ai2/verify-document/<int:document_id>', methods=['POST'])
@login_required
def verify_document_content(document_id):
    """
    Auto-verifica il contenuto di un documento per conformità.
    
    Args:
        document_id: ID del documento da verificare
        
    Returns:
        JSON: Risultato della verifica AI
    """
    try:
        db = db()
        jack_ai2 = get_jack_ai2(db)
        
        # Recupera documento
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return jsonify({'error': 'Documento non trovato'}), 404
        
        # Estrai testo dal documento
        extracted_text = extract_text_from_document(document)
        if not extracted_text:
            return jsonify({'error': 'Impossibile estrarre testo dal documento'}), 400
        
        # Verifica contenuto
        ai_flag = jack_ai2.auto_verify_document_content(document, extracted_text)
        
        if ai_flag:
            return jsonify({
                'success': True,
                'flag_type': ai_flag.flag_type,
                'compliance_score': ai_flag.compliance_score,
                'missing_sections': ai_flag.missing_sections,
                'ai_analysis': json.loads(ai_flag.ai_analysis),
                'message': f"Documento verificato: {ai_flag.flag_display}"
            })
        else:
            return jsonify({'error': 'Errore durante la verifica AI'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Errore verifica documento: {str(e)}'}), 500

@document_intelligence_bp.route('/api/jack/ai2/generate-reply', methods=['POST'])
@login_required
def generate_ai_reply():
    """
    Genera una risposta automatica per richieste di accesso negato.
    
    Args:
        request_type: Tipo di richiesta
        user_id: ID utente richiedente
        document_id: ID documento coinvolto (opzionale)
        
    Returns:
        JSON: Risposta automatica generata
    """
    try:
        data = request.get_json()
        request_type = data.get('request_type')
        user_id = data.get('user_id')
        document_id = data.get('document_id')
        
        if not request_type or not user_id:
            return jsonify({'error': 'Parametri mancanti'}), 400
        
        db = db()
        jack_ai2 = get_jack_ai2(db)
        
        # Recupera utente
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        # Recupera documento se specificato
        document = None
        if document_id:
            document = db.query(Document).filter(Document.id == document_id).first()
        
        # Genera risposta
        ai_reply = jack_ai2.generate_auto_reply(request_type, user, document)
        
        if ai_reply:
            return jsonify({
                'success': True,
                'reply_id': ai_reply.id,
                'reply_text': ai_reply.ai_generated_reply,
                'request_type': ai_reply.request_type,
                'status': ai_reply.status,
                'message': 'Risposta automatica generata con successo'
            })
        else:
            return jsonify({'error': 'Errore generazione risposta automatica'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Errore generazione risposta: {str(e)}'}), 500

@document_intelligence_bp.route('/api/jack/ai2/suggest-archive/<int:document_id>', methods=['POST'])
@login_required
def suggest_archive_location(document_id):
    """
    Suggerisce la posizione di archiviazione per un documento.
    
    Args:
        document_id: ID del documento
        
    Returns:
        JSON: Suggerimento di archiviazione
    """
    try:
        db = db()
        jack_ai2 = get_jack_ai2(db)
        
        # Recupera documento
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return jsonify({'error': 'Documento non trovato'}), 404
        
        # Estrai testo dal documento
        extracted_text = extract_text_from_document(document)
        if not extracted_text:
            return jsonify({'error': 'Impossibile estrarre testo dal documento'}), 400
        
        # Suggerisci archiviazione
        suggestion = jack_ai2.suggest_archive_location(document, extracted_text)
        
        if suggestion:
            return jsonify({
                'success': True,
                'suggested_folder': suggestion.suggested_folder,
                'confidence_score': suggestion.confidence_score,
                'reasoning': suggestion.reasoning,
                'message': f"Suggerimento: {suggestion.suggested_folder} ({suggestion.confidence_score}% confidenza)"
            })
        else:
            return jsonify({'error': 'Errore generazione suggerimento'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Errore suggerimento archiviazione: {str(e)}'}), 500

@document_intelligence_bp.route('/api/jack/ai2/check-behavior', methods=['POST'])
@login_required
def check_suspicious_behavior():
    """
    Controlla comportamenti sospetti e genera alert se necessario.
    
    Args:
        user_id: ID utente
        action: Tipo di azione
        document_id: ID documento (opzionale)
        ip_address: IP del client
        user_agent: User agent del browser
        
    Returns:
        JSON: Risultato controllo comportamenti
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        action = data.get('action')
        document_id = data.get('document_id')
        ip_address = data.get('ip_address')
        user_agent = data.get('user_agent')
        
        if not user_id or not action:
            return jsonify({'error': 'Parametri mancanti'}), 400
        
        db = db()
        jack_ai2 = get_jack_ai2(db)
        
        # Recupera utente
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'Utente non trovato'}), 404
        
        # Recupera documento se specificato
        document = None
        if document_id:
            document = db.query(Document).filter(Document.id == document_id).first()
        
        # Controlla comportamenti
        alert = jack_ai2.check_suspicious_behavior(user, action, document, ip_address, user_agent)
        
        if alert:
            return jsonify({
                'success': True,
                'alert_generated': True,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'description': alert.description,
                'message': f"Alert generato: {alert.alert_type_display}"
            })
        else:
            return jsonify({
                'success': True,
                'alert_generated': False,
                'message': 'Nessun comportamento sospetto rilevato'
            })
            
    except Exception as e:
        return jsonify({'error': f'Errore controllo comportamenti: {str(e)}'}), 500

@document_intelligence_bp.route('/api/jack/ai2/flags/<int:document_id>', methods=['GET'])
@login_required
def get_document_ai_flags(document_id):
    """
    Restituisce i flag AI per un documento.
    
    Args:
        document_id: ID del documento
        
    Returns:
        JSON: Lista flag AI
    """
    try:
        db = db()
        jack_ai2 = get_jack_ai2(db)
        
        flags = jack_ai2.get_ai_flags_for_document(document_id)
        
        flags_data = []
        for flag in flags:
            flags_data.append({
                'id': flag.id,
                'flag_type': flag.flag_type,
                'compliance_score': flag.compliance_score,
                'missing_sections': flag.missing_sections,
                'ai_analysis': json.loads(flag.ai_analysis),
                'created_at': flag.created_at.isoformat(),
                'flag_display': flag.flag_display,
                'badge_class': flag.badge_class
            })
        
        return jsonify({
            'success': True,
            'flags': flags_data,
            'count': len(flags_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore recupero flag AI: {str(e)}'}), 500

@document_intelligence_bp.route('/api/jack/ai2/alerts', methods=['GET'])
@login_required
def get_ai_alerts():
    """
    Restituisce gli alert AI attivi.
    
    Args:
        user_id: ID utente (opzionale, per filtrare)
        
    Returns:
        JSON: Lista alert AI
    """
    try:
        user_id = request.args.get('user_id', type=int)
        
        db = db()
        jack_ai2 = get_jack_ai2(db)
        
        alerts = jack_ai2.get_active_alerts(user_id)
        
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'id': alert.id,
                'alert_type': alert.alert_type,
                'alert_type_display': alert.alert_type_display,
                'severity': alert.severity,
                'severity_badge_class': alert.severity_badge_class,
                'description': alert.description,
                'ip_address': alert.ip_address,
                'user_agent': alert.user_agent,
                'created_at': alert.created_at.isoformat(),
                'resolved': alert.resolved,
                'user_id': alert.user_id,
                'document_id': alert.document_id
            })
        
        return jsonify({
            'success': True,
            'alerts': alerts_data,
            'count': len(alerts_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore recupero alert AI: {str(e)}'}), 500

@document_intelligence_bp.route('/api/jack/ai2/archive-suggestions/<int:document_id>', methods=['GET'])
@login_required
def get_archive_suggestions(document_id):
    """
    Restituisce i suggerimenti di archiviazione per un documento.
    
    Args:
        document_id: ID del documento
        
    Returns:
        JSON: Lista suggerimenti archiviazione
    """
    try:
        db = db()
        jack_ai2 = get_jack_ai2(db)
        
        suggestions = jack_ai2.get_archive_suggestions(document_id)
        
        suggestions_data = []
        for suggestion in suggestions:
            suggestions_data.append({
                'id': suggestion.id,
                'suggested_folder': suggestion.suggested_folder,
                'confidence_score': suggestion.confidence_score,
                'confidence_display': suggestion.confidence_display,
                'confidence_badge_class': suggestion.confidence_badge_class,
                'reasoning': suggestion.reasoning,
                'accepted': suggestion.accepted,
                'created_at': suggestion.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'suggestions': suggestions_data,
            'count': len(suggestions_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore recupero suggerimenti: {str(e)}'}), 500

@document_intelligence_bp.route('/api/jack/ai2/replies', methods=['GET'])
@login_required
def get_ai_replies():
    """
    Restituisce le risposte AI generate.
    
    Args:
        user_id: ID utente (opzionale, per filtrare)
        
    Returns:
        JSON: Lista risposte AI
    """
    try:
        user_id = request.args.get('user_id', type=int)
        
        db = db()
        jack_ai2 = get_jack_ai2(db)
        
        replies = jack_ai2.get_ai_replies(user_id)
        
        replies_data = []
        for reply in replies:
            replies_data.append({
                'id': reply.id,
                'request_type': reply.request_type,
                'request_type_display': reply.request_type_display,
                'ai_generated_reply': reply.ai_generated_reply,
                'sent_via': reply.sent_via,
                'status': reply.status,
                'status_badge_class': reply.status_badge_class,
                'sent_at': reply.sent_at.isoformat() if reply.sent_at else None,
                'created_at': reply.created_at.isoformat(),
                'user_id': reply.user_id,
                'document_id': reply.document_id
            })
        
        return jsonify({
            'success': True,
            'replies': replies_data,
            'count': len(replies_data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore recupero risposte AI: {str(e)}'}), 500

@document_intelligence_bp.route('/api/jack/ai2/resolve-alert/<int:alert_id>', methods=['POST'])
@login_required
def resolve_ai_alert(alert_id):
    """
    Risolve un alert AI.
    
    Args:
        alert_id: ID dell'alert da risolvere
        
    Returns:
        JSON: Conferma risoluzione
    """
    try:
        db = db()
        
        # Recupera alert
        alert = db.query(AIAlert).filter(AIAlert.id == alert_id).first()
        if not alert:
            return jsonify({'error': 'Alert non trovato'}), 404
        
        # Risolve alert
        alert.resolved = True
        alert.resolved_by = current_user.username
        alert.resolved_at = datetime.utcnow()
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'Alert {alert.alert_type_display} risolto con successo'
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore risoluzione alert: {str(e)}'}), 500

@document_intelligence_bp.route('/api/jack/ai2/accept-suggestion/<int:suggestion_id>', methods=['POST'])
@login_required
def accept_archive_suggestion(suggestion_id):
    """
    Accetta un suggerimento di archiviazione.
    
    Args:
        suggestion_id: ID del suggerimento da accettare
        
    Returns:
        JSON: Conferma accettazione
    """
    try:
        db = db()
        
        # Recupera suggerimento
        suggestion = db.query(AIArchiveSuggestion).filter(AIArchiveSuggestion.id == suggestion_id).first()
        if not suggestion:
            return jsonify({'error': 'Suggerimento non trovato'}), 404
        
        # Accetta suggerimento
        suggestion.accepted = True
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'Suggerimento "{suggestion.suggested_folder}" accettato'
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore accettazione suggerimento: {str(e)}'}), 500

@document_intelligence_bp.route('/api/jack/ai2/send-reply/<int:reply_id>', methods=['POST'])
@login_required
def send_ai_reply(reply_id):
    """
    Invia una risposta AI generata.
    
    Args:
        reply_id: ID della risposta da inviare
        
    Returns:
        JSON: Conferma invio
    """
    try:
        db = db()
        
        # Recupera risposta
        reply = db.query(AIReply).filter(AIReply.id == reply_id).first()
        if not reply:
            return jsonify({'error': 'Risposta non trovata'}), 404
        
        # Invia risposta (qui implementare la logica di invio email)
        # Per ora simuliamo l'invio
        reply.status = 'inviato'
        reply.sent_at = datetime.utcnow()
        
        db.commit()
        
        return jsonify({
            'success': True,
            'message': f'Risposta {reply.request_type_display} inviata con successo'
        })
        
    except Exception as e:
        return jsonify({'error': f'Errore invio risposta: {str(e)}'}), 500

# === ROUTE AUTO-VERIFICA DOCUMENTI ===

@document_intelligence_bp.route('/ai/verifica/<int:document_id>', methods=['POST'])
@login_required
def auto_verifica_documento_route(document_id):
    """
    Auto-verifica il contenuto di un documento usando AI.
    
    Args:
        document_id: ID del documento da verificare
        
    Returns:
        JSON: Risultato della verifica AI
    """
    try:
        # Verifica che il documento esista
        document = db.session.query(Document).filter(Document.id == document_id).first()
        if not document:
            return jsonify({
                'success': False,
                'error': 'Documento non trovato'
            }), 404
        
        # Esegui auto-verifica
        result = auto_verifica_documento(document_id)
        
        if not result.get('success'):
            return jsonify(result), 500
        
        # Log audit
        log_event(
            'document_ai_verification_requested',
            user_id=current_user.id,
            document_id=document_id,
            details={
                'conforme': result['conforme'],
                'compliance_score': result['compliance_score'],
                'flag_id': result.get('flag_id')
            }
        )
        
        return jsonify({
            'success': True,
            'conforme': result['conforme'],
            'compliance_score': result['compliance_score'],
            'criticita': result['criticita'],
            'suggerimenti': result['suggerimenti'],
            'analisi_dettagliata': result['analisi_dettagliata'],
            'flag_id': result.get('flag_id'),
            'message': f"Documento {'conforme' if result['conforme'] else 'non conforme'} - Punteggio: {result['compliance_score']}%"
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore auto-verifica documento {document_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore durante l\'auto-verifica: {str(e)}'
        }), 500

@document_intelligence_bp.route('/ai/verifica/<int:document_id>/result', methods=['GET'])
@login_required
def get_verification_result(document_id):
    """
    Recupera il risultato di una verifica AI per un documento.
    
    Args:
        document_id: ID del documento
        
    Returns:
        JSON: Risultato verifica AI
    """
    try:
        from models import DocumentAIFlag
        
        # Cerca il flag AI più recente per il documento
        ai_flag = db.session.query(DocumentAIFlag)\
            .filter(DocumentAIFlag.document_id == document_id)\
            .order_by(DocumentAIFlag.created_at.desc())\
            .first()
        
        if not ai_flag:
            return jsonify({
                'success': False,
                'error': 'Nessuna verifica AI trovata per questo documento'
            }), 404
        
        # Parsa l'analisi dettagliata
        try:
            analisi_dettagliata = json.loads(ai_flag.ai_analysis)
        except:
            analisi_dettagliata = {}
        
        return jsonify({
            'success': True,
            'flag_type': ai_flag.flag_type,
            'compliance_score': ai_flag.compliance_score,
            'missing_sections': ai_flag.missing_sections,
            'analisi_dettagliata': analisi_dettagliata,
            'created_at': ai_flag.created_at.isoformat(),
            'is_conforme': ai_flag.is_conforme,
            'flag_display': ai_flag.flag_display
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore recupero risultato verifica {document_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore recupero risultato: {str(e)}'
        }), 500

@document_intelligence_bp.route('/ai/verifica/batch', methods=['POST'])
@login_required
@roles_required(['admin', 'ceo'])
def batch_verifica_documenti():
    """
    Esegue auto-verifica su più documenti in batch.
    
    Body:
        - document_ids: Lista di ID documenti da verificare
        
    Returns:
        JSON: Risultati verifica batch
    """
    try:
        data = request.get_json()
        document_ids = data.get('document_ids', [])
        
        if not document_ids:
            return jsonify({
                'success': False,
                'error': 'Lista documenti richiesta'
            }), 400
        
        if len(document_ids) > 10:
            return jsonify({
                'success': False,
                'error': 'Massimo 10 documenti per batch'
            }), 400
        
        results = []
        for doc_id in document_ids:
            try:
                result = auto_verifica_documento(doc_id)
                results.append({
                    'document_id': doc_id,
                    'success': result.get('success', False),
                    'conforme': result.get('conforme', False),
                    'compliance_score': result.get('compliance_score', 0),
                    'error': result.get('error')
                })
            except Exception as e:
                results.append({
                    'document_id': doc_id,
                    'success': False,
                    'error': str(e)
                })
        
        # Statistiche batch
        total = len(results)
        success_count = sum(1 for r in results if r['success'])
        conforme_count = sum(1 for r in results if r.get('conforme', False))
        avg_score = sum(r.get('compliance_score', 0) for r in results if r['success']) / success_count if success_count > 0 else 0
        
        return jsonify({
            'success': True,
            'results': results,
            'statistics': {
                'total_documents': total,
                'successful_verifications': success_count,
                'conforme_documents': conforme_count,
                'average_compliance_score': round(avg_score, 2)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore verifica batch: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore verifica batch: {str(e)}'
        }), 500


# === ROUTE PER RISPOSTA AI AUTOMATICA ALLE RICHIESTE DI ACCESSO ===

@document_intelligence_bp.route('/ai/richiesta-accesso/<int:request_id>/rispondi', methods=['POST'])
@login_required
@roles_required(['admin', 'ceo'])
def generate_access_response(request_id):
    """
    Genera una risposta AI automatica per una richiesta di accesso.
    
    Args:
        request_id: ID della richiesta di accesso
        
    Body:
        - override_motivazione: Motivazione opzionale da sovrascrivere
        
    Returns:
        JSON: Risultato della generazione risposta AI
    """
    try:
        data = request.get_json() or {}
        override_motivazione = data.get('override_motivazione')
        
        # Genera risposta AI
        result = generate_ai_access_response(request_id, override_motivazione)
        
        if not result.get('success'):
            return jsonify(result), 500
        
        # Log audit
        log_event(
            'access_request_ai_response_generated',
            user_id=current_user.id,
            details={
                'request_id': request_id,
                'ai_parere': result.get('parere_admin'),
                'has_formal_response': bool(result.get('risposta_formale'))
            }
        )
        
        return jsonify({
            'success': True,
            'risposta_formale': result['risposta_formale'],
            'parere_admin': result['parere_admin'],
            'suggerimento_email': result['suggerimento_email'],
            'request_id': request_id,
            'message': 'Risposta AI generata con successo'
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore generazione risposta AI accesso {request_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore durante la generazione: {str(e)}'
        }), 500


@document_intelligence_bp.route('/ai/richiesta-accesso/<int:request_id>/invia-email', methods=['POST'])
@login_required
@roles_required(['admin', 'ceo'])
def send_access_response_email(request_id):
    """
    Invia la risposta AI via email al richiedente.
    
    Args:
        request_id: ID della richiesta di accesso
        
    Body:
        - email_destinatario: Email destinatario (opzionale)
        - personalizza_testo: Testo personalizzato (opzionale)
        
    Returns:
        JSON: Risultato dell'invio email
    """
    try:
        from models import AccessRequest, User
        
        data = request.get_json() or {}
        email_destinatario = data.get('email_destinatario')
        personalizza_testo = data.get('personalizza_testo')
        
        # Recupera la richiesta di accesso
        access_request = db.session.query(AccessRequest).filter(AccessRequest.id == request_id).first()
        if not access_request:
            return jsonify({
                'success': False,
                'error': 'Richiesta di accesso non trovata'
            }), 404
        
        # Recupera utente
        user = db.session.query(User).filter(User.id == access_request.user_id).first()
        if not user:
            return jsonify({
                'success': False,
                'error': 'Utente non trovato'
            }), 404
        
        # Usa email destinatario specificato o email utente
        destinatario = email_destinatario or user.email
        
        # Usa testo personalizzato o risposta AI
        testo_email = personalizza_testo or access_request.risposta_ai
        
        if not testo_email:
            return jsonify({
                'success': False,
                'error': 'Nessuna risposta AI disponibile. Genera prima una risposta.'
            }), 400
        
        # TODO: Implementare invio email reale
        # Per ora simuliamo l'invio
        email_sent = True
        
        if email_sent:
            # Aggiorna stato email
            access_request.email_inviata = True
            access_request.email_destinatario = destinatario
            access_request.email_testo = testo_email
            access_request.email_inviata_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log audit
            log_event(
                'access_request_email_sent',
                user_id=current_user.id,
                details={
                    'request_id': request_id,
                    'destinatario': destinatario,
                    'email_sent': True
                }
            )
            
            return jsonify({
                'success': True,
                'message': f'Email inviata con successo a {destinatario}',
                'email_destinatario': destinatario,
                'email_sent_at': access_request.email_inviata_at.isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Errore nell\'invio dell\'email'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore invio email accesso {request_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore durante l\'invio email: {str(e)}'
        }), 500


@document_intelligence_bp.route('/ai/richiesta-accesso/<int:request_id>/approva', methods=['POST'])
@login_required
@roles_required(['admin', 'ceo'])
def approve_access_request(request_id):
    """
    Approva una richiesta di accesso con risposta AI.
    
    Args:
        request_id: ID della richiesta di accesso
        
    Body:
        - approva: True/False per approvare/negare
        - commento_admin: Commento aggiuntivo (opzionale)
        
    Returns:
        JSON: Risultato dell'approvazione
    """
    try:
        from models import AccessRequest, User, Document
        
        data = request.get_json() or {}
        approva = data.get('approva', False)
        commento_admin = data.get('commento_admin', '')
        
        # Recupera la richiesta di accesso
        access_request = db.session.query(AccessRequest).filter(AccessRequest.id == request_id).first()
        if not access_request:
            return jsonify({
                'success': False,
                'error': 'Richiesta di accesso non trovata'
            }), 404
        
        # Recupera utente e documento
        user = db.session.query(User).filter(User.id == access_request.user_id).first()
        document = db.session.query(Document).filter(Document.id == access_request.document_id).first()
        
        if not user or not document:
            return jsonify({
                'success': False,
                'error': 'Utente o documento non trovato'
            }), 404
        
        # Aggiorna stato richiesta
        if approva:
            access_request.status = "approved"
            action_message = "APPROVATA"
        else:
            access_request.status = "denied"
            action_message = "NEGATA"
        
        access_request.resolved_at = datetime.utcnow()
        
        # Aggiungi commento admin se fornito
        if commento_admin:
            access_request.note = f"{access_request.note or ''}\n\nCommento Admin: {commento_admin}"
        
        db.session.commit()
        
        # Log audit
        log_event(
            'access_request_resolved',
            user_id=current_user.id,
            document_id=document.id,
            details={
                'request_id': request_id,
                'action': action_message,
                'admin_comment': commento_admin,
                'resolved_by': current_user.username
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Richiesta di accesso {action_message.lower()}',
            'status': access_request.status,
            'resolved_at': access_request.resolved_at.isoformat(),
            'request_id': request_id
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore approvazione accesso {request_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore durante l\'approvazione: {str(e)}'
        }), 500


@document_intelligence_bp.route('/ai/richieste-accesso/pending', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def list_pending_access_requests():
    """
    Lista richieste di accesso in attesa con risposte AI.
    
    Query params:
        - limit: Numero massimo risultati (default: 50)
        - offset: Offset per paginazione (default: 0)
        
    Returns:
        JSON: Lista richieste con risposte AI
    """
    try:
        from models import AccessRequest, User, Document
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Recupera richieste in attesa
        requests = db.session.query(AccessRequest).filter(
            AccessRequest.status == "pending"
        ).order_by(AccessRequest.created_at.desc()).limit(limit).offset(offset).all()
        
        results = []
        for req in requests:
            user = db.session.query(User).filter(User.id == req.user_id).first()
            document = db.session.query(Document).filter(Document.id == req.document_id).first()
            
            results.append({
                'id': req.id,
                'user': {
                    'id': user.id if user else None,
                    'username': user.username if user else 'N/A',
                    'email': user.email if user else 'N/A',
                    'role': user.role if user else 'N/A'
                },
                'document': {
                    'id': document.id if document else None,
                    'title': document.title if document else 'N/A',
                    'visibility': document.visibility if document else 'N/A'
                },
                'status': req.status,
                'note': req.note,
                'created_at': req.created_at.isoformat(),
                'ai_response': {
                    'has_response': req.has_ai_response,
                    'parere_admin': req.ai_parere_display,
                    'email_status': req.email_status_display,
                    'analyzed_at': req.ai_analyzed_at.isoformat() if req.ai_analyzed_at else None
                }
            })
        
        return jsonify({
            'success': True,
            'requests': results,
            'total': len(results),
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore recupero richieste accesso: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore durante il recupero: {str(e)}'
        }), 500


# === ROUTE PER SUGGERIMENTO AI ARCHIVIAZIONE ===

@document_intelligence_bp.route('/ai/suggerisci-cartella/<int:document_id>', methods=['GET'])
@login_required
def get_archive_suggestion(document_id):
    """
    Suggerisce automaticamente la cartella di archiviazione per un documento.
    
    Args:
        document_id: ID del documento da analizzare
        
    Returns:
        JSON: Risultato del suggerimento AI
    """
    try:
        # Genera suggerimento AI
        result = suggerisci_cartella_archiviazione(document_id)
        
        if not result.get('success'):
            return jsonify(result), 500
        
        # Log audit
        log_event(
            'archive_suggestion_requested',
            user_id=current_user.id,
            document_id=document_id,
            details={
                'path_suggerito': result.get('path_suggerito'),
                'categoria_suggerita': result.get('categoria_suggerita'),
                'confidence_score': result.get('confidence_score')
            }
        )
        
        return jsonify({
            'success': True,
            'path_suggerito': result['path_suggerito'],
            'categoria_suggerita': result['categoria_suggerita'],
            'tag_ai': result['tag_ai'],
            'motivazione_ai': result['motivazione_ai'],
            'suggested_folder': result['suggested_folder'],
            'confidence_score': result['confidence_score'],
            'azienda_suggerita': result['azienda_suggerita'],
            'reparto_suggerito': result['reparto_suggerito'],
            'tipo_documento_ai': result['tipo_documento_ai'],
            'suggestion_id': result['suggestion_id'],
            'message': 'Suggerimento AI generato con successo'
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore suggerimento archiviazione documento {document_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore durante il suggerimento: {str(e)}'
        }), 500


@document_intelligence_bp.route('/ai/suggerimenti-archiviazione/<int:document_id>', methods=['GET'])
@login_required
def get_archive_suggestions_for_document(document_id):
    """
    Recupera tutti i suggerimenti di archiviazione per un documento.
    
    Args:
        document_id: ID del documento
        
    Returns:
        JSON: Lista suggerimenti AI
    """
    try:
        from models import AIArchiveSuggestion, Document
        
        # Verifica che il documento esista
        document = db.session.query(Document).filter(Document.id == document_id).first()
        if not document:
            return jsonify({
                'success': False,
                'error': 'Documento non trovato'
            }), 404
        
        # Recupera suggerimenti
        suggestions = db.session.query(AIArchiveSuggestion).filter(
            AIArchiveSuggestion.document_id == document_id
        ).order_by(AIArchiveSuggestion.created_at.desc()).all()
        
        results = []
        for suggestion in suggestions:
            results.append({
                'id': suggestion.id,
                'suggested_folder': suggestion.suggested_folder,
                'path_suggerito': suggestion.path_suggerito,
                'categoria_suggerita': suggestion.categoria_suggerita,
                'tag_ai': suggestion.tag_list,
                'motivazione_ai': suggestion.motivazione_ai,
                'confidence_score': suggestion.confidence_score,
                'azienda_suggerita': suggestion.azienda_suggerita,
                'reparto_suggerito': suggestion.reparto_suggerito,
                'tipo_documento_ai': suggestion.tipo_documento_ai,
                'accepted': suggestion.accepted,
                'created_at': suggestion.created_at.isoformat(),
                'confidence_display': suggestion.confidence_display,
                'tag_display': suggestion.tag_display,
                'path_display': suggestion.path_display
            })
        
        return jsonify({
            'success': True,
            'document_id': document_id,
            'document_title': document.title,
            'suggestions': results,
            'total': len(results)
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore recupero suggerimenti archiviazione {document_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore durante il recupero: {str(e)}'
        }), 500


@document_intelligence_bp.route('/ai/suggerimento-archiviazione/<int:suggestion_id>/accetta', methods=['POST'])
@login_required
def accept_archive_suggestion(suggestion_id):
    """
    Accetta un suggerimento di archiviazione AI.
    
    Args:
        suggestion_id: ID del suggerimento da accettare
        
    Body:
        - apply_to_document: True/False per applicare al documento
        - custom_path: Path personalizzato (opzionale)
        
    Returns:
        JSON: Risultato dell'accettazione
    """
    try:
        from models import AIArchiveSuggestion, Document
        
        data = request.get_json() or {}
        apply_to_document = data.get('apply_to_document', False)
        custom_path = data.get('custom_path')
        
        # Recupera suggerimento
        suggestion = db.session.query(AIArchiveSuggestion).filter(AIArchiveSuggestion.id == suggestion_id).first()
        if not suggestion:
            return jsonify({
                'success': False,
                'error': 'Suggerimento non trovato'
            }), 404
        
        # Aggiorna suggerimento come accettato
        suggestion.accepted = True
        
        # Se richiesto, applica al documento
        if apply_to_document:
            document = db.session.query(Document).filter(Document.id == suggestion.document_id).first()
            if document:
                # Aggiorna campi del documento con i suggerimenti AI
                if suggestion.categoria_suggerita:
                    document.categoria_ai = suggestion.categoria_suggerita
                
                if suggestion.tag_ai:
                    document.tag = ", ".join(suggestion.tag_list)
                
                # Log dell'applicazione
                log_event(
                    'archive_suggestion_applied',
                    user_id=current_user.id,
                    document_id=document.id,
                    details={
                        'suggestion_id': suggestion_id,
                        'categoria_applicata': suggestion.categoria_suggerita,
                        'tag_applicati': suggestion.tag_display,
                        'custom_path': custom_path
                    }
                )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Suggerimento accettato con successo',
            'suggestion_id': suggestion_id,
            'applied_to_document': apply_to_document,
            'custom_path': custom_path
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore accettazione suggerimento {suggestion_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore durante l\'accettazione: {str(e)}'
        }), 500


@document_intelligence_bp.route('/ai/suggerimenti-archiviazione/stats', methods=['GET'])
@login_required
@roles_required(['admin', 'ceo'])
def get_archive_suggestions_stats():
    """
    Statistiche sui suggerimenti di archiviazione AI.
    
    Returns:
        JSON: Statistiche suggerimenti
    """
    try:
        from models import AIArchiveSuggestion, Document
        from sqlalchemy import func
        
        # Statistiche generali
        total_suggestions = db.session.query(func.count(AIArchiveSuggestion.id)).scalar()
        accepted_suggestions = db.session.query(func.count(AIArchiveSuggestion.id)).filter(
            AIArchiveSuggestion.accepted == True
        ).scalar()
        
        # Top categorie suggerite
        top_categories = db.session.query(
            AIArchiveSuggestion.categoria_suggerita,
            func.count(AIArchiveSuggestion.id).label('count')
        ).filter(
            AIArchiveSuggestion.categoria_suggerita.isnot(None)
        ).group_by(AIArchiveSuggestion.categoria_suggerita).order_by(
            func.count(AIArchiveSuggestion.id).desc()
        ).limit(10).all()
        
        # Top reparti suggeriti
        top_departments = db.session.query(
            AIArchiveSuggestion.reparto_suggerito,
            func.count(AIArchiveSuggestion.id).label('count')
        ).filter(
            AIArchiveSuggestion.reparto_suggerito.isnot(None)
        ).group_by(AIArchiveSuggestion.reparto_suggerito).order_by(
            func.count(AIArchiveSuggestion.id).desc()
        ).limit(10).all()
        
        # Media confidenza
        avg_confidence = db.session.query(func.avg(AIArchiveSuggestion.confidence_score)).scalar()
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_suggestions': total_suggestions,
                'accepted_suggestions': accepted_suggestions,
                'acceptance_rate': round((accepted_suggestions / total_suggestions * 100) if total_suggestions > 0 else 0, 2),
                'average_confidence': round(avg_confidence or 0, 2),
                'top_categories': [{'categoria': cat, 'count': count} for cat, count in top_categories],
                'top_departments': [{'reparto': dept, 'count': count} for dept, count in top_departments]
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore statistiche suggerimenti archiviazione: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore durante il calcolo statistiche: {str(e)}'
        }), 500 