"""
Socket.IO server per approvazioni e KPI live.
Gestisce connessioni WebSocket per aggiornamenti in tempo reale.
"""

from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request, session
from flask_login import current_user
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Inizializza Socket.IO
socketio = SocketIO(
    cors_allowed_origins="*",  # In produzione, specifica domini
    logger=True,
    engineio_logger=True,
    async_mode='threading'
)

# Store per tracking connessioni
connected_users = {}

@socketio.on('connect')
def handle_connect():
    """Gestisce connessione client."""
    if not current_user.is_authenticated:
        logger.warning(f"⚠️ Tentativo connessione non autenticato da {request.remote_addr}")
        return False
    
    user_id = current_user.id
    user_email = current_user.email
    
    # Salva info connessione
    connected_users[user_id] = {
        'email': user_email,
        'sid': request.sid,
        'connected_at': datetime.utcnow(),
        'ip': request.remote_addr
    }
    
    # Unisciti alla stanza personale
    join_room(f"user_{user_id}")
    
    # Unisciti alle stanze basate sul ruolo
    if current_user.role in ['Admin', 'CEO', 'CISO']:
        join_room("admin_approvals")
        join_room("admin_kpi")
    
    if current_user.role in ['TeamLead', 'SecurityAnalyst']:
        join_room("team_approvals")
    
    logger.info(f"✅ Client connesso: {user_email} (ID: {user_id}, SID: {request.sid})")
    
    # Invia conferma connessione
    emit('connection_established', {
        'user_id': user_id,
        'user_email': user_email,
        'role': current_user.role,
        'timestamp': datetime.utcnow().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Gestisce disconnessione client."""
    if current_user.is_authenticated:
        user_id = current_user.id
        user_email = current_user.email
        
        # Rimuovi da tracking
        if user_id in connected_users:
            del connected_users[user_id]
        
        logger.info(f"🔌 Client disconnesso: {user_email} (ID: {user_id})")

@socketio.on('join_approval_room')
def handle_join_approval_room(data):
    """Gestisce join stanza approvazioni specifiche."""
    if not current_user.is_authenticated:
        return
    
    room = data.get('room')
    if room:
        join_room(room)
        logger.info(f"👥 {current_user.email} unito alla stanza: {room}")
        emit('room_joined', {'room': room})

@socketio.on('leave_approval_room')
def handle_leave_approval_room(data):
    """Gestisce leave stanza approvazioni specifiche."""
    if not current_user.is_authenticated:
        return
    
    room = data.get('room')
    if room:
        leave_room(room)
        logger.info(f"👋 {current_user.email} lasciato la stanza: {room}")
        emit('room_left', {'room': room})

def emit_approval_event(event_data: dict):
    """
    Emette evento approvazione a tutti i client connessi.
    
    Args:
        event_data (dict): Dati dell'evento approvazione
    """
    try:
        # Aggiungi timestamp se non presente
        if 'timestamp' not in event_data:
            event_data['timestamp'] = datetime.utcnow().isoformat()
        
        # Emetti a tutte le stanze appropriate
        socketio.emit('approval_event', event_data, namespace='/approvals')
        
        logger.info(f"📨 Evento approvazione emesso: {event_data.get('type', 'unknown')}")
        
    except Exception as e:
        logger.error(f"❌ Errore emissione evento approvazione: {e}")

def emit_kpi_update(kpi_data: dict):
    """
    Emette aggiornamento KPI a tutti i client admin.
    
    Args:
        kpi_data (dict): Dati KPI aggiornati
    """
    try:
        # Aggiungi timestamp se non presente
        if 'timestamp' not in kpi_data:
            kpi_data['timestamp'] = datetime.utcnow().isoformat()
        
        # Emetti solo agli admin
        socketio.emit('kpi_update', kpi_data, room='admin_kpi', namespace='/approvals')
        
        logger.info(f"📊 KPI update emesso: {kpi_data.get('type', 'unknown')}")
        
    except Exception as e:
        logger.error(f"❌ Errore emissione KPI update: {e}")

def emit_user_notification(user_id: int, notification_data: dict):
    """
    Emette notifica a un utente specifico.
    
    Args:
        user_id (int): ID utente destinatario
        notification_data (dict): Dati notifica
    """
    try:
        # Aggiungi timestamp se non presente
        if 'timestamp' not in notification_data:
            notification_data['timestamp'] = datetime.utcnow().isoformat()
        
        # Emetti alla stanza personale dell'utente
        room = f"user_{user_id}"
        socketio.emit('user_notification', notification_data, room=room, namespace='/approvals')
        
        logger.info(f"🔔 Notifica inviata a utente {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Errore invio notifica utente {user_id}: {e}")

def emit_escalation_alert(escalation_data: dict):
    """
    Emette alert escalation agli admin.
    
    Args:
        escalation_data (dict): Dati escalation
    """
    try:
        # Aggiungi timestamp se non presente
        if 'timestamp' not in escalation_data:
            escalation_data['timestamp'] = datetime.utcnow().isoformat()
        
        # Emetti agli admin
        socketio.emit('escalation_alert', escalation_data, room='admin_approvals', namespace='/approvals')
        
        logger.warning(f"🚨 Alert escalation emesso: {escalation_data.get('type', 'unknown')}")
        
    except Exception as e:
        logger.error(f"❌ Errore emissione escalation alert: {e}")

def get_connected_users_count() -> dict:
    """
    Ottiene statistiche utenti connessi.
    
    Returns:
        dict: Statistiche connessioni
    """
    try:
        total_connected = len(connected_users)
        
        # Raggruppa per ruolo
        role_counts = {}
        for user_data in connected_users.values():
            role = user_data.get('role', 'unknown')
            role_counts[role] = role_counts.get(role, 0) + 1
        
        return {
            'total_connected': total_connected,
            'role_counts': role_counts,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Errore conteggio utenti connessi: {e}")
        return {'total_connected': 0, 'role_counts': {}, 'error': str(e)}

# Eventi di sistema
@socketio.on('ping')
def handle_ping():
    """Gestisce ping client."""
    emit('pong', {'timestamp': datetime.utcnow().isoformat()})

@socketio.on('get_connection_info')
def handle_get_connection_info():
    """Invia info connessione al client."""
    if current_user.is_authenticated:
        emit('connection_info', {
            'user_id': current_user.id,
            'user_email': current_user.email,
            'role': current_user.role,
            'connected_at': connected_users.get(current_user.id, {}).get('connected_at'),
            'timestamp': datetime.utcnow().isoformat()
        })

@socketio.on('error')
def handle_error(data):
    """Gestisce errori client."""
    logger.error(f"❌ Errore client Socket.IO: {data}")
    emit('error_ack', {'received': True})
