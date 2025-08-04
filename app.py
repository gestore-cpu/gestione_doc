import os
import logging
import random
from datetime import datetime
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, flash, render_template, session, redirect, url_for, request, send_file
from flask_wtf import CSRFProtect
from flask_login import LoginManager, login_required, current_user, logout_user
from flask_migrate import Migrate
from flask_session import Session
from cryptography.fernet import Fernet
from flask.cli import with_appcontext
from logging.handlers import RotatingFileHandler
from extensions import db, bcrypt, mail, csrf
from routes.auth import auth_bp
from routes.admin_routes import admin_bp
from routes.user_routes import user_bp
from routes.docs import docs_bp
from routes.dashboard_ceo import ceo_bp
from routes.ceo_routes import ceo_bp as ceo_brighter_bp
from drive_routes import drive_bp
from upload_routes import upload_bp
from routes.welcome import welcome_bp
from routes.visite_mediche_routes import visite_mediche_bp
from routes.firme_manuali_routes import firme_manuali_bp
from routes.prove_evacuazione_routes import prove_evacuazione_bp
from routes.visite_mediche_avanzate_routes import visite_mediche_avanzate_bp
from routes.quality_routes import quality_bp
from models import User, Document, AdminLog
from werkzeug.utils import secure_filename
from googleapiclient.http import MediaFileUpload
import uuid
import click


basedir = os.path.abspath(os.path.dirname(__file__))

# === APP SETUP ===
app = Flask(
    __name__,
    template_folder=os.path.join(basedir, 'templates'),
    static_folder=os.path.join(basedir, 'static')
)

app.secret_key = os.getenv('SECRET_KEY')

# === ABILITA DEBUG (SOLO IN SVILUPPO) ===
app.config['DEBUG'] = True
app.debug = True

# === LOGGING SU FILE ===
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

# === CONFIG ===
app.config.update({
    'SECRET_KEY': os.getenv('SECRET_KEY'),
    'SESSION_TYPE': 'filesystem',
    'WTF_CSRF_TIME_LIMIT': 3600,
    'WTF_CSRF_ENABLED': True,
    'UPLOAD_FOLDER': os.path.join(basedir, 'uploads'),
    'SQLALCHEMY_DATABASE_URI': f"sqlite:///{os.path.join(basedir, 'gestione.db')}",
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'MAIL_SERVER': os.getenv('MAIL_SERVER'),
    'MAIL_PORT': int(os.getenv('MAIL_PORT', 587)),
    'MAIL_USE_TLS': True,
    'MAIL_USERNAME': os.getenv('MAIL_USERNAME'),
    'MAIL_PASSWORD': os.getenv('MAIL_PASSWORD'),
    'MAIL_DEFAULT_SENDER': os.getenv('MAIL_DEFAULT_SENDER'),
    'SESSION_COOKIE_DOMAIN': None,
    'SESSION_COOKIE_SECURE': False,
    'SESSION_COOKIE_SAMESITE': 'Lax',
    'MAX_CONTENT_LENGTH': 16 * 1024 * 1024
})

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# === SESSION SETUP ===
Session(app)

# === FERNET SETUP ===
fernet_key = os.getenv('FERNET_KEY')
if not fernet_key:
    raise RuntimeError("✖ FERNET_KEY mancante in .env")
try:
    fernet = Fernet(fernet_key.encode())
except Exception as e:
    raise RuntimeError(f"✖ Errore inizializzazione Fernet: {e}")

# === EXTENSIONS INITIALIZATION ===
csrf.init_app(app)
db.init_app(app)
bcrypt.init_app(app)
mail.init_app(app)

from itsdangerous import URLSafeTimedSerializer
serializer = URLSafeTimedSerializer(app.secret_key)

migrate = Migrate(app, db)

# === LOGIN MANAGER ===
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

from routes.guest_routes import guest_bp
from routes.qms_routes import qms_bp
from routes.drive_upload import drive_bp
from routes.documents import docs_bp
from routes.synthia_eventi import router as synthia_eventi_bp
from routes.jack_docs_routes import router as jack_docs_bp

# === REGISTER BLUEPRINTS ===
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
app.register_blueprint(ceo_bp, url_prefix="/ceo", name="ceo_dashboard")
app.register_blueprint(ceo_brighter_bp, url_prefix="/ceo")
app.register_blueprint(drive_bp, url_prefix="/drive")
app.register_blueprint(upload_bp)
app.register_blueprint(welcome_bp)
app.register_blueprint(guest_bp, url_prefix="/guest")
app.register_blueprint(qms_bp, url_prefix="/qms")
app.register_blueprint(docs_bp, url_prefix="/docs")
app.register_blueprint(visite_mediche_bp, url_prefix="/visite_mediche")
app.register_blueprint(firme_manuali_bp, url_prefix="/firme_manuali")
app.register_blueprint(prove_evacuazione_bp, url_prefix="/prove_evacuazione")
app.register_blueprint(visite_mediche_avanzate_bp, url_prefix="/visite_mediche_avanzate")
app.register_blueprint(synthia_eventi_bp, url_prefix="/synthia")
app.register_blueprint(jack_docs_bp, url_prefix="/jack")
app.register_blueprint(quality_bp, url_prefix="/quality")

