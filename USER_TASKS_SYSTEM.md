# 📋 Sistema Task Personali Utente

## Panoramica

Il sistema di task personali permette a ogni utente di gestire i propri task provenienti da diverse origini: analisi AI, diario, deep work, e creazione manuale. Offre un'interfaccia completa per visualizzazione, gestione e analisi dei task personali.

## 🏗️ Architettura del Sistema

### Componenti Principali

#### 1. Modello Task (`models.py`)
```python
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    titolo = db.Column(db.String(200), nullable=False)
    descrizione = db.Column(db.Text, nullable=True)
    priorita = db.Column(db.String(20), default="Media")
    stato = db.Column(db.String(20), default="Da fare")
    scadenza = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.String(150), nullable=False)
    origine = db.Column(db.String(50), default="Manuale")
```

#### 2. Route Utente (`routes/user_routes.py`)
```python
@user_bp.route('/my_tasks')
@login_required
def my_tasks():
    """Visualizza pagina task personali"""

@user_bp.route('/my_tasks/data')
@login_required
def my_tasks_data():
    """Restituisce dati JSON task"""

@user_bp.route('/my_tasks/complete/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    """Completa un task"""

@user_bp.route('/my_tasks/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    """Elimina un task"""

@user_bp.route('/my_tasks/add', methods=['POST'])
@login_required
def add_task():
    """Aggiunge un nuovo task"""

@user_bp.route('/my_tasks/export')
@login_required
def export_my_tasks():
    """Esporta task in CSV"""
```

#### 3. Template Task (`templates/user/user_tasks.html`)
- **Dashboard moderna** con Bootstrap 5
- **Statistiche card** (totali, completati, in attesa, scaduti)
- **Filtri avanzati** (ricerca, priorità, stato, origine, scadenza)
- **Grafici interattivi** (distribuzione origine e priorità)
- **Tabella responsive** con azioni
- **Modal per aggiunta** nuovi task

## 📊 Funzionalità

### 1. Visualizzazione Task
- **Lista completa** dei task personali
- **Statistiche dashboard** in tempo reale
- **Filtri avanzati** per ricerca e ordinamento
- **Grafici interattivi** per analisi
- **Design responsive** per mobile

### 2. Gestione Task
- **Completamento** con un click
- **Eliminazione** con conferma
- **Aggiunta manuale** tramite modal
- **Modifica stato** automatica
- **Tracciamento** date creazione/completamento

### 3. Filtri e Ricerca
- **Ricerca testuale** in titolo e descrizione
- **Filtro priorità** (Bassa, Media, Alta, Critica)
- **Filtro stato** (Da fare, In corso, Completato, Annullato)
- **Filtro origine** (AI, Diario, Deep Work, Manuale)
- **Filtro scadenza** (Oggi, Settimana, Scaduti, Senza scadenza)

### 4. Statistiche e Grafici
- **Distribuzione per origine** (grafico a torta)
- **Distribuzione per priorità** (grafico a barre)
- **Metriche dashboard** (totali, completati, in attesa, scaduti)
- **Aggiornamento automatico** dei dati

### 5. Esportazione Dati
- **Formato CSV** compatibile con Excel
- **Campi completi** (ID, Titolo, Descrizione, Priorità, Stato, Origine, Scadenza, Date)
- **Nome file** con timestamp automatico
- **Solo dati personali** dell'utente

## 🔧 Configurazione

### Proprietà Task
```python
# Proprietà calcolate
task.is_completed          # True se completato
task.is_overdue           # True se scaduto
task.days_until_deadline  # Giorni alla scadenza
task.priority_color       # Classe CSS per priorità
task.status_color         # Classe CSS per stato
task.origine_badge_class  # Classe CSS per origine
task.origine_display      # Nome visualizzato origine
```

