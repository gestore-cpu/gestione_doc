from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, GuestAccess, Document
from datetime import datetime, timedelta
import logging

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

guest_bp = Blueprint('guest', __name__)

@guest_bp.route("/dashboard/guest", methods=["GET"])
@login_required
def dashboard_guest():
    """
    Dashboard per la gestione degli ospiti (guest).
    
    Returns:
        str: Template HTML della dashboard guest
    """
    try:
        # Filtra accessi in base al ruolo utente
        if current_user.role == "user":
            # User vede solo i propri guest
            accessi = GuestAccess.query.filter_by(created_by_user_id=current_user.id).all()
            logger.info(f"User {current_user.id} visualizza {len(accessi)} guest access")
            
        elif current_user.role == "admin":
            # Admin vede tutti i guest della propria azienda
            accessi = (
                GuestAccess.query.join(Document)
                .filter(Document.company_id == current_user.company_id)
                .all()
            )
            logger.info(f"Admin {current_user.id} visualizza {len(accessi)} guest access per company {current_user.company_id}")
            
        elif current_user.is_ceo:
            # CEO vede tutti i guest del sistema
            accessi = GuestAccess.query.all()
            logger.info(f"CEO {current_user.id} visualizza {len(accessi)} guest access totali")
            
        else:
            flash("Accesso negato", "error")
            return redirect(url_for('index'))

        # Importa funzioni AI
        from utils.ai_utils import genera_suggerimenti_guest_ai, analizza_pattern_accessi_guest, genera_raccomandazioni_ai
        
        # Genera suggerimenti AI
        suggerimenti_ai = genera_suggerimenti_guest_ai(accessi)
        
        # Analizza pattern per raccomandazioni
        analisi_pattern = analizza_pattern_accessi_guest(accessi)
        raccomandazioni_ai = genera_raccomandazioni_ai(analisi_pattern)
        
        return render_template(
            "dashboard_guest.html", 
            accessi=accessi, 
            now=datetime.utcnow(),
            suggerimenti_ai=suggerimenti_ai,
            raccomandazioni_ai=raccomandazioni_ai,
            analisi_pattern=analisi_pattern
        )
        
    except Exception as e:
        logger.error(f"Errore nel caricamento dashboard guest: {str(e)}")
        flash("Errore nel caricamento della dashboard", "error")
        return redirect(url_for('index'))

@guest_bp.route("/guest_access/<int:id>/delete", methods=["POST"])
@login_required
def delete_guest_access(id):
    """
    Elimina un accesso guest.
    
    Args:
        id (int): ID dell'accesso guest da eliminare
        
    Returns:
        str: Redirect alla dashboard guest
    """
    try:
        access = GuestAccess.query.get_or_404(id)
        
        # Sicurezza: solo creatore o admin/ceo può eliminare
        if current_user.role == 'user' and access.created_by_user_id != current_user.id:
            flash("Accesso negato", "error")
            return redirect(url_for('dashboard_guest'))
            
        # Verifica che admin possa eliminare solo accessi della propria azienda
        if current_user.role == 'admin':
            document = Document.query.get(access.document_id)
            if document.company_id != current_user.company_id:
                flash("Accesso negato", "error")
                return redirect(url_for('dashboard_guest'))
        
        # Elimina l'accesso
        db.session.delete(access)
        db.session.commit()
        
        logger.info(f"Accesso guest {id} eliminato da user {current_user.id}")
        flash("Accesso eliminato ✅", "success")
        
    except Exception as e:
        logger.error(f"Errore nell'eliminazione accesso guest {id}: {str(e)}")
        flash("Errore nell'eliminazione dell'accesso", "error")
        db.session.rollback()
        
    return redirect(url_for('dashboard_guest'))

@guest_bp.route("/guest_access/<int:id>/update", methods=["POST"])
@login_required
def update_guest_access(id):
    """
    Aggiorna un accesso guest (scadenza e permessi).
    
    Args:
        id (int): ID dell'accesso guest da aggiornare
        
    Returns:
        str: Redirect alla dashboard guest
    """
    try:
        access = GuestAccess.query.get_or_404(id)
        
        # Sicurezza: solo creatore o admin/ceo può modificare
        if current_user.role == 'user' and access.created_by_user_id != current_user.id:
            flash("Accesso negato", "error")
            return redirect(url_for('dashboard_guest'))
            
        # Verifica che admin possa modificare solo accessi della propria azienda
        if current_user.role == 'admin':
            document = Document.query.get(access.document_id)
            if document.company_id != current_user.company_id:
                flash("Accesso negato", "error")
                return redirect(url_for('dashboard_guest'))
        
        # Aggiorna i campi
        expires_at = request.form.get('expires_at')
        can_download = request.form.get('can_download') == 'on'
        
        if expires_at:
            try:
                access.expires_at = datetime.strptime(expires_at, '%Y-%m-%d')
            except ValueError:
                flash("Formato data non valido", "error")
                return redirect(url_for('dashboard_guest'))
        
        access.can_download = can_download
        db.session.commit()
        
        logger.info(f"Accesso guest {id} aggiornato da user {current_user.id}")
        flash("Accesso aggiornato ✅", "success")
        
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento accesso guest {id}: {str(e)}")
        flash("Errore nell'aggiornamento dell'accesso", "error")
        db.session.rollback()
        
    return redirect(url_for('dashboard_guest'))

