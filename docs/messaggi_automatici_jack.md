# 🤖 Messaggi Automatici Jack Synthia - SYNTHIA.PROMPT.096

## 📋 Panoramica

I messaggi automatici di Jack Synthia forniscono assistenza contestuale intelligente agli utenti, reagendo automaticamente a:
- **Login e navigazione** tra moduli
- **Orario della giornata** (mattina, pomeriggio, sera)
- **Contesto specifico** (documenti critici, task in ritardo, eventi programmati)
- **Ruolo utente** (CEO, Admin, User)

## 🎯 Obiettivi

- **Assistenza Proattiva**: Jack parla senza che l'utente clicchi
- **Personalizzazione**: Messaggi specifici per ruolo e contesto
- **Onboarding**: Guida automatica per nuovi utenti
- **Engagement**: Esperienza coinvolgente e interattiva

## 🔧 Implementazione Tecnica

### 1. Route FastAPI - `routes/synthia_eventi.py`

```python
@router.get("/synthia/ai/evento/{evento}")
async def messaggio_automatico(evento: str, user_role: str = "CEO"):
    """
    Genera messaggi automatici di Jack Synthia basati sull'evento
    """
    pagina_map = {
        "login": "dashboard_ceo",
        "apertura_planner": "focus_planner", 
        "apertura_task": "task_manager",
        "apertura_docs": "docs_overview",
        "apertura_qms": "qms_overview"
    }
    
    pagina = pagina_map.get(evento, "dashboard_ceo")
    messaggio = genera_messaggio_jack(pagina, user_role, fake_kpi_data)
    return JSONResponse(content=messaggio)
```

### 2. Template Base - `templates/admin/base_admin.html`

```html
<!-- Area messaggi automatici Jack Synthia -->
<div id="jack-message-area" class="mb-3"></div>

<script>
window.addEventListener('DOMContentLoaded', async () => {
  const evento = sessionStorage.getItem("jack_evento") || "login";
  sessionStorage.removeItem("jack_evento");
  
  const userRole = "{{ current_user.role if current_user else 'USER' }}";
  
  try {
    const res = await fetch(`/synthia/ai/evento/${evento}?user_role=${userRole}`);
    const data = await res.json();
    
    if (data.messaggio) {
      const msgContainer = document.createElement('div');
      msgContainer.innerHTML = `
        <div class="card shadow-sm p-3 mb-3 border-0" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
          <div class="d-flex align-items-center">
            <img src="/static/img/jack_synthia_realistic.png" width="48" height="48" class="me-3 rounded-circle">
            <div class="flex-grow-1">
              <p class="mb-2"><strong>🎙 Jack Synthia:</strong> ${data.messaggio}</p>
              ${data.azione_url ? `<a href="${data.azione_url}" class="btn btn-sm btn-outline-light">${data.azione_testo}</a>` : ''}
            </div>
            <button type="button" class="btn-close btn-close-white" onclick="this.parentElement.parentElement.remove()"></button>
          </div>
        </div>
      `;
      
      document.querySelector("#jack-message-area")?.prepend(msgContainer);
      
      // Auto-remove dopo 10 secondi
      setTimeout(() => {
        if (msgContainer.parentElement) {
          msgContainer.remove();
        }
      }, 10000);
    }
  } catch (error) {
    console.log('Errore nel caricamento messaggio Jack:', error);
  }
});

// Funzione per impostare eventi Jack prima della navigazione
function setJackEvento(evento) {
  sessionStorage.setItem("jack_evento", evento);
}
</script>
```

### 3. Eventi nei Pulsanti

```html
<button class="sidebar-btn" onclick="setJackEvento('apertura_docs'); location.href='{{ url_for('admin.doc_overview') }}'">
  📊 Panoramica Documentale
</button>
```

## 📝 Messaggi per Ruolo

### 🎯 CEO - Messaggi Strategici

| **Evento** | **Messaggio** |
|------------|---------------|
| **Login** | "🌟 Buongiorno CEO! Pronto per guidare la giornata? Ho analizzato i KPI e ho alcuni suggerimenti strategici." |
| **Dashboard** | "🎯 Benvenuto nella tua dashboard! Ho identificato 3 priorità critiche che richiedono la tua attenzione." |
| **Planner** | "⏰ È il momento perfetto per pianificare il Deep Work! Hai già identificato i blocchi di tempo?" |
| **Task Manager** | "📋 Hai 5 task in corso e 2 in ritardo. Vuoi che ti aiuti a riorganizzare le priorità?" |
| **Docs Overview** | "📄 Gestione documentale! Ho rilevato 3 documenti critici che richiedono la tua attenzione." |
| **QMS Overview** | "🏆 Sistema Qualità! Tutti i processi sono conformi. Vuoi un'analisi dettagliata?" |

### 👨‍💼 Admin - Messaggi Operativi

| **Evento** | **Messaggio** |
|------------|---------------|
| **Login** | "👨‍💼 Buongiorno Admin! Sistema operativo al 100%. Tutto sotto controllo." |
| **Dashboard** | "🔧 Dashboard amministrativa attiva! Ho rilevato 2 notifiche che richiedono attenzione." |
| **Docs Overview** | "📄 Gestione documenti! 3 documenti in attesa di approvazione." |

### 👤 User - Messaggi Produttività

| **Evento** | **Messaggio** |
|------------|---------------|
| **Login** | "👋 Buongiorno! Pronto per una giornata produttiva?" |
| **Planner** | "⏰ Pianificazione personale! Ti suggerisco di iniziare con i task più importanti." |

## 🕐 Personalizzazione Orario