# === SCHEDULER SETUP ===
try:
    from scheduler import avvia_scheduler
    with app.app_context():
        avvia_scheduler(app)
    app.logger.info("✅ Scheduler APScheduler avviato per reminder automatici")
except Exception as e:
    app.logger.error(f"❌ Errore avvio scheduler: {e}")

# === CLI COMMAND ===
@click.command("set-role")
@click.argument("email")
@click.argument("role")
@with_appcontext
def set_user_role(email, role):
    from models import User
    from extensions import db
    user = User.query.filter_by(email=email.strip().lower()).first()
    if not user:
        print(f"❌ Utente con email {email} non trovato.")
        return
    valid_roles = ["admin", "user", "guest"]
    if role not in valid_roles:
        print(f"❌ Ruolo non valido. Usa uno di: {', '.join(valid_roles)}.")
        return
    user.role = role
    db.session.commit()
    print(f"✅ Ruolo di {user.email} aggiornato a '{role}'.")

app.cli.add_command(set_user_role)

# === CLI COMMAND PER TEST REMINDER ===
@click.command("test-reminder")
@with_appcontext
def test_reminder():
    """Test manuale del sistema di reminder automatici."""
    try:
        from scheduler import processa_reminder
        from models import Reminder, User
        
        print("🧪 Test sistema reminder automatici...")
        
        # Conta reminder attivi
        reminder_attivi = Reminder.query.filter_by(stato='attivo').count()
        print(f"📊 Reminder attivi nel sistema: {reminder_attivi}")
        
        # Conta utenti
        utenti_totali = User.query.count()
        print(f"👥 Utenti totali: {utenti_totali}")
        
        # Esegui processamento
        print("⚙️ Esecuzione processamento reminder...")
        processa_reminder()
        
        print("✅ Test completato!")
        
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")

app.cli.add_command(test_reminder)

# === CLI COMMAND PER CREARE REMINDER DI TEST ===
@click.command("create-test-reminder")
@click.argument("email")
@click.argument("tipo")
@click.argument("messaggio")
@with_appcontext
def create_test_reminder(email, tipo, messaggio):
    """Crea un reminder di test per un utente."""
    try:
        from scheduler import crea_reminder_automatico
        from models import User
        from datetime import datetime, timedelta
        
        # Verifica che l'utente esista
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"❌ Utente con email {email} non trovato.")
            return
        
        # Crea scadenza di test (tra 5 giorni)
        scadenza = datetime.utcnow() + timedelta(days=5)
        
        # Crea reminder
        reminder = crea_reminder_automatico(
            tipo=tipo,
            entita_id=1,
            entita_tipo='Document',
            destinatario_email=email,
            destinatario_ruolo='hr',
            scadenza=scadenza,
            giorni_anticipo=3,
            messaggio=messaggio,
            canale='email',
            created_by=user.id
        )
        
        if reminder:
            print(f"✅ Reminder di test creato per {email}")
            print(f"📅 Scadenza: {scadenza.strftime('%d/%m/%Y')}")
            print(f"📧 Prossimo invio: {reminder.prossimo_invio.strftime('%d/%m/%Y %H:%M')}")
        else:
            print("❌ Errore nella creazione del reminder")
            
    except Exception as e:
        print(f"❌ Errore: {e}")

app.cli.add_command(create_test_reminder)

# === CLI COMMAND PER GENERARE REMINDER AUTOMATICI ===
@click.command("generate-reminders")
@with_appcontext
def generate_reminders():
    """Genera automaticamente reminder per visite mediche, documenti e checklist."""
    try:
        from scheduler import genera_reminder
        
        print("🔄 Avvio generazione automatica reminder...")
        genera_reminder()
        print("✅ Generazione reminder completata!")
        
    except Exception as e:
        print(f"❌ Errore durante la generazione: {e}")

app.cli.add_command(generate_reminders)

