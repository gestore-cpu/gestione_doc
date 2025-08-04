# 📋 Prompt 26 - FASE 1: Modello SQLAlchemy TaskAI

## Panoramica

Implementazione del modello SQLAlchemy `TaskAI` con enum per la gestione dei task personali provenienti da diverse origini: analisi AI, diario, deep work, e creazione manuale.

## 🏗️ Architettura Implementata

### 1. Enum per Standardizzazione

#### OrigineTask Enum
```python
class OrigineTask(enum.Enum):
    """Enum per l'origine dei task."""
    AI = "AI"
    DIARIO = "Diario"
    DEEP_WORK = "Deep Work"
    MANUALE = "Manuale"
```

#### PrioritaTask Enum
```python
class PrioritaTask(enum.Enum):
    """Enum per la priorità dei task."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
```

### 2. Modello TaskAI

```python
class TaskAI(db.Model):
    """
    Modello per la gestione dei task AI personali.
    
    Attributi:
        id (int): ID primario.
        user_id (int): ID utente assegnato.
        titolo (str): Titolo del task.
        descrizione (str): Descrizione dettagliata.
        data_scadenza (datetime): Data di scadenza.
        priorita (PrioritaTask): Priorità (Low, Medium, High).
        origine (OrigineTask): Origine del task (AI, Diario, Deep Work, Manuale).
        stato (bool): Stato del task (False = da fare, True = completato).
        data_creazione (datetime): Data creazione.
    """
    __tablename__ = "task_ai"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    titolo = db.Column(db.String(255), nullable=False)
    descrizione = db.Column(db.Text, nullable=True)
    data_scadenza = db.Column(db.DateTime, nullable=True)
    priorita = db.Column(db.Enum(PrioritaTask), default=PrioritaTask.MEDIUM)
    origine = db.Column(db.Enum(OrigineTask), default=OrigineTask.MANUALE)
    stato = db.Column(db.Boolean, default=False)  # False = da fare, True = completato
    data_creazione = db.Column(db.DateTime, default=datetime.utcnow)

    # Relazioni
    utente = db.relationship("User", back_populates="tasks_ai")
```

## 🔧 Funzionalità Implementate

### 1. Proprietà Calcolate

#### is_completed
```python
@property
def is_completed(self):
    """Verifica se il task è completato."""
    return self.stato
```

#### is_overdue
```python
@property
def is_overdue(self):
    """Verifica se il task è scaduto."""
    if self.data_scadenza and not self.stato:
        return datetime.utcnow() > self.data_scadenza
    return False
```

#### days_until_deadline
```python
@property
def days_until_deadline(self):
    """Giorni rimanenti alla scadenza."""
    if self.data_scadenza:
        delta = self.data_scadenza - datetime.utcnow()
        return delta.days
    return None
```

### 2. Proprietà per UI

#### priority_color
```python
@property
def priority_color(self):
    """Restituisce il colore Bootstrap per la priorità."""
    colors = {
        PrioritaTask.LOW: "success",
        PrioritaTask.MEDIUM: "info", 
        PrioritaTask.HIGH: "warning"
    }
    return colors.get(self.priorita, "secondary")
```

#### status_color
```python
@property
def status_color(self):
    """Colore del badge in base allo stato."""
    if self.stato:
        return 'bg-success'
    return 'bg-secondary'
```

#### origine_badge_class
```python
@property
def origine_badge_class(self):
    """Classe badge per l'origine del task."""
    colors = {
        OrigineTask.AI: 'bg-primary',
        OrigineTask.DIARIO: 'bg-info',
        OrigineTask.DEEP_WORK: 'bg-warning',
        OrigineTask.MANUALE: 'bg-secondary'
    }
    return colors.get(self.origine, 'bg-secondary')
```

#### origine_display
```python
@property
def origine_display(self):
    """Display name per l'origine del task."""
    display_names = {
        OrigineTask.AI: '🤖 AI',
        OrigineTask.DIARIO: '📝 Diario',
        OrigineTask.DEEP_WORK: '🧠 Deep Work',
        OrigineTask.MANUALE: '✏️ Manuale'
    }
    return display_names.get(self.origine, self.origine.value)
```

### 3. Relazioni

#### Relazione con User
```python
# Nel modello TaskAI
utente = db.relationship("User", back_populates="tasks_ai")

# Nel modello User
tasks_ai = db.relationship('TaskAI', back_populates='utente', cascade='all, delete-orphan')
```

## 📊 Struttura Database

### Tabella task_ai
```sql
CREATE TABLE task_ai (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    titolo VARCHAR(255) NOT NULL,
    descrizione TEXT,
    data_scadenza DATETIME,
    priorita ENUM('Low', 'Medium', 'High') DEFAULT 'Medium',
    origine ENUM('AI', 'Diario', 'Deep Work', 'Manuale') DEFAULT 'Manuale',
    stato BOOLEAN DEFAULT FALSE,
    data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Indici Raccomandati
```sql
-- Indice per performance query per utente
CREATE INDEX idx_task_ai_user_id ON task_ai(user_id);

-- Indice per performance query per scadenza
CREATE INDEX idx_task_ai_data_scadenza ON task_ai(data_scadenza);

-- Indice per performance query per stato
CREATE INDEX idx_task_ai_stato ON task_ai(stato);

