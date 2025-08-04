"""
Utility per la gestione delle versioni dei documenti.
"""

import os
import shutil
from datetime import datetime
from models import Document, DocumentVersion, db
from flask_login import current_user


def salva_versione_anteriore(document, current_user, note=None):
    """
    Salva la versione attuale come versione storica prima di aggiornarla.
    
    Args:
        document (Document): Il documento da versionare
        current_user (User): L'utente che sta facendo l'upload
        note (str): Note opzionali sulla versione
        
    Returns:
        DocumentVersion: La versione salvata
    """
    try:
        # Trova il numero di versione successivo
        ultima_versione = DocumentVersion.query.filter_by(
            document_id=document.id
        ).order_by(DocumentVersion.version_number.desc()).first()
        
        nuovo_numero = (ultima_versione.version_number + 1) if ultima_versione else 1
        
        # Crea la nuova versione
        versione = DocumentVersion(
            document_id=document.id,
            filename=document.filename,
            filepath=document.file_path,
            uploaded_by=current_user.id,
            is_active=False,  # La versione precedente non è più attiva
            version_number=nuovo_numero,
            note=note
        )
        
        db.session.add(versione)
        db.session.commit()
        
        return versione
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Errore nel salvataggio della versione: {str(e)}")


def attiva_nuova_versione(document, nuovo_filename, nuovo_filepath, current_user, note=None):
    """
    Attiva una nuova versione del documento.
    
    Args:
        document (Document): Il documento da aggiornare
        nuovo_filename (str): Nome del nuovo file
        nuovo_filepath (str): Percorso del nuovo file
        current_user (User): L'utente che sta facendo l'upload
        note (str): Note opzionali sulla versione
        
    Returns:
        DocumentVersion: La nuova versione attiva
    """
    try:
        # Salva la versione precedente
        if document.filename and document.file_path:
            salva_versione_anteriore(document, current_user, "Aggiornamento automatico")
        
        # Disattiva tutte le versioni precedenti
        DocumentVersion.query.filter_by(
            document_id=document.id, 
            is_active=True
        ).update({"is_active": False})
        
        # Aggiorna il documento principale
        document.filename = nuovo_filename
        document.file_path = nuovo_filepath
        document.updated_at = datetime.utcnow()
        
        # Crea la nuova versione attiva
        ultima_versione = DocumentVersion.query.filter_by(
            document_id=document.id
        ).order_by(DocumentVersion.version_number.desc()).first()
        
        nuovo_numero = (ultima_versione.version_number + 1) if ultima_versione else 1
        
        nuova_versione = DocumentVersion(
            document_id=document.id,
            filename=nuovo_filename,
            filepath=nuovo_filepath,
            uploaded_by=current_user.id,
            is_active=True,
            version_number=nuovo_numero,
            note=note or "Versione principale"
        )
        
        db.session.add(nuova_versione)
        db.session.commit()
        
        return nuova_versione
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Errore nell'attivazione della nuova versione: {str(e)}")


def ripristina_versione(version_id, current_user):
    """
    Ripristina una versione precedente come versione attiva.
    
    Args:
        version_id (int): ID della versione da ripristinare
        current_user (User): L'utente che sta facendo il ripristino
        
    Returns:
        DocumentVersion: La versione ripristinata
    """
    try:
        versione = DocumentVersion.query.get_or_404(version_id)
        document = versione.document
        
        # Verifica che il file esista
        if not os.path.exists(versione.filepath):
            raise Exception("File della versione non trovato")
        
        # Salva la versione attuale come storica
        if document.filename and document.file_path:
            salva_versione_anteriore(document, current_user, "Backup prima del ripristino")
        
        # Disattiva tutte le versioni
        DocumentVersion.query.filter_by(
            document_id=document.id
        ).update({"is_active": False})
        
        # Aggiorna il documento principale
        document.filename = versione.filename
        document.file_path = versione.filepath
        document.updated_at = datetime.utcnow()
        
        # Attiva la versione selezionata
        versione.is_active = True
        versione.note = f"Ripristinata da {current_user.username} il {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}"
        
        db.session.commit()
        
        return versione
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Errore nel ripristino della versione: {str(e)}")


def elimina_versione(version_id, current_user):
    """
    Elimina una versione specifica (solo se non è attiva).
    
    Args:
        version_id (int): ID della versione da eliminare
        current_user (User): L'utente che sta facendo l'eliminazione
        
    Returns:
        bool: True se eliminata con successo
    """
    try:
        versione = DocumentVersion.query.get_or_404(version_id)
        
        # Non permettere eliminazione della versione attiva
        if versione.is_active:
            raise Exception("Non è possibile eliminare la versione attiva")
        
        # Elimina il file fisico se esiste
        if os.path.exists(versione.filepath):
            os.remove(versione.filepath)
        
        # Elimina la versione dal database
        db.session.delete(versione)
        db.session.commit()
        
        return True
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Errore nell'eliminazione della versione: {str(e)}")


def get_versioni_documento(document_id):
    """
    Ottiene tutte le versioni di un documento ordinate per numero.
    
    Args:
        document_id (int): ID del documento
        
    Returns:
        list: Lista delle versioni ordinate
    """
    return DocumentVersion.query.filter_by(
        document_id=document_id
    ).order_by(DocumentVersion.version_number.desc()).all()


def get_versione_attiva(document_id):
    """
    Ottiene la versione attiva di un documento.
    
    Args:
        document_id (int): ID del documento
        
    Returns:
        DocumentVersion: La versione attiva o None
    """
    return DocumentVersion.query.filter_by(
        document_id=document_id,
        is_active=True
    ).first()


def confronta_versioni(version1_id, version2_id):
    """
    Confronta due versioni di un documento.
    
    Args:
        version1_id (int): ID della prima versione
        version2_id (int): ID della seconda versione
        
    Returns:
        dict: Dati del confronto
    """
    try:
        v1 = DocumentVersion.query.get_or_404(version1_id)
        v2 = DocumentVersion.query.get_or_404(version2_id)
        
        # Verifica che siano dello stesso documento
        if v1.document_id != v2.document_id:
            raise Exception("Le versioni devono appartenere allo stesso documento")
        
        return {
            'version1': v1,
            'version2': v2,
            'size_diff': v1.file_size - v2.file_size,
            'date_diff': (v1.uploaded_at - v2.uploaded_at).days,
            'same_file': v1.filename == v2.filename
        }
        
    except Exception as e:
        raise Exception(f"Errore nel confronto delle versioni: {str(e)}") 