# === CLI COMMAND PER VERIFICARE REMINDER ===
@click.command("list-reminders")
@with_appcontext
def list_reminders():
    """Lista tutti i reminder nel sistema."""
    try:
        from models import Reminder, User
        
        print("📋 Lista Reminder nel Sistema")
        print("=" * 50)
        
        reminder_totali = Reminder.query.count()
        print(f"📊 Totale reminder: {reminder_totali}")
        
        if reminder_totali == 0:
            print("ℹ️ Nessun reminder presente nel sistema.")
            return
        
        # Raggruppa per tipo
        reminder_per_tipo = {}
        for reminder in Reminder.query.all():
            tipo = reminder.tipo
            if tipo not in reminder_per_tipo:
                reminder_per_tipo[tipo] = []
            reminder_per_tipo[tipo].append(reminder)
        
        for tipo, reminders in reminder_per_tipo.items():
            print(f"\n🔸 {tipo.upper()} ({len(reminders)}):")
            for r in reminders[:5]:  # Mostra solo i primi 5
                stato = "✅" if r.stato == 'inviato' else "⏳" if r.stato == 'attivo' else "❌"
                print(f"  {stato} {r.messaggio[:50]}... (scadenza: {r.scadenza.strftime('%d/%m/%Y')})")
            
            if len(reminders) > 5:
                print(f"  ... e altri {len(reminders) - 5} reminder")
        
        # Statistiche per stato
        attivi = Reminder.query.filter_by(stato='attivo').count()
        inviati = Reminder.query.filter_by(stato='inviato').count()
        scaduti = Reminder.query.filter_by(stato='scaduto').count()
        
        print(f"\n📈 Statistiche:")
        print(f"  ⏳ Attivi: {attivi}")
        print(f"  ✅ Inviati: {inviati}")
        print(f"  ❌ Scaduti: {scaduti}")
        
    except Exception as e:
        print(f"❌ Errore: {e}")

app.cli.add_command(list_reminders)

# === CLI COMMAND PER TESTARE DASHBOARD REMINDER ===
@click.command("test-dashboard-reminder")
@with_appcontext
def test_dashboard_reminder():
    """Test della dashboard reminder."""
    try:
        from models import Reminder, User
        
        print("🧪 Test Dashboard Reminder")
        print("=" * 40)
        
        # Conta reminder
        reminder_totali = Reminder.query.count()
        print(f"📊 Reminder totali: {reminder_totali}")
        
        if reminder_totali == 0:
            print("ℹ️ Nessun reminder presente. Crea prima alcuni reminder di test:")
            print("   flask create-test-reminder <email> <tipo> <messaggio>")
            return
        
        # Mostra alcuni esempi
        print("\n📋 Esempi di reminder:")
        for i, reminder in enumerate(Reminder.query.limit(3).all()):
            print(f"  {i+1}. {reminder.tipo_display} - {reminder.destinatario_email}")
            print(f"      Messaggio: {reminder.messaggio[:50]}...")
            print(f"      Scadenza: {reminder.scadenza.strftime('%d/%m/%Y')}")
            print(f"      Stato: {reminder.stato_display}")
            print()
        
        print("✅ Dashboard reminder pronta!")
        print("🔗 URL: /dashboard/reminder")
        
    except Exception as e:
        print(f"❌ Errore: {e}")

app.cli.add_command(test_dashboard_reminder)

# === CLI COMMAND PER TESTARE EXPORT REMINDER ===
@click.command("test-export-reminder")
@with_appcontext
def test_export_reminder():
    """Test delle funzionalità di export reminder."""
    try:
        from models import Reminder
        
        print("🧪 Test Export Reminder")
        print("=" * 40)
        
        # Conta reminder
        reminder_totali = Reminder.query.count()
        print(f"📊 Reminder totali: {reminder_totali}")
        
        if reminder_totali == 0:
            print("ℹ️ Nessun reminder presente. Crea prima alcuni reminder di test:")
            print("   flask create-test-reminder <email> <tipo> <messaggio>")
            return
        
        # Test export CSV
        print("\n📥 Test Export CSV:")
        print("   URL: /dashboard/reminder/export/csv")
        print("   File: reminder_synthia.csv")
        
        # Test export PDF
        print("\n📄 Test Export PDF:")
        print("   URL: /dashboard/reminder/export/pdf")
        print("   File: reminder_synthia.pdf")
        
        # Statistiche per AI
        urgenti = Reminder.query.filter(Reminder.is_urgente == True).count()
        scaduti = Reminder.query.filter(Reminder.is_scaduto == True).count()
        non_inviati = Reminder.query.filter(Reminder.stato != 'inviato').count()
        
        print(f"\n🧠 Statistiche AI:")
        print(f"   Urgenti: {urgenti}")
        print(f"   Scaduti: {scaduti}")
        print(f"   Non inviati: {non_inviati}")
        
        if urgenti > 0 or scaduti > 0:
            print("   ⚠️ Attenzione: ci sono reminder che richiedono azione!")
        else:
            print("   ✅ Tutto sotto controllo!")
        
        print("\n✅ Test export completato!")
        
    except Exception as e:
        print(f"❌ Errore: {e}")

