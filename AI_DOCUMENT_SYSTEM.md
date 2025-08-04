# 🤖 Sistema AI per Analisi Automatica Documenti

## 📋 Panoramica

Il sistema AI per l'analisi automatica dei documenti è stato implementato per rilevare automaticamente:

- **Documenti duplicati** o molto simili
- **Documenti obsoleti** (scaduti, non aggiornati)
- **Documenti vecchi** (creati da più di un anno)
- **Documenti inutilizzati** (non accessi da più di 6 mesi)

Il sistema genera insight AI e suggerisce task automatici per la gestione documentale.

## 🏗️ Architettura

### Componenti Principali

1. **`ai/document_ai_utils.py`** - Utility AI per l'analisi
2. **`ai/document_ai_scheduler.py`** - Script periodico per l'analisi
3. **`models.py`** - Modello `DocumentoAIInsight`
4. **`admin_routes.py`** - Route Flask per la dashboard AI
5. **`templates/docs/dashboard_ai.html`** - Dashboard AI
6. **`cli_ai_analysis.py`** - Comando CLI per l'analisi

### Modello Database

```python
class DocumentoAIInsight(db.Model):
    __tablename__ = "document_ai_insights"
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'))
    tipo = db.Column(db.String(50))  # duplicato, obsoleto, vecchio, inutilizzato
    valore = db.Column(db.String(500))  # Dettagli dell'insight
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    severity = db.Column(db.String(20), default="attenzione")
    status = db.Column(db.String(20), default="attivo")
```

## 🚀 Funzionalità

### 1. Analisi Automatica dei Documenti

Il sistema analizza automaticamente tutti i documenti per:

- **Estrazione testo** da PDF, DOCX, TXT, immagini (OCR)
- **Calcolo similarità** tra documenti usando SequenceMatcher
- **Rilevamento obsolescenza** basato su scadenze e età
- **Analisi utilizzo** basata sui log di accesso

### 2. Generazione Insight AI

Per ogni documento analizzato, il sistema genera insight che includono:

- **Tipo di problema** (duplicato, obsoleto, vecchio, inutilizzato)
- **Severità** (critico, attenzione, informativo)
- **Dettagli specifici** del problema
- **Suggerimenti** per la risoluzione

### 3. Dashboard AI

Interfaccia web moderna per:

- **Visualizzazione insight** con filtri avanzati
- **Statistiche in tempo reale**
- **Azioni rapide** (risolvi, ignora, crea task)
- **Esportazione dati** in CSV

### 4. Task Automatici

Il sistema può generare automaticamente task per:

- **Verifica duplicati** - Priorità Alta
- **Aggiornamento documenti scaduti** - Priorità Critica
- **Revisione documenti vecchi** - Priorità Media
- **Verifica documenti inutilizzati** - Priorità Bassa

## 📊 Dashboard AI

### Accesso
```
/admin/ai/insights
```

### Funzionalità

1. **Statistiche Rapide**
   - Insight attivi
   - Documenti obsoleti
   - Duplicati rilevati
   - Documenti vecchi

2. **Filtri Avanzati**
   - Per tipo di insight
   - Per severità
   - Per stato
   - Ricerca per nome documento

3. **Azioni Disponibili**
   - ✅ Segna come risolto
   - ⚪ Ignora
   - 📋 Crea task automatico
   - 👁️ Vedi documento simile (per duplicati)
   - ✏️ Avvia aggiornamento (per obsoleti)

## 🛠️ Utilizzo

### Via Web Interface

1. Accedi come admin
2. Vai su "AI Documentale" nella sidebar
3. Visualizza gli insight generati
4. Usa i filtri per trovare problemi specifici
5. Esegui azioni sui documenti

### Via CLI

```bash
# Analizza tutti i documenti
python cli_ai_analysis.py --analyze-all

# Pulisce insight obsoleti
python cli_ai_analysis.py --clean-insights

# Esporta insight in CSV
python cli_ai_analysis.py --export-csv

# Mostra riepilogo
python cli_ai_analysis.py --summary
```

### Via API

```bash
# Esegui analisi AI
curl -X POST /admin/ai/analyze

# Risolvi insight
curl -X POST /admin/ai/insight/{id}/resolve

# Ignora insight
curl -X POST /admin/ai/insight/{id}/ignore

# Crea task da insight
curl -X POST /admin/ai/insight/{id}/create-task
```

## 🔧 Configurazione

### Dipendenze

```bash
pip install python-docx opencv-python numpy pytesseract
```

### Soglie Configurabili

Nel file `ai/document_ai_utils.py`:

```python
# Soglia per rilevamento duplicati
SIMILARITY_THRESHOLD = 0.85

# Età documento per considerarlo "vecchio"
OLD_DOCUMENT_DAYS = 365

# Giorni senza accesso per considerarlo "inutilizzato"
UNUSED_DOCUMENT_DAYS = 180
```

## 📈 Monitoraggio

### Log

Il sistema genera log dettagliati in:
- `logs/ai_analysis_report.json` - Report analisi
- Console output per debug

### Metriche

- **Documenti analizzati**
- **Insight generati**
- **Task creati**
- **Errori riscontrati**

## 🔄 Automazione

### Analisi Periodica

Per automatizzare l'analisi, aggiungi al crontab:

```bash
# Analisi giornaliera alle 2:00
0 2 * * * cd /var/www/gestione_doc && python cli_ai_analysis.py --analyze-all

# Pulizia settimanale domenica alle 3:00
0 3 * * 0 cd /var/www/gestione_doc && python cli_ai_analysis.py --clean-insights
```

### Notifiche

Il sistema può essere esteso per inviare notifiche email per:
- Insight critici
- Documenti scaduti
- Duplicati rilevati

## 🧪 Testing

### Test Automatici

```bash
python test_ai_document_system.py
```

Il test verifica:
- Estrazione testo da diversi formati
- Calcolo similarità tra testi
- Generazione insight AI
- Analisi completa documenti

## 🔒 Sicurezza

### Permessi

- Solo admin possono accedere alla dashboard AI
- Tutte le operazioni sono loggate
- Validazione input su tutte le route

### Privacy

- I file vengono analizzati localmente
- Nessun dato viene inviato a servizi esterni
- I log non contengono contenuti sensibili

## 🚀 Roadmap

### Funzionalità Future

1. **OCR Avanzato**
   - Supporto per più lingue
   - Riconoscimento layout complessi

2. **Machine Learning**
   - Classificazione automatica documenti
   - Predizione obsolescenza

3. **Integrazione Avanzata**
   - Notifiche push
   - Integrazione con sistemi esterni
   - API REST completa

4. **Analisi Avanzata**
   - Pattern di utilizzo
   - Suggerimenti intelligenti
   - Automazione completa

## 📞 Supporto

Per problemi o domande:
1. Controlla i log in `logs/`
2. Esegui i test automatici
3. Verifica le dipendenze
4. Controlla i permessi del database

---

**Versione**: 1.0  
**Data**: Luglio 2025  
**Autore**: Sistema AI Documentale 