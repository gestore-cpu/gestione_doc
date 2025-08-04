# 🤖 Guida Integrazione Jack Synthia

## 📋 Panoramica

Jack Synthia è l'assistente AI universale di tutto l'ecosistema SYNTHIA. Questa guida spiega come utilizzare tutti i componenti e funzionalità disponibili.

## 🧩 Componenti Disponibili

### 1. **Onboarding Interattivo** (`onboarding_docs.html`)

**Scopo**: Guida passo-passo per nuovi utenti del modulo DOCS.

**Utilizzo**:
```html
{% include 'components/onboarding_docs.html' %}
```

**Caratteristiche**:
- ✅ Messaggi sequenziali personalizzati
- ✅ Evidenziazione elementi con animazioni
- ✅ Pulsanti azione contestuali
- ✅ Persistenza con localStorage
- ✅ Personalizzazione per ruolo utente

**Configurazione**:
```javascript
// In jack_onboarding.js
const onboardingConfig = {
  module: 'docs',
  messages: [
    {
      text: "Ciao {{nome}}! 👋 Benvenuto nel modulo documenti!",
      action: null,
      highlight: null
    },
    // ... altri messaggi
  ]
};
```

### 2. **Tooltip Permanenti** (`jack_tooltips.html`)

**Scopo**: Spiegazioni contestuali per pulsanti e funzioni.

**Utilizzo**:
```html
{% include 'components/jack_tooltips.html' %}
```

**Attributi HTML**:
```html
<button data-jack-tooltip class="btn btn-primary">Carica Documento</button>
<button class="btn-upload">Upload</button>
<button class="btn-download">Download</button>
<button class="btn-sign">Firma</button>
<button class="btn-analyze">Analizza</button>
```

**Configurazione**:
```javascript
// In jack_tooltips.js
const tooltipConfigs = [
  {
    selector: '[data-jack-tooltip]',
    message: '🤖 Jack dice: Clicca qui per vedere i dettagli',
    position: 'top'
  }
  // ... altre configurazioni
];
```

### 3. **Messaggi Automatici** (`jack_messages.html`)

**Scopo**: Messaggi contestuali basati su azioni, tempo e navigazione.

**Utilizzo**:
```html
{% include 'components/jack_messages.html' %}
```

**Eventi Automatici**:
```html
<button data-jack-event="upload_document">Carica</button>
<button data-jack-event="sign_document">Firma</button>
<button data-jack-event="download_document">Scarica</button>
```

**Messaggi Programmabili**:
```javascript
// Mostra messaggio personalizzato
window.showJackMessage({
  type: 'success',
  title: '🎉 Completato!',
  text: 'Operazione eseguita con successo.',
  action: {
    text: 'Vedi Dettagli',
    url: '/docs/details'
  }
});
```

### 4. **Macro Universale** (`synthia_message.html`)

**Scopo**: Componente riutilizzabile per messaggi Jack in tutti i moduli.

**Utilizzo**:
```html
{% from 'components/synthia_message.html' import synthia_message %}

{{ synthia_message(
    messaggio="🤖 Jack dice: Questo è un messaggio di esempio",
    azione_url="/docs/help",
    azione_testo="Vedi Guida",
    tipo="info",
    dismissible=true
) }}
```

## 🎨 Stili e Temi

### Gradienti Disponibili

```css
/* Info (Blu) */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Success (Verde) */
background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);

/* Warning (Arancione) */
background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);

/* Error (Rosso) */
background: linear-gradient(135deg, #F44336 0%, #D32F2F 100%);
```

### Animazioni

```css
/* Slide In */
@keyframes jackMessageSlideIn {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Pulse */
@keyframes jackPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}
```

## 🔧 Integrazione nei Moduli

### Modulo DOCS

```html
<!-- In templates/admin/base_admin.html -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/jack_onboarding.css') }}">
<script src="{{ url_for('static', filename='js/jack_onboarding.js') }}"></script>

{% include 'components/onboarding_docs.html' %}
{% include 'components/jack_tooltips.html' %}
{% include 'components/jack_messages.html' %}
```

### Altri Moduli

```html
<!-- In templates/base.html di ogni modulo -->
{% include 'components/synthia_message.html' %}

<script src="{{ url_for('static', filename='js/synthia_integration.js') }}"></script>
```

