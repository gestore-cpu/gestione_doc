# ⚙️ Guida Configurazione DOCS Mercury

> Configurazione completa del modulo DOCS Mercury per produzione e sviluppo

## 📋 Panoramica Configurazione

Il modulo DOCS Mercury utilizza un sistema di configurazione basato su variabili d'ambiente e file di configurazione. Questa guida copre tutti i parametri disponibili.

## 🔧 Variabili Ambiente

### Database Configuration

```bash
# PostgreSQL (Produzione)
DATABASE_URL=postgresql://username:password@localhost:5432/docs_mercury

# SQLite (Sviluppo)
DATABASE_URL=sqlite:///docs_mercury.db

# MySQL (Alternativa)
DATABASE_URL=mysql://username:password@localhost/docs_mercury
```

**Parametri Database:**
- `DATABASE_URL`: URL connessione database
- `DB_POOL_SIZE`: Dimensione pool connessioni (default: 10)
- `DB_MAX_OVERFLOW`: Overflow massimo pool (default: 20)
- `DB_POOL_TIMEOUT`: Timeout pool in secondi (default: 30)

### Sicurezza

```bash
# Chiave segreta Flask
SECRET_KEY=your-super-secret-key-here

# Chiave JWT
JWT_SECRET_KEY=your-jwt-secret-key

# Salt per password
PASSWORD_SALT=your-password-salt

# Session timeout (secondi)
SESSION_TIMEOUT=3600

# Max login attempts
MAX_LOGIN_ATTEMPTS=5
```

### AI Services

```bash
# FocusMe AI
FOCUSME_AI_URL=https://64.226.70.28
FOCUSME_AI_KEY=your-focusme-api-key

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=2000

# AI Configuration
AI_ENABLED=true
AI_CONFIDENCE_THRESHOLD=0.7
AI_MAX_RETRIES=3
AI_TIMEOUT=30
```

### Email Configuration

```bash
# SMTP Settings
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Email Templates
MAIL_DEFAULT_SENDER=noreply@mercury-surgelati.com
MAIL_REPLY_TO=support@mercury-surgelati.com

# Email Limits
MAIL_RATE_LIMIT=100  # emails per hour
MAIL_BATCH_SIZE=10    # emails per batch
```

### File Upload

```bash
# Upload Settings
UPLOAD_FOLDER=/var/www/uploads
MAX_CONTENT_LENGTH=16777216  # 16MB
ALLOWED_EXTENSIONS=pdf,doc,docx,xls,xlsx,ppt,pptx,txt,jpg,jpeg,png

# File Processing
ENABLE_PDF_PROCESSING=true
ENABLE_OCR=false
MAX_FILE_SIZE=16777216
COMPRESSION_ENABLED=true
```

### Redis (Cache)

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# Cache Settings
CACHE_TYPE=redis
CACHE_DEFAULT_TIMEOUT=300
CACHE_KEY_PREFIX=docs_mercury
```

### Logging

```bash
# Log Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
LOG_MAX_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# AI Logging
AI_LOG_ENABLED=true
AI_LOG_FILE=logs/ai.log
AI_LOG_LEVEL=DEBUG
```

## 📁 File di Configurazione

### config.py

```python
import os
from datetime import timedelta

class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 20)),
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 30))
    }
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    PASSWORD_SALT = os.environ.get('PASSWORD_SALT')
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', 3600))
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    
    # AI Services
    FOCUSME_AI_URL = os.environ.get('FOCUSME_AI_URL')
    FOCUSME_AI_KEY = os.environ.get('FOCUSME_AI_KEY')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4')
    OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', 2000))
    AI_ENABLED = os.environ.get('AI_ENABLED', 'true').lower() == 'true'
    AI_CONFIDENCE_THRESHOLD = float(os.environ.get('AI_CONFIDENCE_THRESHOLD', 0.7))
    AI_MAX_RETRIES = int(os.environ.get('AI_MAX_RETRIES', 3))
    AI_TIMEOUT = int(os.environ.get('AI_TIMEOUT', 30))
    
    # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    MAIL_REPLY_TO = os.environ.get('MAIL_REPLY_TO')
    MAIL_RATE_LIMIT = int(os.environ.get('MAIL_RATE_LIMIT', 100))
    MAIL_BATCH_SIZE = int(os.environ.get('MAIL_BATCH_SIZE', 10))
    
    # File Upload
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16777216))
    ALLOWED_EXTENSIONS = os.environ.get('ALLOWED_EXTENSIONS', 'pdf,doc,docx,xls,xlsx,ppt,pptx,txt,jpg,jpeg,png').split(',')
    ENABLE_PDF_PROCESSING = os.environ.get('ENABLE_PDF_PROCESSING', 'true').lower() == 'true'
    ENABLE_OCR = os.environ.get('ENABLE_OCR', 'false').lower() == 'true'
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 16777216))
    COMPRESSION_ENABLED = os.environ.get('COMPRESSION_ENABLED', 'true').lower() == 'true'
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL')
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'redis')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    CACHE_KEY_PREFIX = os.environ.get('CACHE_KEY_PREFIX', 'docs_mercury')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    LOG_MAX_SIZE = int(os.environ.get('LOG_MAX_SIZE', 10485760))
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    AI_LOG_ENABLED = os.environ.get('AI_LOG_ENABLED', 'true').lower() == 'true'
    AI_LOG_FILE = os.environ.get('AI_LOG_FILE', 'logs/ai.log')
    AI_LOG_LEVEL = os.environ.get('AI_LOG_LEVEL', 'DEBUG')

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

