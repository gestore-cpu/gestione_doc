# 📋 Guida Installazione DOCS Mercury

> Guida completa per l'installazione e setup del modulo DOCS Mercury

## 🎯 Panoramica

Questa guida ti accompagnerà nell'installazione completa del modulo DOCS Mercury, parte dell'ecosistema SYNTHIA per Mercury Surgelati.

## 📋 Prerequisiti

### Sistema Operativo
- **Linux** (Ubuntu 20.04+ / CentOS 8+)
- **Windows** (Windows 10+ con WSL2)
- **macOS** (10.15+)

### Software Richiesto
```bash
# Python 3.8+
python3 --version

# PostgreSQL 12+
psql --version

# Node.js 14+ (per build frontend)
node --version

# Git
git --version

# Redis (opzionale)
redis-server --version
```

## 🚀 Installazione Passo-Passo

### 1. Clone Repository

```bash
# Clone del repository
git clone https://github.com/synthia-ai/docs-mercury.git
cd docs-mercury

# Verifica struttura
ls -la
```

### 2. Setup Ambiente Virtuale

```bash
# Crea ambiente virtuale
python3 -m venv .venv

# Attiva ambiente virtuale
# Linux/macOS:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate

# Verifica attivazione
which python
pip --version
```

### 3. Installazione Dipendenze

```bash
# Aggiorna pip
pip install --upgrade pip

# Installa dipendenze
pip install -r requirements.txt

# Verifica installazione
python -c "import flask, sqlalchemy, openai; print('✅ Dipendenze installate')"
```

### 4. Configurazione Database

```bash
# Crea database PostgreSQL
sudo -u postgres createdb docs_mercury

# Oppure con SQLite (solo sviluppo)
touch docs_mercury.db

# Configura variabili ambiente
export DATABASE_URL="postgresql://username:password@localhost/docs_mercury"
export SECRET_KEY="your-super-secret-key-here"

# Inizializza database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 5. Configurazione File

```bash
# Crea cartelle necessarie
mkdir -p uploads
mkdir -p logs
mkdir -p static/uploads

# Imposta permessi
chmod 755 uploads/
chmod 755 static/uploads/
chmod 644 logs/

# Crea file di configurazione
cp .env.example .env
```

### 6. Configurazione Variabili Ambiente

Crea/modifica il file `.env`:

```bash
# Database
DATABASE_URL=postgresql://username:password@localhost/docs_mercury
SECRET_KEY=your-super-secret-key-here

# AI Services
FOCUSME_AI_URL=https://64.226.70.28
OPENAI_API_KEY=your-openai-api-key

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# File Upload
UPLOAD_FOLDER=./uploads
MAX_CONTENT_LENGTH=16777216

# Redis (opzionale)
REDIS_URL=redis://localhost:6379

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 7. Setup Utenti Iniziali

```bash
# Avvia shell Flask
flask shell

# Nel shell Python:
from models import db, User
from werkzeug.security import generate_password_hash

# Crea utente admin
admin = User(
    username='admin',
    email='admin@mercury-surgelati.com',
    password=generate_password_hash('admin123'),
    role='admin',
    first_name='Admin',
    last_name='Mercury'
)
db.session.add(admin)

# Crea utente CEO
ceo = User(
    username='ceo',
    email='ceo@mercury-surgelati.com',
    password=generate_password_hash('ceo123'),
    role='ceo',
    first_name='CEO',
    last_name='Mercury'
)
db.session.add(ceo)

db.session.commit()
exit()
```

### 8. Test Installazione

```bash
# Test connessione database
flask db current

# Test server
flask run --host=0.0.0.0 --port=5000

# In altro terminale, test API
curl http://localhost:5000/api/health
```

## 🔧 Configurazione Produzione

### 1. Setup Nginx

```bash
# Installa Nginx
sudo apt update
sudo apt install nginx

# Crea configurazione
sudo nano /etc/nginx/sites-available/docs-mercury
```

Configurazione Nginx:

```nginx
server {
    listen 80;
    server_name 138.68.80.169;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/gestione_doc/static;
        expires 30d;
    }
}
```

```bash
# Abilita sito
sudo ln -s /etc/nginx/sites-available/docs-mercury /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 2. Setup Systemd Service

```bash
# Crea service file
sudo nano /etc/systemd/system/docs-mercury.service
```

Contenuto service:

```ini
[Unit]
Description=DOCS Mercury Flask Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/gestione_doc
Environment="PATH=/var/www/gestione_doc/.venv/bin"
Environment="FLASK_APP=app.py"
Environment="FLASK_ENV=production"
ExecStart=/var/www/gestione_doc/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Abilita e avvia service
sudo systemctl daemon-reload
sudo systemctl enable docs-mercury
sudo systemctl start docs-mercury
sudo systemctl status docs-mercury
```

### 3. Setup SSL (HTTPS)

```bash
# Installa Certbot
sudo apt install certbot python3-certbot-nginx

