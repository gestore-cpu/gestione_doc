# 📊 Sistema Report CEO Mensile Automatico

## 🎯 Panoramica

Il sistema di report CEO mensile automatico genera PDF periodici contenenti informazioni critiche per il CEO di Mercury Surgelati, inclusi invii PDF sensibili, alert AI attivi e eventi di audit trail.

## 🚀 Funzionalità Principali

### 📄 Contenuto del Report
- **Invii PDF Sensibili**: Lista degli invii PDF che hanno attivato criteri di sensibilità
- **Alert AI Attivi**: Alert AI con livello alto o critico
- **Eventi Audit Trail**: Modifiche permessi, gestione documenti, download massivi, modifiche utenti

### ⚙️ Criteri di Sensibilità per PDF
1. **Mittente Admin**: Invii effettuati da utenti admin
2. **Alert AI Alto/Critico**: Destinatari con alert AI di livello alto o critico
3. **Guest Scadenza**: Guest con scadenza accesso < 3 giorni
4. **Email Esterna**: Destinatari con email non aziendale (@mercurysurgelati.org)

### 🤖 Generazione Automatica
- **Schedulazione**: Primo giorno di ogni mese alle 9:00
- **Periodo**: Copre il mese precedente
- **Email**: Invio automatico al CEO se abilitato

## 📁 Struttura File

```
services/
├── ceo_monthly_report.py          # Servizio principale
└── ceo_notifications.py          # Notifiche CEO (esistente)

routes/
└── ceo_report_routes.py          # Route per gestione report

templates/ceo/
├── report_dashboard.html          # Dashboard report
└── genera_report.html            # Generazione manuale

uploads/
└── reports/                      # Directory report PDF
    ├── report_ceo_2024_01.pdf
    ├── report_ceo_2024_02.pdf
    └── ...
```

## 🔧 Configurazione

### Variabili d'Ambiente
```bash
# Email CEO per notifiche e report
CEO_EMAIL=ceo@mercurysurgelati.org

# Abilita invio email report CEO mensile
ENABLE_CEO_EMAIL_REPORTS=True
```

### Configurazione Flask
```python
# config.py
class Config:
    # Email CEO per notifiche automatiche
    CEO_EMAIL = 'ceo@mercurysurgelati.org'
    
    # Abilita invio email report CEO mensile
    ENABLE_CEO_EMAIL_REPORTS = True
```

## 🛠️ Utilizzo

### Generazione Automatica
Il report viene generato automaticamente il primo giorno di ogni mese alle 9:00 tramite APScheduler.

### Generazione Manuale
```python
from services.ceo_monthly_report import genera_report_ceo_mensile

# Genera report per mese specifico
result = genera_report_ceo_mensile(
    month=7,           # Mese (1-12)
    year=2024,         # Anno
    send_email=True    # Invia via email
)
```

### Accesso Web Interface
- **Dashboard Report**: `/ceo/report/`
- **Generazione Manuale**: `/ceo/report/genera`
- **Download Report**: `/ceo/report/download/<filename>`
- **Visualizzazione**: `/ceo/report/visualizza/<filename>`

## 📊 Struttura PDF

### Header
- Titolo: "Report Mensile CEO - [Mese] [Anno]"
- Data generazione
- Logo aziendale (se configurato)

### Sezione 1: Invii PDF Sensibili
| Campo | Descrizione |
|-------|-------------|
| Data/Ora | Timestamp dell'invio |
| Utente/Guest | Nome destinatario |
| Mittente | Email admin mittente |
| Destinatario | Email destinatario |
| Criterio | Motivo sensibilità |

### Sezione 2: Alert AI Attivi
| Campo | Descrizione |
|-------|-------------|
| Data | Data creazione alert |
| Utente/Guest | Utente coinvolto |
| Tipo Alert | Tipo di alert |
| Livello | Basso/Medio/Alto/Critico |
| Stato | Nuovo/In Revisione/Chiuso |

