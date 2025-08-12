import csv
import io
from datetime import datetime, timedelta
from typing import Generator, Dict, Any, Optional, List
from sqlalchemy import and_, or_, func
from flask import current_app, request, flash
from models import AccessRequestNew, DocumentShare, Document, User, db
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

class AccessRequestService:
    """Service per gestire le richieste di accesso ai documenti bloccati."""
    
    def __init__(self):
        self.rate_limit_window = 24 * 60 * 60  # 24 ore in secondi
        self.rate_limit_max = 3  # Max 3 richieste per file/utente nelle ultime 24h
        self.request_logs = {}
    
    def check_rate_limit(self, user_id: int, file_id: int) -> bool:
        """
        Verifica il rate limit per le richieste di accesso.
        
        Args:
            user_id (int): ID dell'utente.
            file_id (int): ID del file.
            
        Returns:
            bool: True se il rate limit non è superato.
        """
        current_time = time.time()
        key = f"{user_id}_{file_id}"
        
        # Pulisci log vecchi
        if key in self.request_logs:
            self.request_logs[key] = [t for t in self.request_logs[key] 
                                    if current_time - t < self.rate_limit_window]
        else:
            self.request_logs[key] = []
        
        # Verifica se il limite è superato
        if len(self.request_logs[key]) >= self.rate_limit_max:
            return False
        
        # Aggiungi timestamp corrente
        self.request_logs[key].append(current_time)
        return True
    
    def create_access_request(self, user_id: int, file_id: int, reason: str = None) -> Dict[str, Any]:
        """
        Crea una nuova richiesta di accesso.
        
        Args:
            user_id (int): ID dell'utente richiedente.
            file_id (int): ID del documento.
            reason (str): Motivo della richiesta (opzionale).
            
        Returns:
            dict: Risultato dell'operazione.
        """
        try:
            # Verifica esistenza file
            document = Document.query.get(file_id)
            if not document:
                return {"success": False, "message": "Documento non trovato."}
            
            # Verifica esistenza utente
            user = User.query.get(user_id)
            if not user:
                return {"success": False, "message": "Utente non trovato."}
            
            # Verifica rate limit
            if not self.check_rate_limit(user_id, file_id):
                return {"success": False, "message": "Hai già fatto troppe richieste per questo documento nelle ultime 24 ore."}
            
            # Verifica se esiste già una richiesta pending
            existing_request = AccessRequestNew.query.filter_by(
                file_id=file_id,
                requested_by=user_id,
                status='pending'
            ).first()
            
            if existing_request:
                return {"success": False, "message": "Hai già una richiesta in attesa per questo documento."}
            
            # Crea nuova richiesta
            access_request = AccessRequestNew(
                file_id=file_id,
                requested_by=user_id,
                owner_id=document.owner_id,
                reason=reason,
                status='pending',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(access_request)
            db.session.commit()
            
            # Log dell'evento
            logger.info(f"Nuova richiesta accesso creata: utente={user.username}, file={document.filename}")
            
            return {
                "success": True, 
                "message": "Richiesta di accesso inviata con successo.",
                "request_id": access_request.id
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore creazione richiesta accesso: {e}")
            return {"success": False, "message": "Errore durante la creazione della richiesta."}
    
    def get_pending_requests(self, filters: Dict[str, Any] = None) -> List[AccessRequestNew]:
        """
        Ottiene le richieste in attesa con filtri opzionali.
        
        Args:
            filters (dict): Filtri da applicare.
            
        Returns:
            list: Lista delle richieste.
        """
        query = AccessRequestNew.query.filter_by(status='pending')
        
        if filters:
            if filters.get('file_id'):
                query = query.filter_by(file_id=filters['file_id'])
            
            if filters.get('requested_by'):
                query = query.filter_by(requested_by=filters['requested_by'])
            
            if filters.get('owner_id'):
                query = query.filter_by(owner_id=filters['owner_id'])
            
            if filters.get('from_date'):
                query = query.filter(AccessRequestNew.created_at >= filters['from_date'])
            
            if filters.get('to_date'):
                query = query.filter(AccessRequestNew.created_at <= filters['to_date'])
        
        return query.order_by(AccessRequestNew.created_at.desc()).all()
    
    def approve_request(self, request_id: int, admin_id: int, expires_in_hours: int = 72, decision_reason: str = None) -> Dict[str, Any]:
        """
        Approva una richiesta di accesso.
        
        Args:
            request_id (int): ID della richiesta.
            admin_id (int): ID dell'admin che approva.
            expires_in_hours (int): Ore di validità dell'accesso.
            decision_reason (str): Motivo della decisione.
            
        Returns:
            dict: Risultato dell'operazione.
        """
        try:
            access_request = AccessRequestNew.query.get(request_id)
            if not access_request:
                return {"success": False, "message": "Richiesta non trovata."}
            
            if access_request.status != 'pending':
                return {"success": False, "message": "La richiesta non è più in attesa."}
            
            # Calcola scadenza
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            
            # Aggiorna richiesta
            access_request.status = 'approved'
            access_request.approver_id = admin_id
            access_request.decided_at = datetime.utcnow()
            access_request.expires_at = expires_at
            access_request.decision_reason = decision_reason
            access_request.updated_at = datetime.utcnow()
            
            # Crea concessione temporanea
            document_share = DocumentShare(
                file_id=access_request.file_id,
                user_id=access_request.requested_by,
                granted_by=admin_id,
                granted_at=datetime.utcnow(),
                expires_at=expires_at,
                scope='download',
                notes=f"Approvata da richiesta #{request_id}"
            )
            
            db.session.add(document_share)
            db.session.commit()
            
            # Log dell'evento
            logger.info(f"Richiesta accesso approvata: ID={request_id}, admin={admin_id}, scadenza={expires_at}")
            
            return {
                "success": True,
                "message": "Richiesta approvata con successo.",
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore approvazione richiesta: {e}")
            return {"success": False, "message": "Errore durante l'approvazione."}
    
    def deny_request(self, request_id: int, admin_id: int, decision_reason: str = None) -> Dict[str, Any]:
        """
        Nega una richiesta di accesso.
        
        Args:
            request_id (int): ID della richiesta.
            admin_id (int): ID dell'admin che nega.
            decision_reason (str): Motivo della decisione.
            
        Returns:
            dict: Risultato dell'operazione.
        """
        try:
            access_request = AccessRequestNew.query.get(request_id)
            if not access_request:
                return {"success": False, "message": "Richiesta non trovata."}
            
            if access_request.status != 'pending':
                return {"success": False, "message": "La richiesta non è più in attesa."}
            
            # Aggiorna richiesta
            access_request.status = 'denied'
            access_request.approver_id = admin_id
            access_request.decided_at = datetime.utcnow()
            access_request.decision_reason = decision_reason
            access_request.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log dell'evento
            logger.info(f"Richiesta accesso negata: ID={request_id}, admin={admin_id}")
            
            return {
                "success": True,
                "message": "Richiesta negata con successo."
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore negazione richiesta: {e}")
            return {"success": False, "message": "Errore durante la negazione."}
    
    def check_user_access(self, user_id: int, file_id: int) -> bool:
        """
        Verifica se un utente ha accesso a un file tramite concessione temporanea.
        
        Args:
            user_id (int): ID dell'utente.
            file_id (int): ID del file.
            
        Returns:
            bool: True se l'utente ha accesso.
        """
        # Cerca concessione attiva
        share = DocumentShare.query.filter_by(
            file_id=file_id,
            user_id=user_id
        ).filter(
            DocumentShare.expires_at > datetime.utcnow()
        ).first()
        
        return share is not None
    
    def expire_old_requests(self):
        """
        Marca come scadute le richieste approvate scadute.
        """
        try:
            # Trova richieste approvate scadute
            expired_requests = AccessRequestNew.query.filter(
                and_(
                    AccessRequestNew.status == 'approved',
                    AccessRequestNew.expires_at < datetime.utcnow()
                )
            ).all()
            
            for request in expired_requests:
                request.status = 'expired'
                request.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            if expired_requests:
                logger.info(f"Marcate {len(expired_requests)} richieste come scadute")
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Errore scadenza richieste: {e}")
    
    def get_request_stats(self) -> Dict[str, int]:
        """
        Ottiene statistiche sulle richieste.
        
        Returns:
            dict: Statistiche.
        """
        try:
            total_pending = AccessRequestNew.query.filter_by(status='pending').count()
            
            today = datetime.utcnow().date()
            today_requests = AccessRequestNew.query.filter(
                func.date(AccessRequestNew.created_at) == today
            ).count()
            
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_requests = AccessRequestNew.query.filter(
                AccessRequestNew.created_at >= week_ago
            ).count()
            
            return {
                'pending': total_pending,
                'today': today_requests,
                'week': week_requests
            }
            
        except Exception as e:
            logger.error(f"Errore statistiche richieste: {e}")
            return {'pending': 0, 'today': 0, 'week': 0}

# Istanza globale del service
access_request_service = AccessRequestService()

def rate_limit_access_request(f):
    """Decorator per rate limiting delle richieste di accesso."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app.config['LOGIN_DISABLED']: # Assuming current_app is available
            from flask import current_user, jsonify # Import here to avoid circular dependency
            if not current_user.is_authenticated:
                return jsonify({"success": False, "message": "Autenticazione richiesta"}), 401
        
        user_id = current_app.config['LOGIN_DISABLED'] and 1 or current_user.id # Placeholder for user_id if login is disabled
        file_id = request.form.get('file_id') or request.json.get('file_id')
        
        if not file_id:
            return jsonify({"success": False, "message": "ID file richiesto"}), 400
        
        if not access_request_service.check_rate_limit(user_id, int(file_id)):
            return jsonify({"success": False, "message": "Troppe richieste per questo documento"}), 429
        
        return f(*args, **kwargs)
    return decorated_function