app.cli.add_command(test_export_reminder)

# === CLI COMMAND PER TESTARE FIRME MANUALI ===
@click.command("test-firme-manuali")
@with_appcontext
def test_firme_manuali():
    """Test del sistema di firme manuali."""
    try:
        from models import FirmaManuale, Document
        
        print("🧪 Test Sistema Firme Manuali")
        print("=" * 40)
        
        # Conta firme esistenti
        firme_totali = FirmaManuale.query.count()
        print(f"📊 Firme manuali registrate: {firme_totali}")
        
        # Conta documenti
        documenti_totali = Document.query.count()
        print(f"📄 Documenti disponibili: {documenti_totali}")
        
        # Statistiche per tipo
        if firme_totali > 0:
            print(f"\n📈 Statistiche:")
            firme_recenti = FirmaManuale.query.filter(FirmaManuale.is_recente == True).count()
            print(f"   Firme recenti (≤30 giorni): {firme_recenti}")
            
            # Firme per documento
            firme_per_doc = db.session.query(
                FirmaManuale.documento_id,
                db.func.count(FirmaManuale.id).label('count')
            ).group_by(FirmaManuale.documento_id).all()
            
            print(f"   Documenti con firme: {len(firme_per_doc)}")
        
        # Test routes
        print(f"\n🔗 Routes disponibili:")
        print(f"   Upload: /firme_manuali/firma_manuale/upload")
        print(f"   Download: /firme_manuali/firma_manuale/<id>/download")
        print(f"   Delete: /firme_manuali/firma_manuale/<id>/delete")
        
        # Test cartella upload
        import os
        upload_folder = os.path.join(app.root_path, 'static', 'uploads', 'firme_manuali')
        if os.path.exists(upload_folder):
            files_count = len([f for f in os.listdir(upload_folder) if os.path.isfile(os.path.join(upload_folder, f))])
            print(f"📁 File in upload folder: {files_count}")
        else:
            print("❌ Cartella upload non trovata")
        
        print("\n✅ Test completato!")
        
    except Exception as e:
        print(f"❌ Errore: {e}")

app.cli.add_command(test_firme_manuali)

import re
from google.oauth2 import service_account
from googleapiclient.discovery import build

# === LOGGER ===
log_dir = os.path.join(basedir, 'logs')
os.makedirs(log_dir, exist_ok=True)

file_handler = RotatingFileHandler(
    os.path.join(log_dir, 'app.log'),
    maxBytes=10240,
    backupCount=10
)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
file_handler.setLevel(logging.DEBUG)

app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG)  # 🔥 QUESTA MANCAVA!

# === Google Drive Setup ===
drive_service = None
try:
    if not app.config.get("TESTING", False):
        SCOPES = ['https://www.googleapis.com/auth/drive']
        SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if SERVICE_ACCOUNT_FILE:
            credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            drive_service = build('drive', 'v3', credentials=credentials)
        else:
            app.logger.warning("Variabile GOOGLE_APPLICATION_CREDENTIALS non trovata.")
    else:
        app.logger.info("In modalità test: Google Drive disattivato.")
except Exception as e:
    app.logger.warning(f"Errore durante l'inizializzazione di Google Drive: {e}")

# === Password validator ===
def is_secure_password(password):
    """
    Verifica se la password soddisfa i criteri di sicurezza minimi.

    Args:
        password (str): La password da validare.

    Returns:
        bool: True se la password è sicura, False altrimenti.
    """
    return (
        len(password) >= 8 and
        re.search(r'[A-Z]', password) and
        re.search(r'\d', password) and
        re.search(r'[^A-Za-z0-9]', password)
    )

# === Allowed file extensions ===
ALLOWED_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'odt', 'xls', 'xlsx', 'ods',
    'ppt', 'pptx', 'odp', 'txt', 'rtf', 'csv', 'tsv',
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg'
}

