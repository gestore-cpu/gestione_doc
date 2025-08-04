# 📥 Sistema di Log Download e Esportazione CSV

## Panoramica

Il sistema di log download permette agli admin di tracciare, filtrare ed esportare tutti i download documentali per scopi di audit, sicurezza e analisi.

## 🏗️ Architettura del Sistema

### Componenti Principali

#### 1. Modello Database (`models.py`)
```python
class DownloadLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="download_logs")
    document = db.relationship("Document", backref="download_logs")
```

#### 2. Route Admin (`admin_routes.py`)
- `GET /admin/download_logs` - Visualizza log download
- `GET /admin/download_logs/export` - Esporta CSV
- `GET /admin/download_logs/stats` - Statistiche

#### 3. Template UI (`templates/admin/download_logs.html`)
- Dashboard con statistiche
- Filtri avanzati
- Grafici interattivi
- Tabella responsive
- Esportazione CSV

## 📊 Funzionalità

### 1. Visualizzazione Log
- **Tabella completa** con tutti i download
- **Relazioni** con utenti, documenti, aziende
- **Ordinamento** per timestamp decrescente
- **Paginazione** automatica

### 2. Filtri Avanzati
- **Utente**: Filtra per utente specifico
- **Documento**: Filtra per documento specifico
- **Azienda**: Filtra per azienda
- **Data**: Range di date personalizzabile
- **Reset**: Pulsante per resettare filtri

### 3. Statistiche Dashboard
- **Download totali**: Numero complessivo
- **Utenti unici**: Utenti che hanno scaricato
- **Documenti unici**: Documenti scaricati
- **Ultimi 30 giorni**: Trend recente

### 4. Esportazione CSV
- **Formato standard**: Compatibile con Excel
- **Campi completi**: Tutti i dati disponibili
- **Nome file**: Con timestamp automatico
- **Filtri applicati**: Esporta solo i dati filtrati

### 5. Grafici Interattivi
- **Distribuzione per azienda**: Grafico a torta
- **Download per periodo**: Grafico a barre
- **Chart.js**: Libreria moderna e responsive

## 🔧 Configurazione

### Campi Esportati CSV
```csv
ID,Data e Ora,Utente,Email Utente,File Scaricato,Azienda,Reparto,IP Accesso,Metodo,Note
1,2024-01-15 10:30:00,admin,admin@example.com,documento.pdf,Mercury,Qualità,192.168.1.100,Web,
```

### Filtri Disponibili
```python
filters = {
    'user_id': '1',           # ID utente
    'document_id': '1',        # ID documento
    'company_id': '1',         # ID azienda
    'date_from': '2024-01-01', # Data inizio
    'date_to': '2024-12-31'    # Data fine
}
```

### Statistiche Calcolate
```python
stats = {
    'total': 100,              # Download totali
    'unique_users': 25,        # Utenti unici
    'unique_documents': 50,    # Documenti unici
    'recent_30_days': 30      # Ultimi 30 giorni
}
```

## 🚀 Utilizzo

### 1. Accesso Dashboard
```
URL: /admin/download_logs
Ruolo: Admin
```

### 2. Applicazione Filtri
```python
# Esempio di filtri
filters = {
    'user_id': '1',           # Solo utente specifico
    'date_from': '2024-01-01', # Da data specifica
    'date_to': '2024-12-31'    # A data specifica
}
```

### 3. Esportazione CSV
```python
# URL per esportazione con filtri
/admin/download_logs/export?user_id=1&date_from=2024-01-01
```

### 4. Recupero Statistiche
```python
# URL per statistiche
/admin/download_logs/stats
```

## 📈 Metriche e KPI

### Download per Periodo
- **Oggi**: Download del giorno corrente
- **Ieri**: Download del giorno precedente
- **Ultimi 7 giorni**: Trend settimanale
- **Ultimi 30 giorni**: Trend mensile

### Top Utenti
- **Classifica**: Utenti con più download
- **Conteggio**: Numero download per utente
- **Periodo**: Ultimi 30 giorni

### Top Documenti
- **Classifica**: Documenti più scaricati
- **Conteggio**: Numero download per documento
- **Periodo**: Ultimi 30 giorni

## 🔒 Sicurezza e Compliance

### GDPR Compliance
- ✅ **Minimizzazione dati**: Solo dati necessari
- ✅ **Trasparenza**: Utenti informati del tracciamento
- ✅ **Diritto di rettifica**: Possibilità di correzione
- ✅ **Sicurezza del trattamento**: Dati protetti

### ISO 27001 Compliance
- ✅ **Controllo accessi**: Solo admin autorizzati
- ✅ **Tracciabilità**: Log completi di accesso
- ✅ **Audit**: Esportazione per audit esterni
- ✅ **Documentazione**: Procedure documentate

### NIS2 Compliance
- ✅ **Monitoraggio**: Tracciamento accessi
- ✅ **Reporting**: Esportazione per autorità
- ✅ **Sicurezza**: Protezione dati sensibili
- ✅ **Compliance**: Aderenza a standard

## 🛠️ Manutenzione

### Log Files
```
/var/log/gestione_doc/download_logs.log
```

### Database
```sql
-- Verifica log recenti
SELECT * FROM download_logs 
WHERE timestamp >= NOW() - INTERVAL 24 HOUR
ORDER BY timestamp DESC;

-- Statistiche per utente
SELECT user_id, COUNT(*) as downloads
FROM download_logs 
GROUP BY user_id
ORDER BY downloads DESC;
```

### Backup
```bash
# Backup log critici
pg_dump -t download_logs --where="timestamp >= NOW() - INTERVAL 30 DAY" gestione_doc > download_logs_recent.sql
```

## 🔄 Aggiornamenti

### Versioni
- **v1.0**: Sistema base di log
- **v1.1**: Filtri avanzati
- **v1.2**: Esportazione CSV
- **v1.3**: Dashboard con grafici

### Roadmap
- **v2.0**: Analisi predittiva
- **v2.1**: Alert automatici
- **v2.2**: Integrazione SIEM
- **v2.3**: API REST

## 📞 Supporto

### Contatti
- **Sviluppatore**: Jack Synthia AI
- **Email**: ai@mercurysurgelati.org
- **Documentazione**: `/docs/download_logs`

### Troubleshooting
1. **Log non visualizzati**: Verifica permessi admin
2. **Filtri non funzionano**: Controlla formato date
3. **CSV non scarica**: Verifica spazio disco
4. **Performance lente**: Ottimizza query database

## 📋 Checklist Implementazione

### ✅ Backend
- [x] Modello DownloadLog
- [x] Route per visualizzazione
- [x] Route per esportazione CSV
- [x] Route per statistiche
- [x] Filtri avanzati
- [x] Gestione errori

### ✅ Frontend
- [x] Template responsive
- [x] Dashboard statistiche
- [x] Filtri interattivi
- [x] Grafici Chart.js
- [x] Esportazione CSV
- [x] Auto-refresh

### ✅ Sicurezza
- [x] Controllo accessi admin
- [x] Validazione input
- [x] Sanitizzazione dati
- [x] Log di accesso
- [x] Protezione CSRF

### ✅ Compliance
- [x] GDPR compliance
- [x] ISO 27001 compliance
- [x] NIS2 compliance
- [x] Audit trail
- [x] Data retention

### ✅ Testing
- [x] Test unitari
- [x] Test integrazione
- [x] Test performance
- [x] Test sicurezza
- [x] Test compliance

---

**Sistema sviluppato da Jack Synthia AI per Mercury Surgelati**
*Compliance GDPR, ISO 27001, NIS2* 