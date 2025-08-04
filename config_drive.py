"""
Configurazione Google Drive API per upload automatico documenti.

Questo file contiene le configurazioni necessarie per l'integrazione
con Google Drive API per l'upload automatico dei documenti approvati.

IMPORTANTE: Configura le variabili d'ambiente nel file .env:

GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON=/percorso/credenziali/drive.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=XXX123  # ID della cartella root su Drive
"""

import os
from dotenv import load_dotenv

load_dotenv()

# === CONFIGURAZIONE GOOGLE DRIVE ===

# Percorso file credenziali Service Account
GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON')

# ID cartella root su Google Drive
GOOGLE_DRIVE_ROOT_FOLDER_ID = os.getenv('GOOGLE_DRIVE_ROOT_FOLDER_ID')

# Scopes necessari per Google Drive API
GOOGLE_DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

# Configurazione upload
DRIVE_UPLOAD_CONFIG = {
    'max_file_size': 100 * 1024 * 1024,  # 100MB
    'allowed_extensions': [
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
        '.ppt', '.pptx', '.txt', '.rtf', '.csv',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp',
        '.zip', '.rar', '.7z'
    ],
    'folder_structure': {
        'company': True,      # Crea cartella azienda
        'department': True,   # Crea cartella reparto  
        'category': True      # Crea cartella categoria
    }
}

# === VALIDAZIONE CONFIGURAZIONE ===

def validate_drive_config():
    """
    Valida la configurazione Google Drive.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    errors = []
    
    # Verifica file credenziali
    if not GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON:
        errors.append("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON non configurato")
    elif not os.path.exists(GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON):
        errors.append(f"File credenziali non trovato: {GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON}")
    
    # Verifica ID cartella root
    if not GOOGLE_DRIVE_ROOT_FOLDER_ID:
        errors.append("GOOGLE_DRIVE_ROOT_FOLDER_ID non configurato")
    
    if errors:
        return False, "; ".join(errors)
    
    return True, "Configurazione Google Drive valida"

# === UTILITY CONFIGURAZIONE ===

def get_drive_folder_structure():
    """
    Restituisce la configurazione struttura cartelle.
    
    Returns:
        dict: Configurazione struttura cartelle
    """
    return DRIVE_UPLOAD_CONFIG['folder_structure']

def get_allowed_extensions():
    """
    Restituisce le estensioni file permesse.
    
    Returns:
        list: Lista estensioni permesse
    """
    return DRIVE_UPLOAD_CONFIG['allowed_extensions']

def is_file_allowed(filename):
    """
    Verifica se un file è permesso per l'upload.
    
    Args:
        filename (str): Nome del file
        
    Returns:
        bool: True se permesso
    """
    if not filename:
        return False
    
    ext = os.path.splitext(filename)[1].lower()
    return ext in get_allowed_extensions()

def get_max_file_size():
    """
    Restituisce la dimensione massima file.
    
    Returns:
        int: Dimensione massima in bytes
    """
    return DRIVE_UPLOAD_CONFIG['max_file_size'] 