### Badge e Colori
```python
# Priorità
"Bassa": "success" (🟢)
"Media": "info" (🟡)
"Alta": "warning" (🔴)
"Critica": "danger" (⚫)

# Stato
"Da fare": "bg-secondary" (⏳)
"In corso": "bg-warning" (🔄)
"Completato": "bg-success" (✅)
"Annullato": "bg-danger" (❌)

# Origine
"AI": "bg-primary" (🤖)
"Diario": "bg-info" (📝)
"Deep Work": "bg-warning" (🧠)
"Manuale": "bg-secondary" (✏️)
```

## 🚀 Utilizzo

### 1. Accesso Task
```
URL: /user/my_tasks
Ruolo: User autenticato
```

### 2. Visualizzazione
- **Caricamento automatico** all'apertura pagina
- **Statistiche in tempo reale** nelle card
- **Grafici interattivi** per analisi
- **Tabella ordinabile** per colonne

### 3. Gestione Task
```javascript
// Completamento task
completeTask(taskId);

// Eliminazione task
deleteTask(taskId);

// Aggiunta task
document.getElementById('addTaskForm').submit();
```

### 4. Filtri
```javascript
// Reset filtri
resetFilters();

// Applicazione filtri
filterTasks();
```

### 5. Esportazione
```python
# URL per esportazione CSV
/user/my_tasks/export
```

## 📈 Metriche e KPI

### Statistiche Dashboard
- **Task totali**: Numero complessivo
- **Completati**: Task finiti
- **In attesa**: Task da fare
- **Scaduti**: Task oltre scadenza

### Distribuzione per Origine
- **AI**: Task generati automaticamente
- **Diario**: Task dal diario personale
- **Deep Work**: Task da sessioni deep work
- **Manuale**: Task creati manualmente

### Distribuzione per Priorità
- **Bassa**: Task non urgenti
- **Media**: Task standard
- **Alta**: Task importanti
- **Critica**: Task urgenti

## 🔒 Sicurezza e Privacy

### Isolamento Dati
- ✅ **Filtro utente**: Solo task dell'utente autenticato
- ✅ **Controllo accessi**: `@login_required` su tutte le route
- ✅ **Validazione**: Controllo ID utente e task
- ✅ **Sanitizzazione**: Dati puliti prima visualizzazione

### GDPR Compliance
- ✅ **Minimizzazione**: Solo dati necessari
- ✅ **Trasparenza**: Utente informato del tracciamento
- ✅ **Diritto di accesso**: Visualizzazione propri task
- ✅ **Diritto di portabilità**: Esportazione CSV

### Privacy
- ✅ **Dati personali**: Solo propri task
- ✅ **Nessuna condivisione**: Task isolati per utente
- ✅ **Controllo**: Utente può vedere solo i propri task
- ✅ **Sicurezza**: Protezione da accessi non autorizzati

## 🛠️ Manutenzione

### Log Files
```
/var/log/gestione_doc/user_tasks.log
```

### Database
```sql
-- Verifica task utente specifico
SELECT * FROM tasks 
WHERE user_id = 1 
ORDER BY created_at DESC;

-- Statistiche utente
SELECT 
    origine,
    COUNT(*) as count,
    SUM(CASE WHEN stato = 'Completato' THEN 1 ELSE 0 END) as completed
FROM tasks 
WHERE user_id = 1 
GROUP BY origine;

-- Task scaduti
SELECT * FROM tasks 
WHERE user_id = 1 
AND scadenza < NOW() 
AND stato NOT IN ('Completato', 'Annullato');
```

### Performance
```sql
-- Indici per performance
CREATE INDEX idx_tasks_user_id 
ON tasks(user_id);

CREATE INDEX idx_tasks_scadenza 
ON tasks(scadenza);

CREATE INDEX idx_tasks_stato 
ON tasks(stato);

CREATE INDEX idx_tasks_origine 
ON tasks(origine);
```

## 🔄 Aggiornamenti

### Versioni
- **v1.0**: Sistema base con CRUD
- **v1.1**: Filtri avanzati
- **v1.2**: Grafici e statistiche
- **v1.3**: Esportazione CSV
- **v1.4**: Design responsive

