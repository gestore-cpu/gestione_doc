# 🚨 Sistema di Monitoraggio AI per Download Sospetti

## Panoramica

Il sistema di monitoraggio AI per download sospetti è progettato per rilevare automaticamente comportamenti anomali nei download documentali, migliorando la sicurezza e la compliance (NIS2, ISO 27001).

## 🧠 Comportamenti Sospetti Rilevati

### 1. Download Massivi
- **Soglia**: >5 download in <2 minuti dallo stesso utente
- **Severità**: Alta
- **Rischio**: Possibile esfiltrazione di dati

### 2. Accessi Fuori Orario
- **Orario**: 20:00 - 07:00
- **Severità**: Media
- **Rischio**: Accesso non autorizzato

### 3. Ripetizione File
- **Soglia**: >3 download dello stesso file in 5 minuti
- **Severità**: Media
- **Rischio**: Tentativo di bypass o errore di sistema

### 4. IP Sospetti
- **Controllo**: IP non nella lista autorizzata
- **Severità**: Alta
- **Rischio**: Accesso da location non autorizzata

### 5. Tentativi su Documenti Bloccati
- **Rilevamento**: Tentativi di download su documenti non scaricabili
- **Severità**: Media
- **Rischio**: Tentativo di accesso non autorizzato

## 🏗️ Architettura del Sistema

### Componenti Principali

#### 1. Servizio AI Monitoring (`services/ai_monitoring.py`)
```python
class AIMonitoringService:
    def analizza_download_sospetti() -> List[Dict]
    def create_ai_alert(alert_data: Dict) -> Optional[AIAlert]
    def get_recent_alerts(hours: int = 24) -> List[AIAlert]
    def get_alert_statistics() -> Dict
```

#### 2. Modello Database (`models.py`)
```python
class AIAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    severity = db.Column(db.String(20), nullable=False)  # bassa, media, alta, critica
    description = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.String(150), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### 3. Route Admin (`admin_routes.py`)
- `GET /admin/ai/alerts` - Visualizza alert AI
- `POST /admin/ai/alerts/analyze` - Analisi manuale
- `POST /admin/ai/alerts/<id>/resolve` - Risolve alert
- `GET /admin/ai/alerts/export` - Esporta CSV
- `GET /admin/ai/alerts/stats` - Statistiche

#### 4. Template UI (`templates/admin/ai_alerts.html`)
- Dashboard con statistiche
- Filtri avanzati
- Grafici interattivi
- Tabella responsive
- Modal per dettagli

#### 5. Scheduler Automatico (`scheduler.py`)
```python
def monitora_download_sospetti():
    """Esegue il monitoraggio AI ogni 10 minuti"""
    alerts = analizza_download_sospetti()
    for alert_data in alerts:
        create_ai_alert(alert_data)
```

## 🔧 Configurazione

### Pattern Sospetti
```python
suspicious_patterns = {
    'download_massivo': {
        'threshold': 5,  # >5 download
        'timeframe': 2,  # in <2 minuti
        'severity': 'alta'
    },
    'accesso_fuori_orario': {
        'start_hour': 20,  # 20:00
        'end_hour': 7,     # 07:00
        'severity': 'media'
    },
    'ripetizione_file': {
        'threshold': 3,  # >3 volte
        'timeframe': 5,  # in 5 minuti
        'severity': 'media'
    },
    'ip_sospetto': {
        'severity': 'alta'
    }
}
```

### IP Autorizzati
```python
# In config.py
AUTHORIZED_IPS = [
    '192.168.1.0/24',  # Rete aziendale
    '10.0.0.0/8',      # VPN aziendale
    # Aggiungi altri IP autorizzati
]
```

## 📊 Funzionalità

### 1. Monitoraggio Automatico
- **Frequenza**: Ogni 10 minuti
- **Scope**: Tutti i log di download
- **Output**: Alert nel database

### 2. Analisi AI
- **Prompt**: "Analizza questo pattern di download. È sospetto?"
- **Output**: Valutazione rischio + raccomandazioni
- **Storico**: Tutte le analisi salvate

### 3. Dashboard Admin
- **Statistiche**: Totali, risolti, in attesa, critici
- **Filtri**: Severità, tipo, stato, data
- **Grafici**: Distribuzione per severità e tipo
- **Azioni**: Risoluzione, esportazione, dettagli

### 4. Notifiche
- **Email**: Opzionale per alert critici
- **Log**: Tutti gli eventi tracciati
- **Audit**: Tracciabilità completa

## 🚀 Utilizzo

### 1. Accesso Dashboard
```
URL: /admin/ai/alerts
Ruolo: Admin
```

### 2. Analisi Manuale
```python
from services.ai_monitoring import analizza_download_sospetti

