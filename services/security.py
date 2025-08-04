#!/usr/bin/env python3
"""
Servizio di sicurezza per firma digitale con 2FA.
Gestisce token temporanei e calcolo hash SHA256.
"""

import random
import string
import hashlib
import os
from datetime import datetime, timedelta
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def generate_signature_token(user, version):
    """
    Genera un token di firma temporaneo per un utente e versione.
    
    Args:
        user (User): Utente che richiede la firma
        version (DocumentVersion): Versione documento da firmare
        
    Returns:
        str: Token di 6 cifre
    """
    try:
        from app import db
        from models import SignatureToken
        
        # Genera token univoco di 6 cifre
        while True:
            token = ''.join(random.choices(string.digits, k=6))
            
            # Verifica che non esista già
            existing = SignatureToken.query.filter_by(token=token).first()
            if not existing:
                break
        
        # Calcola scadenza (15 minuti)
        expires_at = datetime.utcnow() + timedelta(minutes=15)
        
        # Crea record token
        token_obj = SignatureToken(
            token=token,
            user_id=user.id,
            version_id=version.id,
            expires_at=expires_at
        )
        
        db.session.add(token_obj)
        db.session.commit()
        
        logger.info(f"✅ Token generato per utente {user.username} - versione {version.id}: {token}")
        return token
        
    except Exception as e:
        logger.error(f"❌ Errore generazione token: {e}")
        raise

def validate_signature_token(token, user_id, version_id):
    """
    Valida un token di firma.
    
    Args:
        token (str): Token da validare
        user_id (int): ID utente
        version_id (int): ID versione
        
    Returns:
        SignatureToken or None: Token valido o None
    """
    try:
        from models import SignatureToken
        
        token_obj = SignatureToken.query.filter_by(
            token=token,
            user_id=user_id,
            version_id=version_id,
            used=False
        ).first()
        
        if not token_obj:
            logger.warning(f"❌ Token non trovato: {token}")
            return None
        
        if token_obj.is_expired:
            logger.warning(f"❌ Token scaduto: {token}")
            return None
        
        return token_obj
        
    except Exception as e:
        logger.error(f"❌ Errore validazione token: {e}")
        return None

def mark_token_as_used(token_obj):
    """
    Marca un token come utilizzato.
    
    Args:
        token_obj (SignatureToken): Token da marcare
        
    Returns:
        bool: True se successo
    """
    try:
        from app import db
        
        token_obj.used = True
        db.session.commit()
        
        logger.info(f"✅ Token marcato come utilizzato: {token_obj.token}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Errore marcatura token: {e}")
        return False

def calculate_file_hash(file_path):
    """
    Calcola hash SHA256 di un file.
    
    Args:
        file_path (str): Percorso del file
        
    Returns:
        str: Hash SHA256 del file
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"❌ File non trovato: {file_path}")
            return None
        
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            # Leggi file in chunks per gestire file grandi
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        hash_result = sha256_hash.hexdigest()
        logger.info(f"✅ Hash calcolato per {file_path}: {hash_result[:8]}...")
        return hash_result
        
    except Exception as e:
        logger.error(f"❌ Errore calcolo hash: {e}")
        return None

def invia_token_firma(user, token, version):
    """
    Invia token di firma via email e/o WhatsApp.
    
    Args:
        user (User): Utente destinatario
        token (str): Token da inviare
        version (DocumentVersion): Versione documento
        
    Returns:
        bool: True se invio riuscito
    """
    try:
        from app import mail
        from flask_mail import Message
        
        # Prepara messaggio
        subject = f"🔐 Token Firma Documento - {version.document.title or version.document.original_filename}"
        
        message = f"""
🔐 TOKEN FIRMA DOCUMENTO

📄 Documento: {version.document.title or version.document.original_filename}
📋 Versione: v{version.version_number}
👤 Richiesto da: {user.username}
⏰ Scadenza: 15 minuti

🔢 TOKEN: {token}