### Roadmap
- **v2.0**: Notifiche scadenza
- **v2.1**: Collaborazione task
- **v2.2**: Template task
- **v2.3**: Integrazione calendario

## 📞 Supporto

### Contatti
- **Sviluppatore**: Jack Synthia AI
- **Email**: ai@mercurysurgelati.org
- **Documentazione**: `/docs/user_tasks`

### Troubleshooting
1. **Task non visibili**: Verifica filtro utente
2. **Grafici non aggiornati**: Controlla dati origine
3. **CSV non scarica**: Verifica permessi file
4. **Performance lente**: Ottimizza query database

## 📋 Checklist Implementazione

### ✅ Backend
- [x] Modello Task esteso con user_id e origine
- [x] Route per visualizzazione task
- [x] Route per dati JSON
- [x] Route per completamento task
- [x] Route per eliminazione task
- [x] Route per aggiunta task
- [x] Route per esportazione CSV
- [x] Calcolo statistiche
- [x] Gestione errori
- [x] Controllo accessi

### ✅ Frontend
- [x] Template responsive
- [x] Statistiche card
- [x] Filtri avanzati
- [x] Grafici Chart.js
- [x] Tabella interattiva
- [x] Modal aggiunta task
- [x] Azioni task (completa/elimina)
- [x] Ricerca in tempo reale

### ✅ Sicurezza
- [x] Isolamento dati utente
- [x] Controllo accessi
- [x] Validazione input
- [x] Sanitizzazione dati
- [x] Protezione CSRF

### ✅ Privacy
- [x] GDPR compliance
- [x] Minimizzazione dati
- [x] Trasparenza
- [x] Diritto di accesso
- [x] Diritto di portabilità

### ✅ Testing
- [x] Test unitari
- [x] Test integrazione
- [x] Test sicurezza
- [x] Test performance
- [x] Test responsività

## 🎯 Risultati Attesi

### Per l'Utente
- **Gestione completa** dei task personali
- **Interfaccia intuitiva** e moderna
- **Filtri avanzati** per organizzazione
- **Statistiche visive** per analisi
- **Esportazione dati** per backup

### Per il Sistema
- **Tracciabilità completa** delle attività
- **Performance ottimizzate** per grandi dataset
- **Sicurezza garantita** con isolamento dati
- **Scalabilità** per utenti multipli

### Per la Compliance
- **GDPR compliance** completa
- **Privacy by design** implementata
- **Audit trail** per verifiche
- **Controllo accessi** robusto

## 📊 Esempio Dati JSON
```json
{
  "success": true,
  "tasks": [
    {
      "id": 1,
      "titolo": "Revisione documenti HACCP",
      "descrizione": "Controllare aggiornamenti procedure HACCP",
      "priorita": "Alta",
      "stato": "Da fare",
      "origine": "AI",
      "origine_display": "🤖 AI",
      "scadenza": "2024-01-20 17:00",
      "created_at": "2024-01-15 10:30",
      "completed_at": null,
      "is_completed": false,
      "is_overdue": false,
      "days_until_deadline": 5,
      "priority_color": "warning",
      "status_color": "bg-secondary",
      "origine_badge_class": "bg-primary"
    }
  ]
}
```

### 🎯 Caratteristiche Chiave

- **🔒 Sicuro**: Isolamento dati per utente
- **📱 Responsive**: Design mobile-friendly
- **⚡ Performante**: Query ottimizzate
- **🎨 Moderno**: UI/UX contemporanea
- **📊 Informativo**: Statistiche dettagliate
- **🔍 Flessibile**: Filtri avanzati
- **📈 Analitico**: Grafici interattivi

Il sistema è **pronto per la produzione** e offre agli utenti una gestione completa e moderna dei propri task personali! 🚀

---

**Sistema sviluppato da Jack Synthia AI per Mercury Surgelati**
*Privacy by Design - GDPR Compliant* 