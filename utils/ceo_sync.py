"""
Modulo per sincronizzazione con sistema centrale CEO.
"""

import os
import requests
import logging
from datetime import datetime
from flask import current_app

def sync_with_ceo(data, entity_type):
    """
    Sincronizza dati con il sistema centrale CEO.
    
    Args:
        data (dict): Dati da sincronizzare
        entity_type (str): 'users' o 'guests'
    
    Returns:
        bool: True se sincronizzazione riuscita, False altrimenti
    """
    try:
        # Configurazione API CEO
        ceo_base_url = 'https://64.226.70.28/api/sync'
        ceo_token = os.getenv('CEO_API_TOKEN', 'default_token')
        
        # Prepara headers
        headers = {
            'Authorization': f'Bearer {ceo_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Mercury-DOCS/1.0'
        }
        
        # Prepara payload
        payload = {
            'id': data.get('id'),
            'nome': data.get('nome'),
            'email': data.get('email'),
            'ruolo': data.get('ruolo'),
            'azienda': data.get('azienda'),
            'reparto': data.get('reparto'),
            'stato': data.get('stato'),
            'modulo': 'Mercury',
            'ultimo_accesso': data.get('ultimo_accesso'),
            'timestamp': datetime.utcnow().isoformat(),
            'action': data.get('action', 'sync')
        }
        
        # Aggiungi campi specifici per guest
        if entity_type == 'guests':
            payload.update({
                'documenti_assegnati': data.get('documenti_assegnati', []),
                'scadenza_accesso': data.get('scadenza_accesso'),
                'giorni_alla_scadenza': data.get('giorni_alla_scadenza')
            })
        
        # Effettua chiamata API
        endpoint = f'{ceo_base_url}/{entity_type}'
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            current_app.logger.info(f'Sincronizzazione CEO {entity_type} {data.get("email")} completata')
            return True
        else:
            current_app.logger.error(f'Errore sincronizzazione CEO {entity_type}: {response.status_code} - {response.text}')
            log_ceo_sync_error(entity_type, data, response.status_code, response.text)
            return False
            
    except Exception as e:
        current_app.logger.error(f'Errore sincronizzazione CEO {entity_type}: {str(e)}')
        log_ceo_sync_error(entity_type, data, 0, str(e))
        return False

def log_ceo_sync_error(entity_type, data, status_code, error_message):
    """
    Logga errori di sincronizzazione CEO.
    
    Args:
        entity_type (str): Tipo di entità ('users' o 'guests')
        data (dict): Dati che causarono l'errore
        status_code (int): Codice di stato HTTP
        error_message (str): Messaggio di errore
    """
    try:
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'ceo_sync.log')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.utcnow().isoformat()
            f.write(f'[{timestamp}] ERROR - Entity: {entity_type}, ID: {data.get("id")}, '
                   f'Email: {data.get("email")}, Status: {status_code}, Error: {error_message}\n')
                    
    except Exception as e:
        current_app.logger.error(f'Errore logging CEO sync: {str(e)}')

def analizza_attivita_ai(activity_data, entity_type):
    """
    Analizza dati attività per AI (placeholder per futura integrazione).
    
    Args:
        activity_data (list): Lista dati attività
        entity_type (str): 'users' o 'guests'
    """
    try:
        # Conta comportamenti anomali
        anomalous_count = sum(1 for item in activity_data if item.get('comportamento_anomalo', False))
        
        # Analizza pattern temporali
        night_access_count = sum(1 for item in activity_data 
                               if item.get('orari_accesso', {}).get('night', 0) > 0)
        
        # Conta tentativi login falliti
        total_failed_logins = sum(item.get('tentativi_login_falliti', 0) for item in activity_data)
        
        # Logga risultati per AI futura
        current_app.logger.info(f'AI Analysis {entity_type}: '
                              f'Total: {len(activity_data)}, '
                              f'Anomalous: {anomalous_count}, '
                              f'Night access: {night_access_count}, '
                              f'Failed logins: {total_failed_logins}')
        
        # Placeholder per futura integrazione con motore AI Synthia
        # In futuro qui verrà chiamata l'API AI per analisi comportamentale
        
        # Simula invio dati a sistema AI centrale
        ai_payload = {
            'entity_type': entity_type,
            'total_records': len(activity_data),
            'anomalous_count': anomalous_count,
            'night_access_count': night_access_count,
            'total_failed_logins': total_failed_logins,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'Mercury-DOCS'
        }
        
        # In futuro: invio a sistema AI centrale
        # send_to_ai_engine(ai_payload)
        
    except Exception as e:
        current_app.logger.error(f'Errore analisi AI {entity_type}: {str(e)}')