### .env.example

```bash
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/docs_mercury
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30

# Security
SECRET_KEY=your-super-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key
PASSWORD_SALT=your-password-salt
SESSION_TIMEOUT=3600
MAX_LOGIN_ATTEMPTS=5

# AI Services
FOCUSME_AI_URL=https://64.226.70.28
FOCUSME_AI_KEY=your-focusme-api-key
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=2000
AI_ENABLED=true
AI_CONFIDENCE_THRESHOLD=0.7
AI_MAX_RETRIES=3
AI_TIMEOUT=30

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@mercury-surgelati.com
MAIL_REPLY_TO=support@mercury-surgelati.com
MAIL_RATE_LIMIT=100
MAIL_BATCH_SIZE=10

# File Upload
UPLOAD_FOLDER=/var/www/uploads
MAX_CONTENT_LENGTH=16777216
ALLOWED_EXTENSIONS=pdf,doc,docx,xls,xlsx,ppt,pptx,txt,jpg,jpeg,png
ENABLE_PDF_PROCESSING=true
ENABLE_OCR=false
MAX_FILE_SIZE=16777216
COMPRESSION_ENABLED=true

# Redis
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0
CACHE_TYPE=redis
CACHE_DEFAULT_TIMEOUT=300
CACHE_KEY_PREFIX=docs_mercury

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
AI_LOG_ENABLED=true
AI_LOG_FILE=logs/ai.log
AI_LOG_LEVEL=DEBUG
```

## 🔐 Configurazione Sicurezza

### Password Policy

```python
# Password requirements
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_DIGITS = True
PASSWORD_REQUIRE_SPECIAL = True
PASSWORD_HISTORY_COUNT = 5
PASSWORD_EXPIRY_DAYS = 90
```

### Rate Limiting

```python
# Rate limiting configuration
RATE_LIMIT_DEFAULT = "100 per minute"
RATE_LIMIT_STORAGE_URL = "redis://localhost:6379"
RATE_LIMIT_STRATEGY = "fixed-window"
RATE_LIMIT_HEADERS_ENABLED = True
```

### CORS Configuration

```python
# CORS settings
CORS_ORIGINS = [
    "http://localhost:3000",
    "https://138.68.80.169",
    "https://mercury-surgelati.com"
]
CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS = ["Content-Type", "Authorization"]
CORS_EXPOSE_HEADERS = ["Content-Range", "X-Total-Count"]
```

## 🧠 Configurazione AI

### Jack Synthia Settings

```python
# Jack Synthia configuration
JACK_SYNTHIA_ENABLED = True
JACK_SYNTHIA_MODEL = "gpt-4"
JACK_SYNTHIA_MAX_TOKENS = 2000
JACK_SYNTHIA_TEMPERATURE = 0.7
JACK_SYNTHIA_TOP_P = 0.9
JACK_SYNTHIA_FREQUENCY_PENALTY = 0.0
JACK_SYNTHIA_PRESENCE_PENALTY = 0.0

# AI Analysis settings
AI_ANALYSIS_ENABLED = True
AI_DOCUMENT_VERIFICATION = True
AI_ARCHIVE_SUGGESTION = True
AI_ACCESS_RESPONSE = True
AI_BEHAVIOR_ALERTS = True
AI_DASHBOARD_ENABLED = True
AI_REPORT_GENERATION = True

# AI Confidence thresholds
AI_CONFIDENCE_HIGH = 0.8
AI_CONFIDENCE_MEDIUM = 0.6
AI_CONFIDENCE_LOW = 0.4
```

### FocusMe AI Integration

