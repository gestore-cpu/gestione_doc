from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import bcrypt, db
from datetime import datetime, timedelta
from auth.forms import LoginForm
from urllib.parse import urlparse, urljoin

auth_bp = Blueprint('auth', __name__)

# === Funzione di sicurezza per i redirect ===
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    print("🔵 [DEBUG] login() chiamato")

    if current_user.is_authenticated:
        print("🟢 [DEBUG] Utente già autenticato. Redirect in base al ruolo")
        if current_user.is_admin:
            return redirect(url_for('admin.admin_dashboard'))
        elif current_user.is_user:
            return redirect(url_for('user.dashboard'))
        else:
            return redirect(url_for('welcome.welcome'))

    form = LoginForm()
    next_page = request.args.get('next') or request.form.get('next')

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        print(f"🔍 [DEBUG] Trovato utente: {user}")

        if user and user.check_password(form.password.data):
            print(f"🔓 [DEBUG] Login riuscito per {user.username}")
            login_user(user)

            if user.password_set_at and datetime.utcnow() > user.password_set_at + timedelta(days=180):
                flash("⚠️ La tua password è scaduta. Aggiornala.", "warning")
                return redirect(url_for('auth.change_password'))

            # === Redirect sicuro se presente ===
            if next_page and is_safe_url(next_page):
                if next_page.startswith('/admin') and not user.is_admin:
                    flash("❌ Accesso non autorizzato all'area admin", "danger")
                    return redirect(url_for('welcome.welcome'))
                return redirect(next_page)

            # === Redirect in base al ruolo ===
            if user.is_admin:
                return redirect(url_for('admin.admin_dashboard'))
            elif user.is_user:
                return redirect(url_for('user.dashboard'))
            else:
                return redirect(url_for('welcome.welcome'))

        flash('❌ Credenziali errate', 'danger')

    elif form.errors:
        print("⚠️ [DEBUG] Form non valido:", form.errors)
        flash("⚠️ Dati mancanti o non validi. Controlla il form.", "warning")

    return render_template('auth/login.html', form=form, next=next_page)

