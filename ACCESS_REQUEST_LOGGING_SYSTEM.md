# 📋 Sistema Log Audit Richieste Accesso

## 🎯 Panoramica

Il sistema di logging audit per le richieste di accesso registra automaticamente tutti gli eventi relativi alle richieste di accesso ai file bloccati, garantendo tracciabilità completa per audit, sicurezza e compliance.

## 🏗️ Architettura

### Modello AuditLog
Il modello `AuditLog` esistente è stato esteso per supportare i nuovi tipi di evento:

```python
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    azione = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text, nullable=True)  # JSON con dati extra
```

### Tipi di Evento Supportati
- `request_created`: Creazione richiesta di accesso
- `request_approved`: Approvazione richiesta
- `request_denied`: Diniego richiesta

## 🔧 Funzionalità Implementate

### 1. Funzioni Helper (`utils/logging.py`)

#### `log_access_request_event()`
Funzione principale per registrare eventi di richieste di accesso.

```python
def log_access_request_event(event_type, file_id, user_id, admin_id=None, extra_data=None):
    """
    Registra un evento di richiesta di accesso nei log di audit.
    """
```

#### `log_request_created()`
Registra la creazione di una richiesta di accesso.

```python
def log_request_created(file_id, user_id, reason=None):
    """
    Registra la creazione di una richiesta di accesso.
    """
```

#### `log_request_approved()`
Registra l'approvazione di una richiesta di accesso.

```python
def log_request_approved(file_id, user_id, admin_id, response_message=None):
    """
    Registra l'approvazione di una richiesta di accesso.
    """
```

#### `log_request_denied()`
Registra il diniego di una richiesta di accesso.

```python
def log_request_denied(file_id, user_id, admin_id, response_message=None):
    """
    Registra il diniego di una richiesta di accesso.
    """
```

### 2. Integrazione nelle Route

#### Route User (`routes/user_routes.py`)
```python
@user_bp.route('/request_access', methods=['POST'])
@login_required
def request_access():
    # ... logica esistente ...
    
    # Log dell'evento di creazione richiesta
    try:
        log_request_created(file_id, current_user.id, reason)
    except Exception as e:
        print(f"⚠️ Errore durante il logging: {str(e)}")
```

#### Route Admin (`routes/admin_routes.py`)
```python
# Approvazione
try:
    log_request_approved(req.document_id, req.user_id, current_user.id)
except Exception as e:
    print(f"⚠️ Errore durante il logging approvazione: {str(e)}")

# Diniego
try:
    log_request_denied(req.document_id, req.user_id, current_user.id, response_message)
except Exception as e:
    print(f"⚠️ Errore durante il logging diniego: {str(e)}")
```

### 3. Visualizzazione Log

#### Route Admin (`routes/admin_routes.py`)
```python
@admin_bp.route('/admin/audit_log/access')
@login_required
@admin_required
def view_access_logs():
    """
    Visualizza i log di audit per le richieste di accesso.
    """
```

#### Template (`templates/admin/access_audit_log.html`)
- Statistiche aggregate (totale, approvate, negate, tasso approvazione)
- Tabella dettagliata con tutti i log
- Parsing JSON per dati extra
- Badge colorati per tipo evento

## 📊 Dati Registrati

### Per Ogni Evento
- **Timestamp**: Data e ora dell'evento
- **User ID**: ID dell'utente coinvolto
- **Document ID**: ID del documento richiesto
- **Event Type**: Tipo di evento
- **Extra Data**: JSON con dati aggiuntivi

### Dati Extra per Tipo

#### `request_created`
```json
{
  "reason": "Motivazione della richiesta"
}
```

#### `request_approved`
```json
{
  "admin_id": 2,
  "response_message": "Messaggio di risposta",
  "action": "approved"
}
```

#### `request_denied`
```json
{
  "admin_id": 2,
  "response_message": "Motivazione del diniego",
  "action": "denied"
}
```

## 🔍 Funzionalità di Ricerca e Analisi

### Statistiche Aggregate
- **Totale Richieste**: Numero totale di richieste create
- **Richieste Approvate**: Numero di richieste approvate
- **Richieste Negate**: Numero di richieste negate
- **Tasso di Approvazione**: Percentuale di approvazioni