def sync_user_creation(user):
    """
    Sincronizza creazione utente con CEO.
    
    Args:
        user: Oggetto User da sincronizzare
    """
    try:
        user_data = {
            'id': user.id,
            'nome': f"{user.first_name} {user.last_name}",
            'email': user.email,
            'ruolo': user.role,
            'azienda': user.company.name if user.company else None,
            'reparto': user.department.name if user.department else None,
            'stato': 'active',
            'ultimo_accesso': None,
            'action': 'create'
        }
        
        return sync_with_ceo(user_data, 'users')
        
    except Exception as e:
        current_app.logger.error(f'Errore sync creazione utente: {str(e)}')
        return False

def sync_user_update(user):
    """
    Sincronizza aggiornamento utente con CEO.
    
    Args:
        user: Oggetto User da sincronizzare
    """
    try:
        user_data = {
            'id': user.id,
            'nome': f"{user.first_name} {user.last_name}",
            'email': user.email,
            'ruolo': user.role,
            'azienda': user.company.name if user.company else None,
            'reparto': user.department.name if user.department else None,
            'stato': 'active' if not user.access_expiration or user.access_expiration > datetime.utcnow() else 'expired',
            'ultimo_accesso': user.last_login.isoformat() if user.last_login else None,
            'action': 'update'
        }
        
        return sync_with_ceo(user_data, 'users')
        
    except Exception as e:
        current_app.logger.error(f'Errore sync aggiornamento utente: {str(e)}')
        return False

def sync_user_deletion(user_id):
    """
    Sincronizza eliminazione utente con CEO.
    
    Args:
        user_id (int): ID utente eliminato
    """
    try:
        user_data = {
            'id': user_id,
            'action': 'delete'
        }
        
        return sync_with_ceo(user_data, 'users')
        
    except Exception as e:
        current_app.logger.error(f'Errore sync eliminazione utente: {str(e)}')
        return False

def sync_guest_creation(guest):
    """
    Sincronizza creazione guest con CEO.
    
    Args:
        guest: Oggetto User (guest) da sincronizzare
    """
    try:
        guest_data = {
            'id': guest.id,
            'nome': f"{guest.first_name} {guest.last_name}",
            'email': guest.email,
            'ruolo': 'guest',
            'azienda': guest.company.name if guest.company else None,
            'reparto': None,
            'stato': 'active',
            'ultimo_accesso': None,
            'documenti_assegnati': [],  # Lista documenti assegnati
            'scadenza_accesso': guest.access_expiration.isoformat() if guest.access_expiration else None,
            'giorni_alla_scadenza': (guest.access_expiration - datetime.utcnow()).days if guest.access_expiration else None,
            'action': 'create'
        }
        
        return sync_with_ceo(guest_data, 'guests')
        
    except Exception as e:
        current_app.logger.error(f'Errore sync creazione guest: {str(e)}')
        return False

def sync_guest_update(guest):
    """
    Sincronizza aggiornamento guest con CEO.
    
    Args:
        guest: Oggetto User (guest) da sincronizzare
    """
    try:
        guest_data = {
            'id': guest.id,
            'nome': f"{guest.first_name} {guest.last_name}",
            'email': guest.email,
            'ruolo': 'guest',
            'azienda': guest.company.name if guest.company else None,
            'reparto': None,
            'stato': 'active' if not guest.access_expiration or guest.access_expiration > datetime.utcnow() else 'expired',
            'ultimo_accesso': guest.last_login.isoformat() if guest.last_login else None,
            'documenti_assegnati': [],  # Lista documenti assegnati
            'scadenza_accesso': guest.access_expiration.isoformat() if guest.access_expiration else None,
            'giorni_alla_scadenza': (guest.access_expiration - datetime.utcnow()).days if guest.access_expiration else None,
            'action': 'update'
        }
        
        return sync_with_ceo(guest_data, 'guests')
        
    except Exception as e:
        current_app.logger.error(f'Errore sync aggiornamento guest: {str(e)}')
        return False

def sync_guest_deletion(guest_id):
    """
    Sincronizza eliminazione guest con CEO.
    
    Args:
        guest_id (int): ID guest eliminato
    """
    try:
        guest_data = {
            'id': guest_id,
            'action': 'delete'
        }
        
        return sync_with_ceo(guest_data, 'guests')
        
    except Exception as e:
        current_app.logger.error(f'Errore sync eliminazione guest: {str(e)}')
        return False 