# Ottieni certificato
sudo certbot --nginx -d 138.68.80.169

# Test rinnovo automatico
sudo certbot renew --dry-run
```

## 🧪 Test Post-Installazione

### 1. Test Funzionalità Base

```bash
# Test database
flask db current

# Test upload file
curl -X POST -F "file=@test.pdf" http://localhost:5000/api/documents

# Test AI
python test_auto_verifica_documenti.py
python test_ai_access_response.py
python test_ai_archive_suggestion.py
```

### 2. Test API Endpoints

```bash
# Health check
curl http://localhost:5000/api/health

# Lista documenti
curl http://localhost:5000/api/documents

# Dashboard AI
curl http://localhost:5000/api/jack/docs/dashboard/1
```

### 3. Test Integrazione FocusMe AI

```bash
# Test connessione FocusMe AI
curl https://64.226.70.28/api/health

# Test preferenze Jack
curl https://64.226.70.28/api/utente/1/preferenze
```

## 🔍 Troubleshooting

### Problemi Comuni

#### 1. Errore Database
```bash
# Verifica connessione
psql -h localhost -U username -d docs_mercury

# Reset database
flask db downgrade base
flask db upgrade
```

#### 2. Errore Permessi File
```bash
# Fix permessi
sudo chown -R www-data:www-data /var/www/gestione_doc
sudo chmod -R 755 /var/www/gestione_doc/uploads
```

#### 3. Errore AI Services
```bash
# Verifica API key OpenAI
python -c "import openai; openai.api_key='your-key'; print('OK')"

# Test FocusMe AI
curl -v https://64.226.70.28/api/health
```

#### 4. Errore Email
```bash
# Test configurazione email
flask shell
from flask_mail import Mail, Message
# Test invio email
```

### Log Files

```bash
# Log applicazione
tail -f logs/app.log

# Log errori
tail -f logs/error.log

# Log Nginx
sudo tail -f /var/log/nginx/error.log

# Log systemd
sudo journalctl -u docs-mercury -f
```

## 📊 Monitoraggio

### Metriche da Monitorare

- **CPU Usage**: `htop`
- **Memory Usage**: `free -h`
- **Disk Usage**: `df -h`
- **Network**: `iftop`
- **Database**: `pg_stat_activity`

### Alert Setup

```bash
# Crea script monitoraggio
nano /usr/local/bin/monitor-docs-mercury.sh
```

```bash
#!/bin/bash
# Monitoraggio DOCS Mercury

# Check service status
if ! systemctl is-active --quiet docs-mercury; then
    echo "DOCS Mercury service down!" | mail -s "Alert" admin@mercury-surgelati.com
fi

# Check disk space
if [ $(df / | awk 'NR==2{print $5}' | sed 's/%//') -gt 90 ]; then
    echo "Disk space low!" | mail -s "Alert" admin@mercury-surgelati.com
fi

# Check database connections
if [ $(psql -t -c "SELECT count(*) FROM pg_stat_activity" | tr -d ' ') -gt 100 ]; then
    echo "Too many DB connections!" | mail -s "Alert" admin@mercury-surgelati.com
fi
```

```bash
chmod +x /usr/local/bin/monitor-docs-mercury.sh

# Aggiungi a crontab
crontab -e
# Aggiungi: */5 * * * * /usr/local/bin/monitor-docs-mercury.sh
```

## ✅ Verifica Finale

Dopo l'installazione, verifica che tutto funzioni:

1. **Accesso web**: http://138.68.80.169
2. **Login admin**: admin@mercury-surgelati.com / admin123
3. **Upload documento**: Test upload file
4. **AI features**: Test suggerimenti AI
5. **Dashboard**: Verifica dashboard AI
6. **Report**: Test generazione report CEO

## 📞 Supporto

Se incontri problemi durante l'installazione:

- **Email**: support@synthia-ai.com
- **Documentazione**: [docs.synthia-ai.com](https://docs.synthia-ai.com)
- **Issues**: [GitHub Issues](https://github.com/synthia-ai/docs-mercury/issues)

---

**Ultimo aggiornamento**: 2025-01-27  
**Versione**: 2.0.0 