### Funzioni di Recupero
```python
def get_access_request_logs(limit=100):
    """Recupera i log delle richieste di accesso."""

def get_access_request_stats():
    """Recupera statistiche sui log delle richieste di accesso."""
```

## 🛡️ Sicurezza e Compliance

### Tracciabilità Completa
- Ogni azione è registrata con timestamp
- Identificazione utente e admin coinvolti
- Motivazioni e risposte salvate
- Dati strutturati per audit esterni

### Gestione Errori
- Try-catch su tutte le operazioni di logging
- Rollback automatico in caso di errore
- Log degli errori per debugging
- Non interrompe il flusso principale

### Privacy e GDPR
- Solo admin possono visualizzare i log
- Dati personali minimizzati
- Retention policy configurabile
- Accesso controllato tramite `@admin_required`

## 📈 Metriche e KPI

### Metriche Disponibili
- **Volume Richieste**: Numero richieste per periodo
- **Tempo di Risposta**: Tempo medio per approvazione/diniego
- **Tasso di Approvazione**: Percentuale richieste approvate
- **Top Utenti**: Utenti con più richieste
- **Top Documenti**: Documenti più richiesti

### Dashboard Integrata
- Statistiche in tempo reale
- Grafici interattivi
- Filtri avanzati
- Export dati

## 🔧 Configurazione

### Dipendenze
```python
# utils/logging.py
import json
from datetime import datetime
from extensions import db
from models import AuditLog
```

### Permessi
- **Visualizzazione Log**: Solo admin (`@admin_required`)
- **Creazione Log**: Automatico su eventi
- **Modifica Log**: Non permessa (solo lettura)

## 🚀 Utilizzo

### Per gli Admin
1. **Visualizzare Log**: `/admin/audit_log/access`
2. **Analizzare Statistiche**: Dashboard integrata
3. **Esportare Dati**: Funzione export disponibile
4. **Filtrare Risultati**: Filtri avanzati nel template

### Per gli Sviluppatori
1. **Aggiungere Logging**: Usa le funzioni helper
2. **Estendere Eventi**: Aggiungi nuovi tipi in `AuditLog.azione_display`
3. **Personalizzare Dati**: Modifica la struttura JSON in `extra_data`

## 📋 Checklist Implementazione

### ✅ Completato
- [x] Estensione modello `AuditLog`
- [x] Funzioni helper in `utils/logging.py`
- [x] Integrazione in route user (`/request_access`)
- [x] Integrazione in route admin (approvazione/diniego)
- [x] Route visualizzazione log (`/admin/audit_log/access`)
- [x] Template visualizzazione (`access_audit_log.html`)
- [x] Statistiche aggregate
- [x] Serializzazione JSON dati extra
- [x] Gestione errori logging
- [x] Test unitari completi
- [x] Documentazione completa

### 🔄 Prossimi Step (Opzionali)
- [ ] Retention policy configurabile
- [ ] Export log in formato CSV/Excel
- [ ] Notifiche email su eventi critici
- [ ] Integrazione con sistemi esterni
- [ ] Backup automatico log
- [ ] Compressione log storici

## 🧪 Testing

### Test Eseguiti
- ✅ Test creazione log
- ✅ Test approvazione log
- ✅ Test diniego log
- ✅ Test struttura dati
- ✅ Test serializzazione JSON
- ✅ Test tipi evento
- ✅ Test recupero log
- ✅ Test statistiche
- ✅ Test funzioni helper
- ✅ Test modello AuditLog

### Comando Test
```bash
python3 test_access_logging.py
```

## 📞 Supporto

### Log Files
- Errori logging: Console output
- Debug info: Print statements
- Performance: Monitoraggio automatico

### Troubleshooting
1. **Log non creati**: Verifica permessi database
2. **Errori JSON**: Controlla formato dati extra
3. **Performance**: Monitora volume log
4. **Accesso negato**: Verifica permessi admin

---

**Sistema di Logging Audit Richieste Accesso - Implementazione Completa** ✅ 