# 🤖 Sistema Auto-Task AI per Documenti

## 📋 Panoramica

Il sistema **Auto-Task AI** è un componente avanzato che collega automaticamente il modulo **Docs** con i sistemi **FocusMe AI** e **QMS**, generando task intelligenti quando l'AI identifica documenti che necessitano di attenzione.

### 🎯 Obiettivi

- **Rilevamento Automatico**: Identifica documenti obsoleti, duplicati, vecchi o inutilizzati
- **Generazione Task**: Crea automaticamente task appropriati con priorità e scadenze
- **Routing Intelligente**: Assegna task al modulo corretto (QMS o FocusMe AI)
- **Gestione Centralizzata**: Dashboard unificata per monitorare tutti i task AI

## 🏗️ Architettura

### Componenti Principali

1. **`ai/task_generator.py`** - Motore di generazione task
2. **`ai/document_ai_scheduler.py`** - Integrazione con analisi AI
3. **`admin_routes.py`** - API e route per gestione task
4. **`templates/admin/ai_tasks.html`** - Dashboard task AI
5. **`models.py`** - Modello Task esistente (esteso)

### Flusso di Lavoro

```
Documento → Analisi AI → Insight → Task Generator → Routing → Task Finale
    ↓           ↓           ↓           ↓           ↓         ↓
  Upload    Obsoleto    Critico    QMS/FocusMe   Priorità   Dashboard
```

## 🔧 Funzionalità Implementate

### 1. Generazione Task Intelligente

#### Tipi di Task Supportati

| Tipo Insight | Priorità | Scadenza | Modulo Destinazione |
|-------------|----------|----------|-------------------|
| **Obsoleto** | Critica | 3 giorni | QMS |
| **Duplicato** | Alta | 7 giorni | QMS |
| **Vecchio** | Media | 14 giorni | FocusMe |
| **Inutilizzato** | Bassa | 30 giorni | FocusMe |

#### Esempi di Task Generati

```python
# Task QMS per documento obsoleto
titolo = "⚠️ Revisione urgente: Manuale Qualità 2024"
descrizione = "Il documento è stato identificato come obsoleto dall'AI..."
priorita = "Critica"
scadenza = oggi + 3 giorni

# Task FocusMe per documento vecchio
titolo = "📅 Aggiornamento consigliato: Piano Strategico 2023"
descrizione = "Il documento è stato creato più di un anno fa..."
priorita = "Media"
scadenza = oggi + 14 giorni
```

### 2. Routing Intelligente

#### Logica di Routing

```python
def determina_modulo_destinazione(document, tipo_insight):
    # Documenti di processo → QMS
    if document.company.name.lower() in ['processo', 'certificazione', 'qualità']:
        return "QMS"
    
    # Documenti strategici → FocusMe
    if document.title.lower() in ['strategia', 'piano', 'obiettivo', 'kpi']:
        return "FocusMe"
    
    # Per tipo di insight
    if tipo_insight in ["obsoleto", "duplicato"]:
        return "QMS"  # Problemi critici
    else:
        return "FocusMe"  # Analisi strategica
```

### 3. Dashboard Task AI

#### Caratteristiche

- **Statistiche in Tempo Reale**: Totali, da fare, in corso, completati, critici, scaduti
- **Filtri Avanzati**: Per stato, priorità, modulo, ricerca testuale
- **Gestione Task**: Aggiornamento stato, note, completamento
- **Esportazione**: CSV con tutti i task AI
- **Pulizia Automatica**: Rimozione task obsoleti

#### Azioni Disponibili

- 👁️ **Visualizza Dettagli**: Modal con informazioni complete
- ✏️ **Aggiorna Stato**: Da fare → In corso → Completato
- ✅ **Completa Task**: Completamento rapido
- 📊 **Esporta CSV**: Download dati per analisi
- 🧹 **Pulisci Obsoleti**: Rimozione automatica

## 🚀 Utilizzo

### 1. Accesso alla Dashboard

1. Accedi come **admin**
2. Vai su **"Task AI"** nella sidebar
3. Visualizza le statistiche e i task generati

### 2. Esecuzione Analisi AI

```bash
# Analisi manuale
python cli_ai_analysis.py --analyze-all

# Analisi automatica (cron)
0 2 * * * cd /var/www/gestione_doc && python cli_ai_analysis.py --analyze-all
```

### 3. Gestione Task

#### Via Dashboard Web
- Filtra per stato/priorità/modulo
- Aggiorna stato con note
- Completa task direttamente

#### Via API
```bash
# Aggiorna stato task
curl -X POST /admin/ai/tasks/123/update \
  -d "stato=Completato&note=Revisione completata"

# Esporta task
curl /admin/ai/tasks/export

# Statistiche
curl /admin/ai/tasks/stats
```

## 📊 Monitoraggio e Statistiche

### Metriche Chiave

- **Task Generati**: Numero totale di task AI creati
- **Distribuzione Moduli**: QMS vs FocusMe
- **Stati Task**: Da fare, in corso, completati
- **Priorità**: Critici, alti, media, bassi
- **Scadenze**: Task scaduti o in scadenza

