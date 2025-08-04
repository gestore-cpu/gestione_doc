from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import logging
from datetime import datetime

# Configurazione logging
logger = logging.getLogger(__name__)

def get_drive_service():
    """
    Inizializza e restituisce il servizio Google Drive.
    
    Returns:
        googleapiclient.discovery.Resource: Servizio Google Drive
    """
    try:
        # Carica credenziali dal file JSON
        credentials_path = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON")
        if not credentials_path or not os.path.exists(credentials_path):
            raise FileNotFoundError(f"File credenziali Google Drive non trovato: {credentials_path}")
        
        creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        
        service = build('drive', 'v3', credentials=creds)
        logger.info("Servizio Google Drive inizializzato correttamente")
        return service
        
    except Exception as e:
        logger.error(f"Errore nell'inizializzazione Google Drive: {str(e)}")
        raise

def create_or_get_folder(service, folder_name, parent_id):
    """
    Crea una cartella su Google Drive o restituisce quella esistente.
    
    Args:
        service: Servizio Google Drive
        folder_name (str): Nome della cartella
        parent_id (str): ID della cartella padre
        
    Returns:
        str: ID della cartella
    """
    try:
        # Cerca cartella esistente
        query = f"'{parent_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query).execute().get('files', [])
        
        if results:
            folder_id = results[0]['id']
            logger.info(f"Cartella '{folder_name}' trovata con ID: {folder_id}")
            return folder_id
        else:
            # Crea nuova cartella
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            
            file = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = file.get('id')
            logger.info(f"Cartella '{folder_name}' creata con ID: {folder_id}")
            return folder_id
            
    except Exception as e:
        logger.error(f"Errore nella creazione/ricerca cartella '{folder_name}': {str(e)}")
        raise

def upload_to_drive(local_path, nome_file, subfolders):
    """
    Carica un file su Google Drive nella struttura di cartelle specificata.
    
    Args:
        local_path (str): Percorso del file locale
        nome_file (str): Nome del file da salvare su Drive
        subfolders (list): Lista delle sottocartelle (es. [azienda, reparto, categoria])
        
    Returns:
        str: ID del file caricato su Google Drive
    """
    try:
        # Verifica esistenza file locale
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"File locale non trovato: {local_path}")
        
        # Inizializza servizio Drive
        service = get_drive_service()
        
        # Ottieni ID cartella root
        root_folder_id = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")
        if not root_folder_id:
            raise ValueError("GOOGLE_DRIVE_ROOT_FOLDER_ID non configurato")
        
        # Naviga/crea struttura cartelle
        current_parent_id = root_folder_id
        for folder_name in subfolders:
            if folder_name:  # Salta cartelle vuote
                current_parent_id = create_or_get_folder(service, folder_name, current_parent_id)
        
        # Prepara metadata file
        file_metadata = {
            'name': nome_file,
            'parents': [current_parent_id]
        }
        
        # Carica file
        media = MediaFileUpload(local_path, resumable=True)
        uploaded_file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id,name,webViewLink'
        ).execute()
        
        file_id = uploaded_file.get('id')
        web_link = uploaded_file.get('webViewLink')
        
        logger.info(f"File '{nome_file}' caricato su Drive con ID: {file_id}")
        logger.info(f"Link visualizzazione: {web_link}")
        
        return file_id
        
    except Exception as e:
        logger.error(f"Errore nell'upload su Drive del file '{nome_file}': {str(e)}")
        raise

def delete_from_drive(file_id):
    """
    Elimina un file da Google Drive.
    
    Args:
        file_id (str): ID del file su Google Drive
        
    Returns:
        bool: True se eliminato con successo
    """
    try:
        service = get_drive_service()
        service.files().delete(fileId=file_id).execute()
        logger.info(f"File con ID {file_id} eliminato da Google Drive")
        return True
        
    except Exception as e:
        logger.error(f"Errore nell'eliminazione file {file_id} da Drive: {str(e)}")
        return False

def get_file_info(file_id):
    """
    Ottiene informazioni su un file di Google Drive.
    
    Args:
        file_id (str): ID del file su Google Drive
        
    Returns:
        dict: Informazioni del file
    """
    try:
        service = get_drive_service()
        file_info = service.files().get(
            fileId=file_id, 
            fields='id,name,size,createdTime,modifiedTime,webViewLink'
        ).execute()
        
        return file_info
        
    except Exception as e:
        logger.error(f"Errore nel recupero info file {file_id}: {str(e)}")
        return None

def check_drive_connection():
    """
    Verifica la connessione a Google Drive.
    
    Returns:
        bool: True se connessione OK
    """
    try:
        service = get_drive_service()
        # Prova a listare i file per verificare la connessione
        service.files().list(pageSize=1).execute()
        logger.info("Connessione Google Drive verificata con successo")
        return True
        
    except Exception as e:
        logger.error(f"Errore nella verifica connessione Google Drive: {str(e)}")
        return False 