```python
# FocusMe AI configuration
FOCUSME_AI_BASE_URL = "https://64.226.70.28"
FOCUSME_AI_TIMEOUT = 30
FOCUSME_AI_RETRIES = 3
FOCUSME_AI_RETRY_DELAY = 1

# FocusMe AI endpoints
FOCUSME_AI_ENDPOINTS = {
    'preferences': '/api/utente/{user_id}/preferenze',
    'branding': '/api/jack/branding/{user_id}',
    'messages': '/api/jack/docs/messages/{user_id}',
    'tasks': '/api/jack/docs/tasks/{user_id}',
    'suggestions': '/api/jack/docs/suggestions/{user_id}',
    'report': '/api/jack/docs/report'
}
```

## 📊 Configurazione Monitoraggio

### Logging Configuration

```python
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(app):
    # Create logs directory
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Application logging
    if not app.debug:
        file_handler = RotatingFileHandler(
            app.config['LOG_FILE'],
            maxBytes=app.config['LOG_MAX_SIZE'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        file_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.addHandler(file_handler)
    
    # AI logging
    if app.config['AI_LOG_ENABLED']:
        ai_handler = RotatingFileHandler(
            app.config['AI_LOG_FILE'],
            maxBytes=app.config['LOG_MAX_SIZE'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        ai_handler.setFormatter(logging.Formatter(app.config['LOG_FORMAT']))
        ai_handler.setLevel(getattr(logging, app.config['AI_LOG_LEVEL']))
        
        ai_logger = logging.getLogger('ai')
        ai_logger.addHandler(ai_handler)
        ai_logger.setLevel(getattr(logging, app.config['AI_LOG_LEVEL']))
```

### Metrics Configuration

```python
# Metrics configuration
METRICS_ENABLED = True
METRICS_INTERVAL = 60  # seconds
METRICS_RETENTION_DAYS = 30

# Metrics to collect
METRICS_COLLECT = [
    'documents_uploaded',
    'ai_suggestions_generated',
    'ai_suggestions_accepted',
    'alerts_generated',
    'api_requests',
    'response_times',
    'error_rates'
]
```

## 🔄 Configurazione Backup

### Database Backup

```bash
#!/bin/bash
# backup-database.sh

BACKUP_DIR="/var/backups/docs-mercury"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="docs_mercury"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
pg_dump $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_backup_$DATE.sql.gz"
```

### File Backup

```bash
#!/bin/bash
# backup-files.sh

BACKUP_DIR="/var/backups/docs-mercury"
DATE=$(date +%Y%m%d_%H%M%S)
UPLOAD_DIR="/var/www/uploads"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup uploads
tar -czf $BACKUP_DIR/uploads_backup_$DATE.tar.gz -C $UPLOAD_DIR .

# Keep only last 30 days of backups
find $BACKUP_DIR -name "uploads_backup_*.tar.gz" -mtime +30 -delete

echo "File backup completed: uploads_backup_$DATE.tar.gz"
```

## 🚀 Configurazione Produzione

### Gunicorn Configuration

```python
# gunicorn.conf.py

bind = "127.0.0.1:5000"
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2
preload_app = True

# Logging
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
```

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/docs-mercury

upstream docs_mercury {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name 138.68.80.169;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name 138.68.80.169;

    ssl_certificate /etc/letsencrypt/live/138.68.80.169/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/138.68.80.169/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # File upload size
    client_max_body_size 16M;

    location / {
        proxy_pass http://docs_mercury;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /static {
        alias /var/www/gestione_doc/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads {
        alias /var/www/uploads;
        expires 1d;
        add_header Cache-Control "public";
    }
}
```

## ✅ Verifica Configurazione

### Test Script

```python
# test_config.py

import os
from app import create_app

def test_configuration():
    app = create_app()
    
    print("🔧 Testing Configuration...")
    
    # Test database
    try:
        from models import db
        db.engine.execute("SELECT 1")
        print("✅ Database connection: OK")
    except Exception as e:
        print(f"❌ Database connection: FAILED - {e}")
    
    # Test AI services
    if app.config['AI_ENABLED']:
        print("✅ AI services: ENABLED")
    else:
        print("⚠️ AI services: DISABLED")
    
    # Test email
    if app.config['MAIL_SERVER']:
        print("✅ Email configuration: OK")
    else:
        print("❌ Email configuration: MISSING")
    
    # Test file upload
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        print("✅ Upload folder: OK")
    else:
        print("❌ Upload folder: MISSING")
    
    # Test Redis
    if app.config['REDIS_URL']:
        try:
            import redis
            r = redis.from_url(app.config['REDIS_URL'])
            r.ping()
            print("✅ Redis connection: OK")
        except Exception as e:
            print(f"❌ Redis connection: FAILED - {e}")
    
    print("🎉 Configuration test completed!")

if __name__ == "__main__":
    test_configuration()
```

Esegui il test:

```bash
python test_config.py
```

---

**Ultimo aggiornamento**: 2025-01-27  
**Versione**: 2.0.0 