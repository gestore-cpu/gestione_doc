from itsdangerous import URLSafeTimedSerializer
from flask import current_app
import logging

# Configurazione logging
logger = logging.getLogger(__name__)

def generate_reset_token(email):
    """
    Genera un token sicuro per il reset della password.
    
    Args:
        email (str): Email dell'utente per cui generare il token
        
    Returns:
        str: Token sicuro per il reset
    """
    try:
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        token = s.dumps(email, salt='reset-password')
        logger.info(f"Token reset generato per email: {email}")
        return token
    except Exception as e:
        logger.error(f"Errore nella generazione token reset per {email}: {str(e)}")
        return None

def verify_reset_token(token, expiration=1800):
    """
    Verifica e decodifica un token di reset password.
    
    Args:
        token (str): Token da verificare
        expiration (int): Durata massima del token in secondi (default: 30 minuti)
        
    Returns:
        str: Email dell'utente se il token è valido, None altrimenti
    """
    try:
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = s.loads(token, salt='reset-password', max_age=expiration)
        logger.info(f"Token reset verificato per email: {email}")
        return email
    except Exception as e:
        logger.warning(f"Token reset non valido o scaduto: {str(e)}")
        return None

def is_secure_password(password):
    """
    Verifica se la password soddisfa i criteri di sicurezza.
    
    Args:
        password (str): Password da validare
        
    Returns:
        bool: True se la password è sicura
    """
    if len(password) < 8:
        return False
    
    # Verifica presenza di almeno una lettera maiuscola
    if not any(c.isupper() for c in password):
        return False
    
    # Verifica presenza di almeno una lettera minuscola
    if not any(c.islower() for c in password):
        return False
    
    # Verifica presenza di almeno un numero
    if not any(c.isdigit() for c in password):
        return False
    
    # Verifica presenza di almeno un carattere speciale
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False
    
    return True

def get_password_strength(password):
    """
    Calcola la forza della password.
    
    Args:
        password (str): Password da analizzare
        
    Returns:
        dict: Dizionario con punteggio e suggerimenti
    """
    score = 0
    suggestions = []
    
    # Lunghezza
    if len(password) >= 8:
        score += 1
    else:
        suggestions.append("La password deve essere di almeno 8 caratteri")
    
    # Complessità
    if any(c.isupper() for c in password):
        score += 1
    else:
        suggestions.append("Aggiungi almeno una lettera maiuscola")
    
    if any(c.islower() for c in password):
        score += 1
    else:
        suggestions.append("Aggiungi almeno una lettera minuscola")
    
    if any(c.isdigit() for c in password):
        score += 1
    else:
        suggestions.append("Aggiungi almeno un numero")
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if any(c in special_chars for c in password):
        score += 1
    else:
        suggestions.append("Aggiungi almeno un carattere speciale")
    
    # Valutazione finale
    if score >= 5:
        strength = "forte"
        color = "success"
    elif score >= 3:
        strength = "media"
        color = "warning"
    else:
        strength = "debole"
        color = "danger"
    
    return {
        'score': score,
        'strength': strength,
        'color': color,
        'suggestions': suggestions
    } 