### Report Automatici

```python
# Esempio report JSON
{
  "totali": 45,
  "qms": 28,
  "focusme": 17,
  "da_fare": 12,
  "in_corso": 8,
  "completati": 25,
  "critici": 5,
  "scaduti": 2
}
```

## 🔄 Integrazione con Sistemi Esistenti

### FocusMe AI
- **Task Strategici**: Analisi documenti vecchi, ottimizzazioni
- **Priorità Media/Bassa**: Revisioni consigliate, analisi utilizzo
- **Focus**: Miglioramento processi, efficienza

### QMS (Quality Management System)
- **Task Critici**: Documenti obsoleti, duplicati
- **Priorità Alta/Critica**: Conformità, aggiornamenti urgenti
- **Focus**: Qualità, certificazioni, processi

## 🛠️ Configurazione

### Variabili di Ambiente

```bash
# Configurazione task generator
AI_TASK_CLEANUP_DAYS=30          # Giorni per pulizia task obsoleti
AI_TASK_DEFAULT_ASSIGNEE=admin    # Assegnatario di default
AI_TASK_NOTIFICATION_EMAIL=true   # Notifiche email
```

### Personalizzazione

#### Modifica Priorità
```python
# In ai/task_generator.py
def _determina_priorita_scadenza(tipo_insight):
    if tipo_insight == "obsoleto":
        return "Critica", oggi + timedelta(days=3)  # Personalizza
```

#### Aggiungi Nuovi Tipi
```python
# Aggiungi nuovo tipo di insight
elif tipo_insight == "nuovo_tipo":
    return "Alta", oggi + timedelta(days=10)
```

## 🔍 Troubleshooting

### Problemi Comuni

#### 1. Task Non Generati
```bash
# Verifica analisi AI
python cli_ai_analysis.py --summary

# Controlla log
tail -f logs/app.log | grep "AI"
```

#### 2. Routing Errato
```python
# Verifica logica routing
python -c "from ai.task_generator import determina_modulo_destinazione; print('OK')"
```

#### 3. Dashboard Non Carica
```bash
# Verifica route
curl -I /admin/ai/tasks

# Controlla template
ls templates/admin/ai_tasks.html
```

### Log e Debug

```bash
# Log dettagliati
journalctl -u gestione_doc.service -f

# Test task generator
python test_task_generator.py

# Test integrazione
python test_ai_document_system.py
```

## 📈 Roadmap Futura

### Fasi di Sviluppo

#### Fase 1 ✅ (Completata)
- ✅ Generazione task automatica
- ✅ Routing intelligente QMS/FocusMe
- ✅ Dashboard web
- ✅ API REST

#### Fase 2 🔄 (In Sviluppo)
- 🔄 Notifiche email automatiche
- 🔄 Integrazione con calendario
- 🔄 Report avanzati
- 🔄 Machine Learning per priorità

#### Fase 3 📋 (Pianificata)
- 📋 Integrazione con sistemi esterni
- 📋 Workflow automatizzati
- 📋 Dashboard executive
- 📋 Mobile app

### Miglioramenti Proposti

1. **Notifiche Intelligenti**: Email/SMS per task critici
2. **Escalation Automatica**: Promozione priorità per task scaduti
3. **Analisi Predittiva**: Previsione documenti a rischio
4. **Integrazione Slack**: Notifiche in tempo reale
5. **Dashboard Executive**: Vista strategica per management

## 📚 Riferimenti

### File Principali
- `ai/task_generator.py` - Motore task
- `ai/document_ai_scheduler.py` - Integrazione AI
- `admin_routes.py` - API e route
- `templates/admin/ai_tasks.html` - Dashboard
- `test_task_generator.py` - Test unitari

### API Endpoints
- `GET /admin/ai/tasks` - Dashboard task
- `POST /admin/ai/tasks/{id}/update` - Aggiorna task
- `GET /admin/ai/tasks/export` - Esporta CSV
- `POST /admin/ai/tasks/cleanup` - Pulisci obsoleti
- `GET /admin/ai/tasks/stats` - Statistiche

### Comandi CLI
- `python cli_ai_analysis.py --analyze-all` - Analisi completa
- `python cli_ai_analysis.py --clean-insights` - Pulizia insight
- `python cli_ai_analysis.py --export-csv` - Esporta dati
- `python test_task_generator.py` - Test sistema

---

## 🎉 Conclusione

Il sistema **Auto-Task AI** è ora completamente funzionale e integrato con il sistema di gestione documenti. Fornisce:

- ✅ **Generazione automatica** di task basati su insight AI
- ✅ **Routing intelligente** tra QMS e FocusMe AI
- ✅ **Dashboard completa** per gestione task
- ✅ **API REST** per integrazione esterna
- ✅ **Test completi** per verifica funzionalità

Il sistema è pronto per l'uso in produzione e può essere facilmente esteso per nuove funzionalità future. 