@guest_bp.route("/guest_access/<int:id>/resend", methods=["POST"])
@login_required
def resend_guest_invitation(id):
    """
    Reinvia l'invito a un guest non registrato.
    
    Args:
        id (int): ID dell'accesso guest per cui reinviare l'invito
        
    Returns:
        str: Redirect alla dashboard guest
    """
    try:
        access = GuestAccess.query.get_or_404(id)
        
        # Sicurezza: solo creatore o admin/ceo può reinviare
        if current_user.role == 'user' and access.created_by_user_id != current_user.id:
            flash("Accesso negato", "error")
            return redirect(url_for('dashboard_guest'))
            
        # Verifica che admin possa reinviare solo inviti della propria azienda
        if current_user.role == 'admin':
            document = Document.query.get(access.document_id)
            if document.company_id != current_user.company_id:
                flash("Accesso negato", "error")
                return redirect(url_for('dashboard_guest'))
        
        # Verifica che il guest non sia già registrato
        if access.guest.password:
            flash("Il guest è già registrato", "warning")
            return redirect(url_for('dashboard_guest'))
        
        # TODO: Implementare logica di reinvio email
        # Per ora solo log dell'azione
        logger.info(f"Reinvio invito per guest {access.guest.email} da user {current_user.id}")
        flash("Invito reinviato ✅", "success")
        
    except Exception as e:
        logger.error(f"Errore nel reinvio invito guest {id}: {str(e)}")
        flash("Errore nel reinvio dell'invito", "error")
        
    return redirect(url_for('dashboard_guest'))

@guest_bp.route("/guest_access/bulk_actions", methods=["POST"])
@login_required
def bulk_guest_actions():
    """
    Azioni rapide per gestione multipla degli accessi guest.
    
    Returns:
        str: Redirect alla dashboard guest
    """
    try:
        action = request.form.get('action')
        
        if action == 'cleanup_expired':
            # Elimina tutti gli accessi scaduti
            oggi = datetime.utcnow()
            accessi_scaduti = GuestAccess.query.filter(GuestAccess.expires_at < oggi).all()
            
            # Filtra per permessi utente
            if current_user.role == 'user':
                accessi_scaduti = [a for a in accessi_scaduti if a.created_by_user_id == current_user.id]
            elif current_user.role == 'admin':
                accessi_scaduti = [a for a in accessi_scaduti if a.document.company_id == current_user.company_id]
            
            count = 0
            for access in accessi_scaduti:
                db.session.delete(access)
                count += 1
            
            db.session.commit()
            flash(f"🧹 Eliminati {count} accessi scaduti", "success")
            
        elif action == 'resend_invites':
            # Reinvia inviti a guest non registrati
            guest_non_registrati = GuestAccess.query.filter(
                GuestAccess.guest.has(password=None)
            ).all()
            
            # Filtra per permessi utente
            if current_user.role == 'user':
                guest_non_registrati = [a for a in guest_non_registrati if a.created_by_user_id == current_user.id]
            elif current_user.role == 'admin':
                guest_non_registrati = [a for a in guest_non_registrati if a.document.company_id == current_user.company_id]
            
            count = 0
            for access in guest_non_registrati:
                # TODO: Implementare invio email
                logger.info(f"Reinvio invito per guest {access.guest.email}")
                count += 1
            
            flash(f"📧 Inviti reinviati a {count} guest non registrati", "success")
            
        elif action == 'extend_expiring':
            # Estende scadenza per accessi in scadenza
            oggi = datetime.utcnow()
            accessi_in_scadenza = GuestAccess.query.filter(
                GuestAccess.expires_at >= oggi,
                GuestAccess.expires_at <= oggi + timedelta(days=3)
            ).all()
            
            # Filtra per permessi utente
            if current_user.role == 'user':
                accessi_in_scadenza = [a for a in accessi_in_scadenza if a.created_by_user_id == current_user.id]
            elif current_user.role == 'admin':
                accessi_in_scadenza = [a for a in accessi_in_scadenza if a.document.company_id == current_user.company_id]
            
            count = 0
            for access in accessi_in_scadenza:
                access.expires_at = access.expires_at + timedelta(days=30)
                count += 1
            
            db.session.commit()
            flash(f"⏰ Estesa scadenza per {count} accessi in scadenza", "success")
            
        else:
            flash("Azione non riconosciuta", "error")
            
    except Exception as e:
        logger.error(f"Errore nelle azioni bulk guest: {str(e)}")
        flash("Errore nell'esecuzione delle azioni", "error")
        db.session.rollback()
        
    return redirect(url_for('dashboard_guest'))

