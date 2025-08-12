# 📁 DOCS Mercury – Modulo gestione documentale per Mercury Surgelati

> **Ecosistema SYNTHIA** - Sistema integrato di gestione documentale intelligente

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com)
[![AI](https://img.shields.io/badge/AI-Jack%20Synthia-orange.svg)](https://github.com/synthia-ai)
[![Status](https://img.shields.io/badge/Status-Production-brightgreen.svg)](https://138.68.80.169)

## 📝 Descrizione

DOCS Mercury è il modulo di gestione documentale intelligente per **Mercury Surgelati**, parte dell'ecosistema SYNTHIA. Il sistema integra funzionalità avanzate di AI con gestione tradizionale dei documenti.

### 🧠 Funzionalità AI (Jack Synthia)

- **Auto-verifica contenuto documenti** - Analisi automatica PDF/Word per compliance
- **Suggerimento archiviazione AI** - Suggerimenti intelligenti per cartelle e tag
- **Risposta automatica accesso** - Generazione AI di risposte per richieste accesso
- **Alert comportamenti sospetti** - Rilevamento automatico attività anomale
- **Dashboard AI documentale** - Visualizzazione strategica con indicatori AI
- **Report mensili CEO** - Generazione automatica report PDF per direzione

### 👥 Gestione Utenti

- **CEO e Admin Mercury** - Accesso completo con dashboard avanzate
- **Gestione Guest** - Assegnazione documenti, scadenze, permessi temporanei
- **Sistema di ruoli** - Controllo accessi granulare (user, admin, ceo, guest)
- **Audit logging** - Tracciamento completo di tutte le attività

### 🔄 Integrazione Sistema

- **Sincronizzazione CEO** - Integrazione con sistema centrale SYNTHIA
- **API esterne** - Connessione con FocusMe AI (64.226.70.28)
- **UX/UI coerente** - Stessa interfaccia degli altri moduli DOCS
- **Modulo Quality** - Gestione certificazioni, audit, azioni correttive

## 🚀 Installazione Rapida

```bash
# Clone repository
git clone https://github.com/synthia-ai/docs-mercury.git
cd docs-mercury

# Setup ambiente virtuale
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# oppure
.venv\Scripts\activate     # Windows

# Installazione dipendenze
pip install -r requirements.txt

# Configurazione database
flask db upgrade

# Avvio server
flask run --host=0.0.0.0 --port=5000
```

## 📋 Prerequisiti

- **Python 3.8+**
- **PostgreSQL 12+** (o SQLite per sviluppo)
- **Node.js 14+** (per build frontend)
- **Redis** (opzionale, per cache)

## ⚙️ Configurazione

### Variabili Ambiente

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/docs_mercury
SECRET_KEY=your-secret-key-here

# AI Services
FOCUSME_AI_URL=https://64.226.70.28
OPENAI_API_KEY=your-openai-key

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# File Upload
UPLOAD_FOLDER=/var/www/uploads
MAX_CONTENT_LENGTH=16777216  # 16MB
```

### Configurazione Avanzata

Vedi [docs/configurazione.md](docs/configurazione.md) per dettagli completi.

## 🧪 Test

```bash
# Test unitari
python -m pytest tests/

# Test AI specifici
python test_auto_verifica_documenti.py
python test_ai_access_response.py
python test_ai_archive_suggestion.py

# Test integrazione
python -m pytest tests/integration/

# Coverage
coverage run -m pytest
coverage report
```

## 📚 Documentazione API

### Endpoint Principali

```bash
# Documenti
GET    /api/documents                    # Lista documenti
POST   /api/documents                    # Upload documento
GET    /api/documents/{id}              # Dettagli documento
PUT    /api/documents/{id}              # Aggiorna documento
DELETE /api/documents/{id}              # Elimina documento

# AI Intelligence
GET    /docs/ai/verifica/{id}           # Auto-verifica documento
GET    /docs/ai/suggerisci-cartella/{id} # Suggerimento archiviazione
POST   /docs/ai/richiesta-accesso/{id}/rispondi # Risposta AI accesso

# Dashboard
GET    /api/jack/docs/dashboard/{user_id} # Dashboard AI
GET    /api/jack/docs/report_ceo/{year}/{month} # Report CEO

# Quality Module
GET    /quality/certificazioni          # Lista certificazioni
POST   /quality/documenti               # Upload documento qualità
GET    /quality/audit                   # Lista audit
```

Vedi [docs/api.md](docs/api.md) per documentazione completa delle API.

## 🏗️ Architettura

```
docs-mercury/
├── app.py                 # Entry point Flask
├── models.py             # Modelli database
├── routes/               # API routes
│   ├── admin_routes.py
│   ├── document_intelligence_routes.py
│   ├── quality_routes.py
│   └── docs_reports.py
├── services/             # Business logic
│   └── document_intelligence.py
├── templates/            # Frontend templates
│   └── admin/
├── static/              # Assets statici
├── tests/               # Test suite
├── docs/                # Documentazione
└── requirements.txt     # Dipendenze Python
```

## 🔧 Sviluppo

### Struttura Database

```sql
-- Tabelle principali
documents              # Documenti caricati
users                  # Utenti sistema
companies              # Aziende
departments            # Reparti

-- Tabelle AI
document_ai_flags      # Flag AI documenti
ai_archive_suggestions # Suggerimenti archiviazione
ai_alerts             # Alert comportamenti sospetti
ai_replies            # Risposte AI automatiche

-- Tabelle Quality
certificazioni         # Certificazioni qualità
audit_qualita         # Audit qualità
azioni_correttive     # Azioni correttive
```

### Comandi Utili

```bash
# Database
flask db migrate -m "Description"
flask db upgrade
flask db downgrade

# Shell
flask shell

# Logs
tail -f logs/app.log

# Backup
pg_dump docs_mercury > backup.sql
```

## 🚨 Troubleshooting

### Problemi Comuni

1. **Errore database connessione**
   ```bash
   # Verifica connessione
   flask db current
   ```

2. **AI non funziona**
   ```bash
   # Test connessione FocusMe AI
   curl https://64.226.70.28/api/health
   ```

3. **Upload file fallisce**
   ```bash
   # Verifica permessi cartella
   ls -la /var/www/uploads/
   chmod 755 /var/www/uploads/
   ```

4. **Email non inviate**
   ```bash
   # Test configurazione email
   flask test-email
   ```

## 📊 Monitoraggio

### Log Files

```bash
# Log applicazione
tail -f logs/app.log

# Log errori
tail -f logs/error.log

# Log AI
tail -f logs/ai.log
```

### Metriche

- **Documenti caricati/giorno**
- **Suggerimenti AI accettati**
- **Alert generati**
- **Performance API**

## 🤝 Contribuire

1. Fork del repository
2. Crea branch feature (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri Pull Request

## 📄 Licenza

Questo progetto è sotto licenza MIT. Vedi [LICENSE](LICENSE) per dettagli.

## 📞 Supporto

- **Email**: support@synthia-ai.com
- **Documentazione**: [docs.synthia-ai.com](https://docs.synthia-ai.com)
- **Issues**: [GitHub Issues](https://github.com/synthia-ai/docs-mercury/issues)

## 🔗 Link Utili

- [Ecosistema SYNTHIA](https://synthia-ai.com)
- [FocusMe AI](https://64.226.70.28)
- [Mercury Surgelati](https://mercury-surgelati.com)
- [Documentazione API](docs/api.md)

---

**Versione**: 2.0.0  
**Ultimo aggiornamento**: 2025-01-27  
**Mantenuto da**: Team SYNTHIA AI 