⚠️ IMPORTANTE:
- Il token scade tra 15 minuti
- Usalo solo per firmare questo documento specifico
- Non condividere il token con altri

🔗 Accedi a: /admin/docs/{version.document_id}/versions

---
Mercury Document Intelligence
Sistema di Firma Digitale Sicura
{datetime.now().strftime('%d/%m/%Y %H:%M')}
"""
        
        success_count = 0
        
        # Invia email
        if user.reminder_email:
            try:
                msg = Message(
                    subject=subject,
                    recipients=[user.email],
                    body=message.strip(),
                    sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@mercurysurgelati.org')
                )
                mail.send(msg)
                logger.info(f"✅ Email token inviata a {user.email}")
                success_count += 1
            except Exception as e:
                logger.error(f"❌ Errore invio email token a {user.email}: {e}")
        
        # Invia WhatsApp (placeholder)
        if user.reminder_whatsapp and user.phone:
            try:
                # TODO: Integrare con API WhatsApp Business
                logger.info(f"📱 WhatsApp token per {user.phone}: {token}")
                success_count += 1
            except Exception as e:
                logger.error(f"❌ Errore invio WhatsApp token a {user.phone}: {e}")
        
        return success_count > 0
        
    except Exception as e:
        logger.error(f"❌ Errore invio token: {e}")
        return False

def verify_user_can_sign(user, version):
    """
    Verifica se un utente può firmare una versione.
    
    Args:
        user (User): Utente da verificare
        version (DocumentVersion): Versione documento
        
    Returns:
        bool: True se può firmare
    """
    # Ruoli autorizzati per la firma
    authorized_roles = ['ceo', 'rspp', 'dirigente', 'admin']
    
    # Verifica ruolo
    if user.role.lower() not in authorized_roles:
        logger.warning(f"❌ Utente {user.username} non autorizzato alla firma (ruolo: {user.role})")
        return False
    
    # Verifica che non abbia già firmato questa versione
    existing_signature = version.signatures.filter_by(signed_by=user.username).first()
    if existing_signature:
        logger.warning(f"❌ Utente {user.username} ha già firmato la versione {version.id}")
        return False
    
    return True

def create_document_signature(user, version, token_used=None, note=None):
    """
    Crea una firma digitale per un documento.
    
    Args:
        user (User): Utente che firma
        version (DocumentVersion): Versione da firmare
        token_used (str, optional): Token utilizzato per 2FA
        note (str, optional): Note aggiuntive
        
    Returns:
        DocumentSignature or None: Firma creata o None
    """
    try:
        from app import db
        from models import DocumentSignature
        
        # Calcola hash del file
        file_hash = calculate_file_hash(version.file_path)
        if not file_hash:
            logger.error(f"❌ Impossibile calcolare hash per {version.file_path}")
            return None
        
        # Crea firma
        signature = DocumentSignature(
            version_id=version.id,
            signed_by=user.username,
            role=user.role.upper(),
            hash_sha256=file_hash,
            signature_note=note,
            token_used=token_used
        )
        
        db.session.add(signature)
        db.session.commit()
        
        logger.info(f"✅ Firma creata per versione {version.id} da {user.username}")
        return signature
        
    except Exception as e:
        logger.error(f"❌ Errore creazione firma: {e}")
        return None

def cleanup_expired_tokens():
    """
    Pulisce i token scaduti dal database.
    
    Returns:
        int: Numero di token eliminati
    """
    try:
        from app import db
        from models import SignatureToken
        
        # Trova token scaduti
        expired_tokens = SignatureToken.query.filter(
            SignatureToken.expires_at < datetime.utcnow()
        ).all()
        
        count = len(expired_tokens)
        
        # Elimina token scaduti
        for token in expired_tokens:
            db.session.delete(token)
        
        db.session.commit()
        
        if count > 0:
            logger.info(f"🧹 Eliminati {count} token scaduti")
        
        return count
        
    except Exception as e:
        logger.error(f"❌ Errore pulizia token: {e}")
        return 0 