### 🌅 Mattina (6-12)
- Saluto: "🌅 Buongiorno"
- Focus: Pianificazione giornata, priorità
- Energia: Alta produttività

### ☀️ Pomeriggio (12-18)
- Saluto: "☀️ Buon pomeriggio"
- Focus: Esecuzione task, revisioni
- Energia: Mantenimento focus

### 🌆 Sera (18-22)
- Saluto: "🌆 Buonasera"
- Focus: Riepilogo, preparazione domani
- Energia: Riflessione

### 🌙 Notte (22-6)
- Saluto: "🌙 Buonanotte"
- Focus: Rilassamento, disconnessione
- Energia: Bassa

## 🎨 Design e UX

### Stile Messaggio
```css
.jack-message-container .card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.jack-message-container img {
  border: 2px solid white;
  border-radius: 50%;
}
```

### Comportamento
- **Auto-remove**: Dopo 10 secondi
- **Chiusura manuale**: Pulsante X
- **Animazioni**: Fade in/out fluide
- **Responsive**: Adattamento mobile

## 🔄 Eventi Supportati

### Eventi di Navigazione
| **Evento** | **Pagina** | **Trigger** |
|------------|------------|-------------|
| `login` | Dashboard | Accesso utente |
| `apertura_planner` | Focus Planner | Clic su "Planner" |
| `apertura_task` | Task Manager | Clic su "Task" |
| `apertura_docs` | Docs Overview | Clic su "Documenti" |
| `apertura_qms` | QMS Overview | Clic su "Qualità" |
| `apertura_obeya` | Mappa Obeya | Clic su "Mappa" |
| `apertura_kpi` | KPI Dashboard | Clic su "KPI" |

### Eventi Contestuali
| **Evento** | **Contesto** | **Messaggio** |
|------------|--------------|---------------|
| `task_in_ritardo` | Task scadute | "⚠️ Hai X task in ritardo" |
| `documenti_critici` | Documenti critici | "📄 Ci sono X documenti critici" |
| `performance_bassa` | Performance < 70% | "📉 Performance in calo" |

## 🚀 Funzionalità Avanzate

### 1. Messaggi Dinamici dal Backend

```python
def get_ai_tooltip_message(document, action):
    if document.ai_status == 'incompleto':
        return "⚠️ Questo documento è incompleto. Verifica le firme mancanti."
    elif document.ai_status == 'scaduto':
        return "🚨 Documento scaduto! Richiede aggiornamento immediato."
    else:
        return "✅ Documento completo e aggiornato."
```

### 2. Onboarding Progressivo

```javascript
const onboardingMessages = [
    { id: 'first_login', message: '👋 Benvenuto! Sono Jack, il tuo assistente AI.' },
    { id: 'first_planner', message: '⏰ Pianificazione intelligente! Organizza la tua giornata.' },
    { id: 'first_docs', message: '📄 Gestione documentale! Tutto sotto controllo.' }
];
```

### 3. Analytics e Metriche

```javascript
// Traccia l'utilizzo dei messaggi
document.querySelectorAll('.jack-message-container').forEach(function(element) {
    element.addEventListener('shown', function() {
        // Invia analytics
        console.log('Messaggio Jack mostrato:', this.getAttribute('data-evento'));
    });
});
```

## 📊 Configurazione

### Variabili d'Ambiente
```bash
# .env
JACK_SYNTHIA_ENABLED=true
JACK_MESSAGE_DURATION=10000  # 10 secondi
JACK_AUTO_REMOVE=true
```

### Configurazione Backend
```python
# config.py
JACK_SYNTHIA_CONFIG = {
    'enabled': True,
    'message_duration': 10000,
    'auto_remove': True,
    'max_messages_per_session': 5
}
```

## ✅ Checklist Implementazione

- [x] **Route FastAPI** per messaggi automatici
- [x] **Template base** con area messaggi
- [x] **JavaScript** per gestione eventi
- [x] **Eventi sidebar** per navigazione
- [x] **Messaggi personalizzati** per ruolo
- [x] **Personalizzazione orario** (mattina/pomeriggio/sera)
- [x] **Auto-remove** dopo 10 secondi
- [x] **Chiusura manuale** con pulsante X
- [x] **Stile coerente** con Synthia
- [x] **Registrazione blueprint** in app.py
- [x] **Documentazione completa**

## 🎯 Prossimi Passi

### 1. Estensioni Immediate
- **Messaggi basati su AI predittiva** (stress, performance)
- **Auto-messaggi programmati** (cron jobs)
- **Modalità "Jack Coach"** in background

### 2. Integrazione Avanzata
- **Chatbot completo** per conversazioni
- **Voice commands** per interazioni vocali
- **Machine Learning** per personalizzazione

### 3. Analytics e Ottimizzazione
- **Tracking utilizzo** messaggi
- **A/B testing** per ottimizzazione
- **Feedback loop** per miglioramenti

## 🔧 Troubleshooting

### Problemi Comuni

1. **Messaggi non appaiono**
   - Verifica che il blueprint sia registrato
   - Controlla la console per errori JavaScript
   - Verifica che l'endpoint `/synthia/ai/evento/` risponda

2. **Eventi non funzionano**
   - Verifica che `setJackEvento()` sia chiamato
   - Controlla che `sessionStorage` funzioni
   - Verifica che l'evento sia mappato correttamente

3. **Stile non corretto**
   - Verifica che Bootstrap sia caricato
   - Controlla che il CSS sia applicato
   - Verifica che l'immagine Jack sia presente

---

*Documentazione creata per SYNTHIA.PROMPT.096 - Messaggi Automatici Jack Synthia* 