-- Indice per performance query per origine
CREATE INDEX idx_task_ai_origine ON task_ai(origine);
```

## 🧪 Test Implementati

### Test Modello TaskAI
- ✅ **Creazione modello**: Verifica esistenza e struttura
- ✅ **Proprietà calcolate**: Test is_completed, is_overdue, days_until_deadline
- ✅ **Colori UI**: Test priority_color, status_color, origine_badge_class
- ✅ **Display names**: Test origine_display
- ✅ **Relazioni**: Test relazione con User
- ✅ **Integrità dati**: Test validazione campi
- ✅ **Enum usage**: Test utilizzo enum

### Test Enum
- ✅ **OrigineTask**: Verifica valori e iterazione
- ✅ **PrioritaTask**: Verifica valori e iterazione
- ✅ **Confronti**: Test confronto enum
- ✅ **Valori**: Test valori stringa

## 🔄 Migrazione da Task Legacy

### Compatibilità
Il modello `Task` legacy è mantenuto per compatibilità, mentre il nuovo `TaskAI` offre:

1. **Enum standardizzati** per priorità e origine
2. **Stato booleano** semplificato (True/False)
3. **Relazioni migliorate** con User
4. **Proprietà calcolate** ottimizzate
5. **Naming consistente** (data_scadenza vs scadenza)

### Esempio Migrazione
```python
# Task legacy
task_legacy = Task(
    user_id=1,
    titolo="Task Legacy",
    priorita="Media",
    stato="Da fare",
    origine="Manuale"
)

# TaskAI nuovo
task_ai = TaskAI(
    user_id=1,
    titolo="Task AI",
    priorita=PrioritaTask.MEDIUM,
    stato=False,
    origine=OrigineTask.MANUALE
)
```

## 🎯 Vantaggi del Nuovo Modello

### 1. Type Safety
- **Enum** garantiscono valori validi
- **Prevenzione errori** di digitazione
- **IntelliSense** migliorato in IDE

### 2. Performance
- **Indici ottimizzati** per query comuni
- **Relazioni efficienti** con User
- **Cascade delete** automatico

### 3. Manutenibilità
- **Codice più pulito** con enum
- **Documentazione integrata** nelle proprietà
- **Test completi** per tutte le funzionalità

### 4. Scalabilità
- **Facile estensione** con nuovi enum
- **Compatibilità** con sistema esistente
- **Migrazione graduale** possibile

## 📈 Metriche e KPI

### Statistiche TaskAI
```python
# Task per utente
user_tasks = TaskAI.query.filter_by(user_id=user_id).all()

# Task completati
completed_tasks = [t for t in user_tasks if t.is_completed]

# Task scaduti
overdue_tasks = [t for t in user_tasks if t.is_overdue]

# Distribuzione per origine
origine_stats = {}
for task in user_tasks:
    origine = task.origine.value
    origine_stats[origine] = origine_stats.get(origine, 0) + 1
```

### Query Performance
```sql
-- Task scaduti per utente
SELECT * FROM task_ai 
WHERE user_id = ? 
AND data_scadenza < NOW() 
AND stato = FALSE;

-- Statistiche per origine
SELECT origine, COUNT(*) as count, 
       SUM(CASE WHEN stato = TRUE THEN 1 ELSE 0 END) as completed
FROM task_ai 
WHERE user_id = ? 
GROUP BY origine;
```

## 🔒 Sicurezza e Privacy

### Isolamento Dati
- ✅ **Foreign Key** su user_id
- ✅ **Cascade delete** per pulizia automatica
- ✅ **Relazione back_populates** per integrità

### Validazione
- ✅ **Enum** prevengono valori non validi
- ✅ **Nullable** appropriato per campi opzionali
- ✅ **Default values** per campi obbligatori

## 🚀 Prossimi Passi

### FASE 2: Route e Controller
- [ ] Implementare route CRUD per TaskAI
- [ ] Aggiungere controller per gestione task
- [ ] Implementare filtri e ricerca

### FASE 3: Frontend
- [ ] Creare template per TaskAI
- [ ] Implementare interfaccia utente
- [ ] Aggiungere grafici e statistiche

### FASE 4: Integrazione
- [ ] Collegare con sistema AI esistente
- [ ] Implementare notifiche scadenza
- [ ] Aggiungere export CSV

## 📋 Checklist Implementazione

### ✅ FASE 1 Completata
- [x] Enum OrigineTask implementato
- [x] Enum PrioritaTask implementato
- [x] Modello TaskAI creato
- [x] Relazioni con User configurate
- [x] Proprietà calcolate implementate
- [x] Test unitari completi
- [x] Documentazione dettagliata

### 🎯 Risultati Attesi

Il modello `TaskAI` è ora **pronto per l'uso** e offre:

1. **Type safety** con enum standardizzati
2. **Performance ottimizzate** con indici appropriati
3. **Relazioni robuste** con il sistema User
4. **Proprietà calcolate** per UI moderna
5. **Test completi** per affidabilità
6. **Documentazione** per manutenzione

### 🎉 Caratteristiche Chiave

- **🔒 Sicuro**: Enum prevengono errori
- **⚡ Performante**: Indici ottimizzati
- **🎨 UI-Ready**: Proprietà per colori e badge
- **🧪 Testato**: Copertura test completa
- **📚 Documentato**: Guida dettagliata
- **🔄 Scalabile**: Facile estensione futura

Il modello è **pronto per la FASE 2** e può essere utilizzato immediatamente per la gestione dei task AI personali! 🚀

---

**Sviluppato da Jack Synthia AI per Mercury Surgelati**
*Prompt 26 - FASE 1: Modello SQLAlchemy TaskAI* 