# Esegue analisi completa
alerts = analizza_download_sospetti()

# Crea alert nel database
for alert_data in alerts:
    create_ai_alert(alert_data)
```

### 3. Recupero Alert
```python
from services.ai_monitoring import get_recent_alerts, get_alert_statistics

# Alert ultime 24 ore
alerts = get_recent_alerts(24)

# Statistiche
stats = get_alert_statistics()
```

### 4. Risoluzione Alert
```python
from services.ai_monitoring import ai_monitoring_service

# Risolve alert
success = ai_monitoring_service.resolve_alert(alert_id, "admin")
```

## 🔒 Sicurezza e Compliance

### NIS2 Compliance
- ✅ Monitoraggio accessi
- ✅ Tracciabilità completa
- ✅ Alert automatici
- ✅ Audit log

### ISO 27001 Compliance
- ✅ Controllo accessi
- ✅ Monitoraggio anomalie
- ✅ Gestione incidenti
- ✅ Documentazione

### GDPR Compliance
- ✅ Minimizzazione dati
- ✅ Trasparenza
- ✅ Diritto di rettifica
- ✅ Sicurezza del trattamento

## 📈 Metriche e KPI

### Alert per Severità
- **Bassa**: 0-10%
- **Media**: 10-30%
- **Alta**: 30-60%
- **Critica**: 60-100%

### Tempo di Risoluzione
- **Target**: <4 ore per alert critici
- **Target**: <24 ore per alert alti
- **Target**: <72 ore per alert medi

### Falsi Positivi
- **Target**: <5% per alert critici
- **Target**: <15% per alert alti
- **Target**: <25% per alert medi

## 🛠️ Manutenzione

### Log Files
```
/var/log/gestione_doc/ai_monitoring.log
```

### Database
```sql
-- Verifica alert recenti
SELECT * FROM ai_alerts 
WHERE created_at >= NOW() - INTERVAL 24 HOUR
ORDER BY created_at DESC;

-- Statistiche per severità
SELECT severity, COUNT(*) as count
FROM ai_alerts 
GROUP BY severity;
```

### Backup
```bash
# Backup alert critici
pg_dump -t ai_alerts --where="severity IN ('alta', 'critica')" gestione_doc > ai_alerts_critical.sql
```

## 🔄 Aggiornamenti

### Versioni
- **v1.0**: Sistema base di monitoraggio
- **v1.1**: Aggiunta analisi AI
- **v1.2**: Dashboard admin
- **v1.3**: Scheduler automatico

### Roadmap
- **v2.0**: Machine Learning avanzato
- **v2.1**: Geolocalizzazione IP
- **v2.2**: Integrazione SIEM
- **v2.3**: API REST

## 📞 Supporto

### Contatti
- **Sviluppatore**: Jack Synthia AI
- **Email**: ai@mercurysurgelati.org
- **Documentazione**: `/docs/ai_monitoring`

### Troubleshooting
1. **Alert non generati**: Verifica scheduler
2. **Falsi positivi**: Aggiusta soglie
3. **Performance**: Ottimizza query
4. **Integrazione**: Verifica API

---

**Sistema sviluppato da Jack Synthia AI per Mercury Surgelati**
*Compliance NIS2, ISO 27001, GDPR* 