def allowed_file(filename):
    """
    Controlla se il file ha un'estensione consentita.

    Args:
        filename (str): Il nome del file.

    Returns:
        bool: True se l'estensione è ammessa, False altrimenti.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === User loader ===
@login_manager.user_loader
def load_user(user_id):
    """
    Carica l'utente dal database dato l'user_id.

    Args:
        user_id (int): L'ID dell'utente.

    Returns:
        User: L'oggetto utente corrispondente.
    """
    return User.query.get(int(user_id))

# === Helper functions ===
def send_email(subject, recipients, body, html_body=None):
    """
    Invia una email tramite Flask-Mail.

    Args:
        subject (str): Oggetto della mail.
        recipients (list): Lista destinatari.
        body (str): Corpo testuale.
        html_body (str, optional): Corpo HTML.
    """
    app.logger.info(f"send_email called with recipients={recipients}")
    try:
        from flask_mail import Message
        msg = Message(subject=subject, recipients=recipients)
        msg.body = body
        if html_body:
            msg.html = html_body
        conn = mail.connect()
        conn.send(msg)
        conn.close()
    except Exception as e:
        app.logger.error(f"Errore invio email: {e}")

def notify_upload(doc):
    """
    Notifica l'utente del caricamento di un documento via email.

    Args:
        doc (Document): Il documento caricato.
    """
    subject = f"\U0001F4E4 Documento caricato: {doc.title}"
    body = (
        f"L'utente {doc.uploader_email} ha caricato un documento.\n"
        f"Titolo: {doc.title}\n"
        f"Azienda: {doc.company.name if doc.company else 'N/A'}\n"
        f"Reparto: {doc.department.name if doc.department else 'N/A'}\n"
    )
    send_email(subject, [doc.uploader_email], body)

def notify_download(doc, user_email):
    """
    Notifica l'utente e l'uploader del download di un documento.

    Args:
        doc (Document): Il documento scaricato.
        user_email (str): Email dell'utente che ha scaricato.
    """
    subject = f"\u2B07\uFE0F Documento scaricato: {doc.title}"
    body = (
        f"L'utente {user_email} ha scaricato il documento.\n"
        f"Titolo: {doc.title}\n"
        f"Azienda: {doc.company.name if doc.company else 'N/A'}\n"
        f"Reparto: {doc.department.name if doc.department else 'N/A'}\n"
    )
    send_email(subject, [doc.uploader_email, user_email], body)

def get_or_create_folder(name, parent_id=None):
    """
    Ottiene o crea una cartella su Google Drive.

    Args:
        name (str): Nome della cartella.
        parent_id (str, optional): ID della cartella padre.

    Returns:
        str: ID della cartella trovata o creata.
    """
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']

    folder_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        folder_metadata['parents'] = [parent_id]
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def upload_file_to_drive(filepath, filename, folder_id):
    """
    Carica un file su Google Drive.

    Args:
        filepath (str): Percorso locale del file.
        filename (str): Nome del file su Drive.
        folder_id (str): ID della cartella Drive.

    Returns:
        str: ID del file caricato su Drive.
    """
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    media = MediaFileUpload(filepath, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def save_file_and_upload_to_drive(file_storage, company_name, department_name):
    """
    Salva un file localmente e lo carica su Google Drive.

    Args:
        file_storage (FileStorage): Il file da salvare.
        company_name (str): Nome azienda.
        department_name (str): Nome reparto.

    Returns:
        tuple: (new_filename, local_path, drive_file_id)
    """
    filename = secure_filename(file_storage.filename)
    ext = os.path.splitext(filename)[1]
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    new_filename = f"{company_name}_{department_name}_{current_user.username}_{timestamp}{ext}"

    # Percorso locale
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], company_name, department_name)
    os.makedirs(folder_path, exist_ok=True)
    local_path = os.path.join(folder_path, new_filename)
    file_storage.save(local_path)

    # Upload su Drive
    root_folder_id = os.getenv('DRIVE_ROOT_FOLDER_ID')
    company_folder_id = get_or_create_folder(company_name, root_folder_id)
    department_folder_id = get_or_create_folder(department_name, company_folder_id)
    drive_file_id = upload_file_to_drive(local_path, new_filename, department_folder_id)

    return new_filename, local_path, drive_file_id

# === Routes ===

@app.route('/')
def index():
    quotes = [
        "Chi condivide, moltiplica.",
        "Organizza oggi, risparmia domani.",
        "La conoscenza è potere, la condivisione è progresso.",
        "Documenti sicuri, azienda più agile.",
        "Ogni file condiviso è un ostacolo in meno.",
        "Ordine digitale, mente libera.",
        "Un documento organizzato è mezzo lavoro fatto.",
        "Semplificare i processi è potenziare le persone.",
        "Archiviazione intelligente, collaborazione efficace.",
        "Dati accessibili, decisioni migliori.",
        "Condividere responsabilmente è costruire fiducia.",
        "Digitalizzare è il primo passo per migliorare."
    ]
    today = datetime.now().strftime("%d/%m/%Y")
    return render_template('index.html', quote=random.choice(quotes), today=today)

@app.before_request
def before_request():
    app.logger.info(f"Before request - User: {current_user.get_id()}, Authenticated: {current_user.is_authenticated}")

    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)
    session.modified = True

    last_activity = session.get('last_activity')
    now = datetime.utcnow()

    if last_activity:
        elapsed = (now - last_activity).total_seconds()
        app.logger.info(f"Session last_activity: {last_activity}, elapsed seconds: {elapsed}")
        if elapsed > 1800:  # 30 minuti
            app.logger.info("Session timeout: logging out user.")
            logout_user()
            flash('Sessione scaduta, effettua di nuovo il login.', 'warning')
            return redirect(url_for('auth.login'))

    session['last_activity'] = now

@app.route('/upload_to_drive', methods=['GET', 'POST'])
@login_required
def upload_to_drive():
    if request.method == 'POST':
        file = request.files.get('file')
        title = request.form.get('title')
        visibility = request.form.get('visibility')
        password = request.form.get('password') if visibility == 'protetto' else None
        shared_email = request.form.get('shared_email') if visibility == 'condividi' else None

        if not file or not title:
            flash("⚠️ File e titolo sono obbligatori", "danger")
            return redirect(url_for('upload_to_drive'))

        if not allowed_file(file.filename):
            flash("❌ Estensione file non valida", "danger")
            return redirect(url_for('upload_to_drive'))

        if app.config.get('TESTING'):
            upload_to_drive = False
        else:
            upload_to_drive = request.form.get('upload_to_drive', 'true') == 'true'

        if upload_to_drive:
            new_filename, local_path, drive_file_id = save_file_and_upload_to_drive(
                file, current_user.companies[0].name if current_user.companies else 'N/A', current_user.departments[0].name if current_user.departments else 'N/A'
            )
        else:
            new_filename = secure_filename(file.filename)
            ext = os.path.splitext(new_filename)[1]
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            new_filename = f"{current_user.username}_{timestamp}{ext}"
            local_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.username, new_filename)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            file.save(local_path)
            drive_file_id = None # No upload to Drive in this case

        doc = Document(
            title=title,
            description=request.form.get('description'),
            note=request.form.get('note'),
            filename=new_filename,
            original_filename=file.filename,
            uploader_email=current_user.email,
            user_id=current_user.id,
            company_id=current_user.companies[0].id if current_user.companies else None,
            department_id=current_user.departments[0].id if current_user.departments else None,
            visibility=visibility,
            shared_email=shared_email,
            drive_file_id=drive_file_id,
            created_at=datetime.utcnow()
        )
        try:
            db.session.add(doc)
            db.session.flush()
            
            # === CLASSIFICAZIONE AI DEL DOCUMENTO ===
            try:
                from services.ai_classifier import classifica_e_processa_documento
                classifica_e_processa_documento(doc)
            except Exception as e:
                app.logger.error(f"Errore classificazione AI: {e}")
            
            db.session.commit()
            if upload_to_drive:
                notify_upload(doc)
            flash("✅ Documento caricato con successo", "success")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Errore salvataggio documento: {e}")
            flash("❌ Errore durante il salvataggio del documento.", "danger")

        return redirect(url_for('user.my_documents'))

    companies = Company.query.all()
    departments = Department.query.all()
    return render_template("upload.html", all_companies=companies, all_departments=departments)

# === Avvio app ===
if __name__ == '__main__':
    app.run(port=5001)

# === Upload manuale documenti (non GCS/Drive) ===
# @app.route('/local_upload', methods=['GET', 'POST'])
# @login_required
# def local_upload():
#     if request.method == 'POST':
#         file = request.files.get('file')
#         title = request.form.get('title')
#         description = request.form.get('description')
#         note = request.form.get('note')
#         visibility = request.form.get('visibility')
#         password = request.form.get('password') if visibility == 'protetto' else None
#         shared_email = request.form.get('shared_email') if visibility == 'condividi' else None
#
#         target_companies = request.form.getlist('target_companies')
#         target_departments = request.form.getlist('target_departments')
#
#         if not file or not title or not target_companies or not target_departments:
#             flash("⚠️ File, titolo, azienda e reparto sono obbligatori", "danger")
#             return redirect(url_for('local_upload'))
#
#         allowed_extensions_local = {'pdf', 'docx', 'xlsx', 'png', 'jpg', 'jpeg', 'txt'}
#         if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions_local:
#             flash("❌ Estensione file non valida", "danger")
#             return redirect(url_for('local_upload'))
#
#         original_name = secure_filename(file.filename)
#         name, ext = os.path.splitext(original_name)
#
#         try:
#             for company_id in target_companies:
#                 for department_id in target_departments:
#                     unique_filename = f"{name}_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:8]}{ext}"
#                     save_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(company_id), str(department_id))
#                     os.makedirs(save_dir, exist_ok=True)
#                     save_path = os.path.join(save_dir, unique_filename)
#                     file.stream.seek(0)  # reset per più salvataggi
#                     file.save(save_path)
#
#                     doc = Document(
#                         title=title,
#                         description=description,
#                         note=note,
#                         filename=unique_filename,
#                         original_filename=original_name,
#                         uploader_email=current_user.email,
#                         user_id=current_user.id,
#                         company_id=company_id,
#                         department_id=department_id,
#                         visibility=visibility,
#                         shared_email=shared_email,
#                         password=bcrypt.generate_password_hash(password).decode('utf-8') if password else None,
#                         created_at=datetime.utcnow()
#                     )
#
#                     db.session.add(doc)
#                     notify_upload(doc)
#
#             db.session.commit()
#             app.logger.info(f"[UPLOAD] Utente {current_user.username} ha caricato il documento '{title}'")
#             flash("✅ Documento caricato con successo", "success")
#
#         except Exception as e:
#             db.session.rollback()
#             app.logger.error(f"[UPLOAD] Errore salvataggio documento locale: {e}")
#             flash("❌ Errore durante il salvataggio del documento.", "danger")
#
#         return redirect(url_for('user.my_documents'))
#
#     companies = Company.query.all()
#     departments = Department.query.all()
#     return render_template("upload.html", all_companies=companies, all_departments=departments)

# === Download file con verifica approvazione ===
@app.route('/download_file/<filename>')
@login_required
def download_file(filename):
    """
    Download di un file con verifica che sia approvato da Admin e CEO.
    
    Args:
        filename (str): Nome del file da scaricare.
        
    Returns:
        file: Il file se approvato, altrimenti redirect con errore.
    """
    # Trova il documento dal filename
    doc = Document.query.filter_by(filename=filename).first()
    if not doc:
        flash("❌ Documento non trovato", "danger")
        return redirect(url_for('index'))
    
    # Verifica che il documento sia approvato da Admin e CEO
    if not (doc.validazione_admin and doc.validazione_ceo):
        # Log dell'accesso negato
        audit_log = AuditLog(
            user_id=current_user.id,
            document_id=doc.id,
            azione='accesso_negato',
            note=f'Tentativo di download documento non ancora approvato: "{doc.title or doc.original_filename}"'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash("⛔ Documento non ancora approvato da Admin e CEO.", "warning")
        return redirect(url_for('index'))
    
    # Verifica che l'utente abbia accesso al documento
    if not current_user.is_admin and not current_user.is_ceo:
        # Per utenti normali, verifica che siano l'uploader o abbiano accesso autorizzato
        if doc.user_id != current_user.id:
            # Verifica se l'utente ha accesso autorizzato
            authorized = AuthorizedAccess.query.filter_by(
                user_id=current_user.id,
                document_id=doc.id
            ).first()
            if not authorized:
                # Log dell'accesso non autorizzato
                audit_log = AuditLog(
                    user_id=current_user.id,
                    document_id=doc.id,
                    azione='accesso_negato',
                    note=f'Accesso non autorizzato al documento: "{doc.title or doc.original_filename}"'
                )
                db.session.add(audit_log)
                db.session.commit()
                
                flash("🚫 Accesso non autorizzato al documento", "danger")
                return redirect(url_for('index'))
    
    # Verifica che il file esista
    local_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.company.name, doc.department.name, doc.filename)
    if not os.path.exists(local_path):
        flash("❌ File non trovato sul server", "danger")
        return redirect(url_for('index'))
    
    # Log del download
    log = DocumentActivityLog(
        document_id=doc.id,
        user_id=current_user.id,
        action='download',
        note=f'Download effettuato da {current_user.username}'
    )
    db.session.add(log)
    
    # Audit log per il download
    audit_log = AuditLog(
        user_id=current_user.id,
        document_id=doc.id,
        azione='download',
        note=f'Download documento "{doc.title or doc.original_filename}"'
    )
    db.session.add(audit_log)
    db.session.commit()
    
    # Log della visualizzazione
    view_log = AuditLog(
        user_id=current_user.id,
        document_id=doc.id,
        azione='visualizzazione',
        note=f'Visualizzazione documento "{doc.title or doc.original_filename}"'
    )
    db.session.add(view_log)
    db.session.commit()
    
    return send_file(local_path, as_attachment=True)

# === Download sicuro per ospiti ===
@app.route('/guest_secure_download')
def guest_secure_download():
    guest_email = session.get('guest_email')
    doc_id = session.get('guest_doc_id')

    if not guest_email or not doc_id:
        flash("❌ Accesso non autorizzato o sessione scaduta", "danger")
        return redirect(url_for('guest.guest_access'))

    doc = Document.query.get(doc_id)
    if not doc:
        flash("❌ Documento non trovato", "danger")
        return redirect(url_for('guest.guest_access'))

    if doc.expiry_date and doc.expiry_date < datetime.utcnow():
        flash("Documento scaduto, download non consentito", "warning")
        return redirect(url_for('guest.guest_access'))

    valid_emails = [e.strip().lower() for e in (doc.shared_email or '').split(';')]
    if guest_email.lower() not in valid_emails:
        flash("🚫 Email non autorizzata", "danger")
        return redirect(url_for('guest.guest_access'))

    local_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.company.name, doc.department.name, doc.filename)
    if not os.path.exists(local_path):
        flash("❌ File non trovato sul server", "danger")
        return redirect(url_for('guest.guest_access'))

    log = AdminLog(
        action='guest_download',
        timestamp=datetime.utcnow(),
        performed_by=guest_email,
        document_id=doc.id
    )
    db.session.add(log)
    db.session.commit()

    return send_file(local_path, as_attachment=True)

# === Registrazione ospite ===
@app.route('/guest_register', methods=['GET', 'POST'])
def guest_register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm', '').strip()

        if not email or not password or not confirm:
            flash("Tutti i campi sono obbligatori.", "danger")
            return render_template('guest_register.html')

        if password != confirm:
            flash("Le password non coincidono.", "danger")
            return render_template('guest_register.html')

        if not is_secure_password(password):
            flash("La password non è sufficientemente sicura.", "danger")
            return render_template('guest_register.html')

        if User.query.filter_by(email=email).first():
            flash("Utente già esistente con questa email.", "danger")
            return render_template('guest_register.html')

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password=hashed_pw, username=email, department="Guest")
        db.session.add(new_user)
        db.session.commit()
        flash("Registrazione completata. Ora puoi accedere.", "success")
        return redirect(url_for('guest.guest_access'))

    return render_template('guest_register.html')

# === Gestione Dati Sicuri (Password Criptate) ===
@app.route('/admin/secure_data', methods=['GET', 'POST'])
@login_required
def admin_secure_data():
    if not current_user.is_admin:
        flash("Accesso negato.", "danger")
        return redirect(url_for('user.dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        password = request.form.get('password')
        url_data = request.form.get('url')
        notes = request.form.get('notes')

        if not title or not password:
            flash("Titolo e password sono obbligatori.", "danger")
            return redirect(url_for('admin_secure_data'))

        encrypted_password = fernet.encrypt(password.encode())

        new_entry = PasswordLink(
            title=title,
            encrypted_password=encrypted_password,
            url=url_data,
            notes=notes,
            created_by_id=current_user.id
        )
        db.session.add(new_entry)
        db.session.commit()
        flash("✅ Dati salvati in modo sicuro.", "success")
        return redirect(url_for('admin_secure_data'))

    entries = PasswordLink.query.filter_by(created_by_id=current_user.id).all()
    return render_template('admin_secure_data.html', entries=entries)

# === Visualizza Password Decriptata ===
@app.route('/admin/secure_data/<int:entry_id>/view_password')
@login_required
def admin_view_secure_password(entry_id):
    entry = PasswordLink.query.get_or_404(entry_id)
    if not current_user.is_admin and entry.created_by_id != current_user.id:
        flash("Accesso negato.", "danger")
        return redirect(url_for('admin_secure_data'))

    try:
        decrypted_password = fernet.decrypt(entry.encrypted_password).decode()
    except Exception as e:
        app.logger.error(f"Errore nella decrittazione: {e}")
        flash("Errore nel recupero della password.", "danger")
        return redirect(url_for('admin_secure_data'))

    return render_template('admin_view_password.html', entry=entry, password=decrypted_password)

# === Elimina Dato Sicuro ===
@app.route('/admin/secure_data/<int:entry_id>/delete', methods=['POST'])
@login_required
def admin_delete_secure_data(entry_id):
    entry = PasswordLink.query.get_or_404(entry_id)
    if not current_user.is_admin and entry.created_by_id != current_user.id:
        flash("Accesso negato.", "danger")
        return redirect(url_for('admin_secure_data'))
    try:
        db.session.delete(entry)
        db.session.commit()
        flash("✅ Voce eliminata con successo.", "success")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Errore durante eliminazione: {e}")
        flash("Errore durante l'eliminazione della voce.", "danger")
    return redirect(url_for('admin_secure_data'))

from flask_wtf.csrf import CSRFError

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    app.logger.warning(f"❌ CSRF error: {e.description}")
    flash("❌ Errore di sicurezza (CSRF). Riprova a fare login.", "danger")
    return redirect(url_for("auth.login"))

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def page_not_found(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500