## 📱 Responsive Design

Tutti i componenti sono ottimizzati per dispositivi mobili:

```css
@media (max-width: 768px) {
  .jack-message-header {
    padding: 12px 15px;
  }
  
  .jack-avatar {
    width: 40px;
    height: 40px;
  }
  
  .jack-action-btn {
    padding: 6px 12px;
    font-size: 11px;
  }
}
```

## 🚀 API e Funzioni

### Funzioni Globali

```javascript
// Mostra messaggio
window.showJackMessage(config);

// Reset onboarding
window.JackOnboarding.reset();

// Mostra tooltip
window.jackTooltips.showTooltip(element, message, position);

// Rimuovi messaggio
window.jackMessages.removeMessage(messageId);
```

### Eventi Personalizzati

```javascript
// Trigger evento Jack
document.dispatchEvent(new CustomEvent('jack-event', {
  detail: { type: 'upload_document', data: { docId: 123 } }
}));

// Ascolta eventi Jack
document.addEventListener('jack-event', (e) => {
  console.log('Evento Jack:', e.detail);
});
```

## 🎯 Best Practices

### 1. **Performance**
- ✅ Usa lazy loading per componenti pesanti
- ✅ Minimizza le chiamate API
- ✅ Ottimizza le animazioni

### 2. **Accessibilità**
- ✅ Supporta navigazione da tastiera
- ✅ Usa contrasti appropriati
- ✅ Fornisci alternative testuali

### 3. **UX**
- ✅ Messaggi brevi e chiari
- ✅ Azioni contestuali
- ✅ Feedback immediato

### 4. **Manutenibilità**
- ✅ Codice modulare
- ✅ Configurazioni centralizzate
- ✅ Documentazione aggiornata

## 🔍 Debug e Troubleshooting

### Console Logs

```javascript
// Abilita debug
window.JACK_DEBUG = true;

// Log eventi
console.log('Jack Event:', event);
```

### Controlli Comuni

1. **Onboarding non si mostra**:
   - Controlla `localStorage.getItem("onboarding_docs_completato")`
   - Verifica che il modulo sia DOCS

2. **Tooltip non funzionano**:
   - Controlla i selettori CSS
   - Verifica che gli elementi abbiano le classi corrette

3. **Messaggi non appaiono**:
   - Controlla che `jack-message-area` esista
   - Verifica la configurazione dei messaggi

## 📊 Analytics e Tracking

```javascript
// Traccia eventi Jack
function trackJackEvent(event, data) {
  if (window.gtag) {
    gtag('event', 'jack_synthia', {
      event_category: 'user_interaction',
      event_label: event,
      value: data
    });
  }
}
```

## 🎨 Personalizzazione

### Tema Personalizzato

```css
:root {
  --jack-primary: #667eea;
  --jack-secondary: #764ba2;
  --jack-success: #4CAF50;
  --jack-warning: #FF9800;
  --jack-error: #F44336;
}
```

### Messaggi Personalizzati

```javascript
// Estendi configurazione
window.JACK_CONFIG = {
  messages: {
    custom_event: {
      type: 'info',
      title: '🎯 Personalizzato',
      text: 'Il tuo messaggio personalizzato'
    }
  }
};
```

## 🚀 Deployment

### File da Includere

```
static/
├── css/
│   ├── jack_onboarding.css
│   └── jack_tooltips.css
├── js/
│   ├── jack_onboarding.js
│   ├── jack_tooltips.js
│   └── synthia_integration.js
└── img/
    └── jack_synthia_realistic.png

templates/
└── components/
    ├── onboarding_docs.html
    ├── jack_tooltips.html
    ├── jack_messages.html
    └── synthia_message.html
```

### Verifica Installazione

```bash
# Controlla file
ls -la static/css/jack_*.css
ls -la static/js/jack_*.js
ls -la templates/components/jack_*.html

# Test funzionalità
curl -s http://localhost:5000/docs/ | grep -i jack
```

---

**🎯 Jack Synthia è ora completamente integrato in tutto l'ecosistema SYNTHIA!**

Per supporto tecnico o domande, consulta la documentazione completa o contatta il team di sviluppo. 