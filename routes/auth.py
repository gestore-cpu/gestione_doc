from flask import Blueprint, render_template, redirect, url_for, request, session, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from forms import LoginForm
from models import User, db
from extensions import bcrypt
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from datetime import datetime
from utils.security import generate_reset_token, verify_reset_token, is_secure_password, get_password_strength

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash("🔒 Sei già autenticato.", "info")
        print("Utente già autenticato, redirect...")
        if current_user.is_admin:
            return redirect(url_for('admin.admin_dashboard'))
        elif current_user.is_user:
            return redirect(url_for('welcome.welcome'))
        elif current_user.is_guest:
            return redirect(url_for('guest.guest_dashboard'))
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('❌ Accesso non consentito: utente non trovato.', 'danger')
            print(f"[LOGIN] Utente non trovato: {email}")
            return render_template('auth/login.html', form=form)


        if not user.password or user.password.strip() == "":
            flash('📝 Primo accesso: completa la registrazione come ospite.', 'warning')
            print(f"[LOGIN] Utente guest senza password valida: {email}")
            return redirect(url_for('guest.guest_register'))

        if not bcrypt.check_password_hash(user.password, form.password.data):
            flash('❌ Password errata.', 'danger')
            print(f"[LOGIN] Password errata per: {email}")
            return render_template('auth/login.html', form=form)

        login_user(user)
        session.permanent = True
        print(f"[LOGIN] Login riuscito per {user.email} (ruolo: {user.role})")

        if user.is_admin:
            return redirect(url_for('admin.admin_dashboard'))
        elif user.is_user:
            return redirect(url_for('welcome.welcome'))
        elif user.is_guest:
            return redirect(url_for('guest.guest_dashboard'))

        flash('⚠️ Ruolo utente non riconosciuto.', 'warning')
        return redirect(url_for('index'))

    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logout eseguito", 'info')
    print("Utente disconnesso")
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """
    Gestisce la richiesta di reset password.
    
    Returns:
        str: Template o redirect
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash("❌ Inserisci un indirizzo email valido.", "danger")
            return render_template('auth/forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Genera token di reset
            token = generate_reset_token(email)
            
            if token:
                # Crea link di reset
                reset_link = url_for('auth.reset_password', token=token, _external=True)
                
                # Invia email di reset
                try:
                    from app import send_email
                    send_email(
                        to=user.email,
                        subject="🔐 Reset Password SYNTHIA",
                        body=f"""Ciao,

Hai richiesto il reset della password per il tuo account SYNTHIA.

Clicca sul link qui sotto per reimpostare la tua password (valido per 30 minuti):

{reset_link}

Se non hai richiesto tu questo reset, ignora questa email.

Saluti,
Team SYNTHIA"""
                    )
                    
                    # BONUS AI: Alert per CEO
                    if user.role == 'ceo' or user.is_ceo:
                        try:
                            send_email(
                                to=current_app.config.get('MAIL_DEFAULT_SENDER', 'admin@synthia.com'),
                                subject="🛡️ Tentativo Reset Password CEO",
                                body=f"""⚠️ ATTENZIONE SICUREZZA

È stato richiesto un reset della password per l'account CEO:
- Email: {email}
- Ruolo: {user.role}
- Data/ora: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}
- IP richiedente: {request.remote_addr}

Verifica immediatamente se questa richiesta è legittima."""
                            )
                        except Exception as e:
                            print(f"Errore nell'invio alert CEO: {e}")
                    
                except Exception as e:
                    print(f"Errore nell'invio email reset: {e}")
                    flash("❌ Errore nell'invio dell'email. Riprova più tardi.", "danger")
                    return render_template('auth/forgot_password.html')
        
        # Per sicurezza, non confermare se l'email esiste
        flash("📩 Se esiste un account con questa email, riceverai un link di reset.", "info")
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
    Gestisce il reset della password tramite token.
    
    Args:
        token (str): Token di reset
        
    Returns:
        str: Template o redirect
    """
    # Verifica token
    email = verify_reset_token(token)
    if not email:
        flash("❌ Link non valido o scaduto.", "danger")
        return redirect(url_for('auth.forgot_password'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("❌ Utente non trovato.", "danger")
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        
        # Validazioni
        if not password:
            flash("❌ Inserisci una password.", "danger")
            return render_template('auth/reset_password.html', email=email, token=token)
        
        if password != confirm:
            flash("❌ Le password non coincidono.", "danger")
            return render_template('auth/reset_password.html', email=email, token=token)
        
        # Verifica sicurezza password
        if not is_secure_password(password):
            flash("❌ La password non soddisfa i criteri di sicurezza.", "danger")
            return render_template('auth/reset_password.html', email=email, token=token)
        
        # Aggiorna password
        try:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user.password = hashed_password
            user.password_set_at = datetime.utcnow()
            db.session.commit()
            
            flash("✅ Password aggiornata con successo. Ora puoi accedere.", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            print(f"Errore nell'aggiornamento password: {e}")
            flash("❌ Errore nell'aggiornamento della password.", "danger")
            return render_template('auth/reset_password.html', email=email, token=token)
    
    return render_template('auth/reset_password.html', email=email, token=token)