### Sezione 3: Eventi Audit Trail
| Campo | Descrizione |
|-------|-------------|
| Data/Ora | Timestamp evento |
| Tipo Evento | Categoria evento |
| Utente | Utente coinvolto |
| Azione | Descrizione azione |
| Ruolo | Ruolo utente |

## 🔍 API Endpoints

### Dashboard Report
```http
GET /ceo/report/
```
Visualizza lista report disponibili e statistiche.

### Generazione Manuale
```http
POST /ceo/report/genera
```
Genera report per mese/anno specifico.

**Parametri:**
- `month`: Mese (1-12)
- `year`: Anno
- `send_email`: Invia via email (checkbox)

### Download Report
```http
GET /ceo/report/download/<filename>
```
Scarica report PDF.

### Visualizzazione Report
```http
GET /ceo/report/visualizza/<filename>
```
Visualizza report nel browser.

### Statistiche API
```http
GET /ceo/report/api/statistiche
```
Restituisce statistiche JSON sui report.

## 🧪 Testing

### Test Manuale
```bash
# Test generazione report
python -c "from services.ceo_monthly_report import test_report_generation; test_report_generation()"

# Test completo
python scripts/test_ceo_monthly_report.py
```

### Test Scheduler
```bash
# Verifica job scheduler
python -c "from scheduler import genera_report_ceo_mensile_automatico; print('Scheduler OK')"
```

## 📈 Monitoraggio

### Log Files
- **Generazione Report**: `logs/app.log`
- **Scheduler**: `logs/scheduler.log`
- **Email**: `logs/mail.log`

### Metriche Chiave
- Numero report generati per mese
- Dimensione totale report
- Successo invio email
- Errori generazione

## 🔒 Sicurezza

### Controlli Accesso
- Solo CEO e Admin possono accedere ai report
- Autenticazione richiesta per tutte le operazioni
- Logging di tutte le azioni

### Protezione Dati
- Report salvati in directory protetta
- Email inviate solo a indirizzi autorizzati
- Nessun dato sensibile nei log

## 🚨 Troubleshooting

### Problemi Comuni

#### 1. Report non generato automaticamente
```bash
# Verifica scheduler
python -c "from app import app; print('Scheduler:', hasattr(app, 'scheduler'))"

# Verifica configurazione
python -c "from config import Config; print('Email CEO:', Config.CEO_EMAIL)"
```

#### 2. Errore generazione PDF
```bash
# Verifica dipendenze
pip list | grep reportlab

# Test generazione
python -c "from services.ceo_monthly_report import test_report_generation; test_report_generation()"
```

#### 3. Email non inviata
```bash
# Verifica configurazione email
python -c "from config import Config; print('Mail config:', Config.MAIL_SERVER)"

# Test invio email
python -c "from services.ceo_monthly_report import CEOMonthlyReportGenerator; g = CEOMonthlyReportGenerator(); g.send_report_via_email()"
```

### Log di Debug
```python
import logging
logging.getLogger('services.ceo_monthly_report').setLevel(logging.DEBUG)
```

## 📋 Checklist Implementazione

- [x] Servizio generazione report
- [x] Integrazione APScheduler
- [x] Route web interface
- [x] Template dashboard
- [x] Template generazione manuale
- [x] Configurazione email
- [x] Test automatici
- [x] Documentazione
- [x] Sicurezza e accessi
- [x] Monitoraggio e log

## 🎉 Risultati

Il sistema di report CEO mensile è ora completamente implementato e funzionante:

✅ **Generazione Automatica**: Report mensili automatici il primo giorno del mese
✅ **Contenuto Completo**: Invii sensibili, alert AI, audit trail
✅ **Interface Web**: Dashboard completa per gestione report
✅ **Email Automatica**: Invio automatico al CEO
✅ **Sicurezza**: Controlli accesso e protezione dati
✅ **Monitoraggio**: Logging completo e metriche

Il sistema è pronto per l'uso in produzione! 🚀
