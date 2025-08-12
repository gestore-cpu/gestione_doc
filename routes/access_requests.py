"""
Route per il sistema di richieste di accesso ai documenti.
Implementa il flusso completo: richiesta → approvazione → enforcement → scadenza.
"""

from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from models import AccessRequest, DocumentShare, Document, User, db
from datetime import datetime, timedelta
from sqlalchemy import and_
from extensions import mail
from flask_mail import Message
import re

access_requests_bp = Blueprint('access_requests', __name__, url_prefix='/access-requests')

# === RATE LIMITING ===
def check_rate_limit(user_id, file_id):
    """
    Verifica il rate limit per le richieste di accesso.
    Max 3 richieste per (file_id, user_id) nelle ultime 24h.
    
    Args:
        user_id (int): ID dell'utente
        file_id (int): ID del file
        
    Returns:
        tuple: (is_allowed, message)
    """
    # Controlla richieste nelle ultime 24h
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_requests = AccessRequest.query.filter(
        and_(
            AccessRequest.requested_by == user_id,
            AccessRequest.file_id == file_id,
            AccessRequest.created_at >= yesterday
        )
    ).count()
    
    if recent_requests >= 3:
        return False, "Hai già inviato 3 richieste per questo documento nelle ultime 24 ore"
    
    return True, ""

def check_existing_pending(user_id, file_id):
    """
    Verifica se esiste già una richiesta pending per la stessa coppia.
    
    Args:
        user_id (int): ID dell'utente
        file_id (int): ID del file
        
    Returns:
        bool: True se esiste già una richiesta pending
    """
    return AccessRequest.query.filter(
        and_(
            AccessRequest.requested_by == user_id,
            AccessRequest.file_id == file_id,
            AccessRequest.status == 'pending'
        )
    ).first() is not None

# === ROUTE PUBBLICHE ===
@access_requests_bp.route('/', methods=['POST'])
@login_required
def create_access_request():
    """
    Crea una nuova richiesta di accesso.
    
    Input:
        file_id (int): ID del documento
        reason (str, opzionale): Motivo della richiesta
        
    Returns:
        JSON response con esito
    """
    try:
        # Validazione input
        file_id = request.form.get('file_id')
        reason = request.form.get('reason', '').strip()
        
        if not file_id:
            return jsonify({'ok': False, 'message': 'ID documento richiesto'}), 400
        
        try:
            file_id = int(file_id)
        except ValueError:
            return jsonify({'ok': False, 'message': 'ID documento non valido'}), 400
        
        # Validazione lunghezza reason
        if len(reason) > 500:
            return jsonify({'ok': False, 'message': 'Motivo troppo lungo (max 500 caratteri)'}), 400
        
        # Verifica esistenza documento
        document = Document.query.get(file_id)
        if not document:
            return jsonify({'ok': False, 'message': 'Documento non trovato'}), 404
        
        # Rate limiting
        is_allowed, rate_limit_msg = check_rate_limit(current_user.id, file_id)
        if not is_allowed:
            return jsonify({'ok': False, 'message': rate_limit_msg}), 429
        
        # Verifica richiesta pending esistente
        if check_existing_pending(current_user.id, file_id):
            return jsonify({'ok': True, 'message': 'Richiesta già inviata'}), 200
        
        # Crea richiesta
        access_request = AccessRequest(
            file_id=file_id,
            requested_by=current_user.id,
            owner_id=document.user_id,
            reason=reason,
            status='pending',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        db.session.add(access_request)
        db.session.commit()
        
        # Invia email di notifica
        send_access_request_notification(access_request)
        
        return jsonify({
            'ok': True, 
            'message': 'Richiesta inviata con successo'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'message': f'Errore interno: {str(e)}'}), 500

# === EMAIL NOTIFICATIONS ===
def send_access_request_notification(access_request):
    """
    Invia email di notifica per la richiesta di accesso.
    
    Args:
        access_request (AccessRequest): Richiesta di accesso
    """
    try:
        # Determina destinatari
        recipients = []
        
        # Se il documento ha un proprietario, notifica lui
        if access_request.owner_id:
            owner = User.query.get(access_request.owner_id)
            if owner and owner.email:
                recipients.append(owner.email)
        
        # Altrimenti notifica tutti gli admin
        if not recipients:
            admins = User.query.filter_by(role='admin').all()
            recipients = [admin.email for admin in admins if admin.email]
        
        if not recipients:
            return
        
        # Prepara email
        subject = f"Nuova richiesta di accesso - {access_request.file.title}"
        
        body = f"""
        È stata ricevuta una nuova richiesta di accesso al documento.
        
        📄 Documento: {access_request.file.title}
        👤 Richiedente: {access_request.requested_by_user.username} ({access_request.requested_by_user.email})
        📝 Motivo: {access_request.reason or 'Nessuno specificato'}
        📅 Data: {access_request.created_at.strftime('%d/%m/%Y %H:%M')}
        
        Per gestire la richiesta, accedi alla dashboard admin:
        {url_for('admin.access_requests_admin', _external=True)}
        """
        
        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body
        )
        
        mail.send(msg)
        
    except Exception as e:
        # Log dell'errore ma non bloccare il flusso
        print(f"Errore invio email notifica: {e}")

