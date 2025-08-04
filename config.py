class Config:
    SECRET_KEY = 'questa-è-una-chiave-super-segreta-123456'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///gestione.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465               # Porta 465 per SSL
    MAIL_USE_TLS = False          # Disattivato se usi SSL
    MAIL_USE_SSL = True           # Attivato per porta 465
    MAIL_USERNAME = 'noreply@mercurysurgelati.org'
    MAIL_PASSWORD = 'yeoq fqlr khdc vjnz'
    MAIL_DEFAULT_SENDER = 'noreply@mercurysurgelati.org'

    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    WTF_CSRF_TIME_LIMIT = 3600

    # Cookie di sessione configurati per dominio e sicurezza
    SESSION_COOKIE_DOMAIN = '.mercurysurgelati.org'
    SESSION_COOKIE_SECURE = True        # Metti True se usi HTTPS, altrimenti False
    SESSION_COOKIE_SAMESITE = 'Lax'

    # ATTENZIONE: Non usare valori hardcoded in produzione! Usa sempre variabili d'ambiente per SECRET_KEY e MAIL_PASSWORD.