def send_approval_notification(access_request, approved=True, expires_at=None):
    """
    Invia email di notifica per l'approvazione/negazione.
    
    Args:
        access_request (AccessRequest): Richiesta di accesso
        approved (bool): True se approvata, False se negata
        expires_at (datetime): Data scadenza (solo se approvata)
    """
    try:
        recipient = access_request.requested_by_user.email
        if not recipient:
            return
        
        if approved:
            subject = f"Richiesta accesso approvata - {access_request.file.title}"
            body = f"""
            La tua richiesta di accesso è stata approvata!
            
            📄 Documento: {access_request.file.title}
            ✅ Stato: Approvata
            📅 Scadenza: {expires_at.strftime('%d/%m/%Y alle %H:%M')}
            
            Puoi ora scaricare il documento fino alla data di scadenza.
            """
        else:
            subject = f"Richiesta accesso negata - {access_request.file.title}"
            body = f"""
            La tua richiesta di accesso è stata negata.
            
            📄 Documento: {access_request.file.title}
            ❌ Stato: Negata
            📝 Motivo: {access_request.decision_reason or 'Non specificato'}
            
            Per ulteriori informazioni, contatta l'amministratore.
            """
        
        msg = Message(
            subject=subject,
            recipients=[recipient],
            body=body
        )
        
        mail.send(msg)
        
    except Exception as e:
        print(f"Errore invio email approvazione: {e}")

# === ENFORCEMENT FUNCTIONS ===
def check_document_access(user_id, file_id):
    """
    Verifica se l'utente ha accesso al documento.
    
    Args:
        user_id (int): ID dell'utente
        file_id (int): ID del documento
        
    Returns:
        tuple: (has_access, reason)
    """
    # Verifica permessi standard
    document = Document.query.get(file_id)
    if not document:
        return False, "Documento non trovato"
    
    # Se l'utente è il proprietario o ha permessi standard
    if document.user_id == user_id:
        return True, "Proprietario"
    
    # Verifica DocumentShare attivo
    active_share = DocumentShare.query.filter(
        and_(
            DocumentShare.file_id == file_id,
            DocumentShare.user_id == user_id,
            DocumentShare.expires_at > datetime.utcnow()
        )
    ).first()
    
    if active_share:
        return True, "Accesso temporaneo"
    
    return False, "Accesso non autorizzato"

# === UTILITY FUNCTIONS ===
def expire_access_requests():
    """
    Scade automaticamente le richieste approvate con expires_at < now.
    """
    try:
        expired_requests = AccessRequest.query.filter(
            and_(
                AccessRequest.status == 'approved',
                AccessRequest.expires_at < datetime.utcnow()
            )
        ).all()
        
        for request in expired_requests:
            request.status = 'expired'
        
        db.session.commit()
        
        # Log del numero di richieste scadute
        if expired_requests:
            print(f"Scadute {len(expired_requests)} richieste di accesso")
            
    except Exception as e:
        db.session.rollback()
        print(f"Errore durante la scadenza richieste: {e}")

def cleanup_expired_shares():
    """
    Pulisce i DocumentShare scaduti.
    """
    try:
        expired_shares = DocumentShare.query.filter(
            DocumentShare.expires_at < datetime.utcnow()
        ).all()
        
        for share in expired_shares:
            db.session.delete(share)
        
        db.session.commit()
        
        if expired_shares:
            print(f"Rimossi {len(expired_shares)} accessi temporanei scaduti")
            
    except Exception as e:
        db.session.rollback()
        print(f"Errore durante la pulizia accessi scaduti: {e}")
