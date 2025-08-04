# 🤖 Onboarding AI Interattivo - Jack Synthia (SYNTHIA.DOCS.PROMPT.093)

## 📋 Panoramica

L'onboarding AI interattivo di Jack Synthia fornisce una guida passo-passo automatica per nuovi utenti del modulo DOCS, con messaggi animati, frecce, e la voce visiva di Jack.

## 🎯 Obiettivi

- **Guida Automatica**: Onboarding al primo accesso senza intervento manuale
- **Evidenziazione Elementi**: Overlay semi-trasparente con frecce e box animati
- **Messaggi Contestuali**: Spiegazioni specifiche per ogni pulsante e funzione
- **Persistenza**: Guida visibile solo alla prima visita, salvata in localStorage
- **Controllo Ruoli**: Attivazione automatica per user/auditor, manuale per admin/CEO

## 🔧 Implementazione Tecnica

### 1. File JavaScript - `static/js/onboarding_jack.js`

```javascript
class JackOnboarding {
    constructor() {
        this.currentStep = 0;
        this.steps = [];
        this.isActive = false;
        this.userRole = this.getUserRole();
        this.init();
    }

    // Verifica se mostrare l'onboarding
    shouldShowOnboarding() {
        const onboardingShown = localStorage.getItem('docs_onboarding_shown');
        const userRole = this.userRole.toUpperCase();
        
        // Per utenti normali: mostra sempre al primo accesso
        if (userRole === 'USER' || userRole === 'AUDITOR') {
            return !onboardingShown;
        }
        
        // Per admin/CEO: solo se richiesto manualmente
        return false;
    }
}
```

### 2. File CSS - `static/css/onboarding_jack.css`

```css
/* Overlay principale */
.jack-onboarding-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.7);
    z-index: 9999;
    backdrop-filter: blur(2px);
    animation: fadeIn 0.3s ease-in-out;
}

/* Evidenziazione elementi target */
.jack-onboarding-highlight {
    position: relative;
    z-index: 10000 !important;
    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.8), 0 0 20px rgba(102, 126, 234, 0.4) !important;
    border-radius: 8px !important;
    animation: pulse 2s infinite;
}
```

### 3. Template Base - `templates/admin/base_admin.html`

```html
<!-- Inclusione file CSS e JS -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/onboarding_jack.css') }}">
<script src="{{ url_for('static', filename='js/onboarding_jack.js') }}"></script>

<!-- Attributo ruolo utente -->
<body data-user-role="{{ current_user.role if current_user else 'USER' }}">
```

## 📝 Passi dell'Onboarding

### Step 1: Upload Documenti
- **Target**: `#uploadBtn, .btn-upload, [data-onboarding="upload"]`
- **Messaggio**: "📤 Carica un nuovo documento PDF, firmato e con nome chiaro."
- **Posizione**: Bottom
- **Suggerimento**: "💡 Usa nomi descrittivi come 'Manuale_HACCP_2024.pdf'"

### Step 2: Analisi AI
- **Target**: `.btn-analyze-ai, [data-onboarding="analyze"]`
- **Messaggio**: "🧠 Clicca qui per lanciare l'analisi AI automatica sul documento."
- **Posizione**: Left
- **Suggerimento**: "🔍 Analizzo: conformità, completezza, rischi"

### Step 3: Firma Digitale
- **Target**: `.btn-sign, [data-onboarding="sign"]`
- **Messaggio**: "✍️ Firma il documento se hai l'autorizzazione."
- **Posizione**: Top
- **Suggerimento**: "🔐 Firma sicura con 2FA e hash SHA256"

### Step 4: Esporta Dati
- **Target**: `.btn-export, [data-onboarding="export"]`
- **Messaggio**: "⬇️ Esporta l'elenco documenti critici per audit, riunioni o archiviazione."
- **Posizione**: Right
- **Suggerimento**: "📊 Formati: CSV, PDF, Excel per diversi usi"

### Step 5: Aiuto Jack
- **Target**: `.btn-help-jack, [data-onboarding="help"]`
- **Messaggio**: "❓ Hai bisogno d'aiuto? Jack ti guida sempre da qui."
- **Posizione**: Bottom
- **Suggerimento**: "🎯 Guida contestuale, tooltip, messaggi automatici"

## 🎨 Design e UX

### Overlay Semi-trasparente
- **Background**: `rgba(0, 0, 0, 0.7)` con blur
- **Z-index**: 9999 per sovrapporsi a tutto
- **Animazione**: Fade in 0.3s

### Container Messaggi
- **Stile**: Gradiente Synthia (`#667eea` → `#764ba2`)
- **Bordi**: 16px radius con bordo bianco semi-trasparente
- **Ombra**: 20px blur con opacità 0.3
- **Animazione**: Slide in 0.4s

### Evidenziazione Elementi
- **Box-shadow**: Blu Synthia con glow
- **Animazione**: Pulse 2s infinite
- **Z-index**: 10000 per essere sopra l'overlay
- **Scroll**: Auto-scroll all'elemento evidenziato

### Controlli
- **Layout**: Flex con gap 8px
- **Pulsanti**: Bootstrap con hover effects
- **Responsive**: Stack verticale su mobile
- **Accessibilità**: Focus states e keyboard navigation

## 🔄 Controllo Ruoli

### Utenti Normali (USER, AUDITOR)
- **Comportamento**: Onboarding automatico al primo accesso
- **Trigger**: `localStorage.getItem('docs_onboarding_shown')` è null
- **Persistenza**: Salvato in localStorage dopo completamento

### Admin/CEO
- **Comportamento**: Solo se richiesto manualmente
- **Trigger**: Pulsante "🎙 Jack ti guida di nuovo"
- **Controllo**: `userRole === 'ADMIN' || userRole === 'CEO'`

## 🎮 Controlli Interfaccia

### Pulsanti di Navigazione
- **← Indietro**: Passo precedente (disabilitato al primo)
- **Avanti →**: Passo successivo (diventa "Fine" all'ultimo)
- **Salta Guida**: Completa l'onboarding immediatamente
- **✕ Chiudi**: Chiude l'onboarding

### Pulsante Riavvia
- **Posizione**: Fixed bottom-right
- **Stile**: Gradiente Synthia con hover effects
- **Funzione**: Rimuove localStorage e ricarica pagina

## 📱 Responsive Design

### Desktop (>768px)
- **Container**: 450px max-width, 400px min-width
- **Controlli**: Flex row con gap 8px
- **Posizionamento**: Assoluto con calcoli dinamici

### Mobile (≤768px)
- **Container**: 90vw max-width, margin 20px
- **Controlli**: Flex column, width 100%
- **Padding**: Ridotto a 16px
- **Scroll**: Auto-scroll con margin 100px

## 🔧 Attributi HTML

### Data Attributes
```html
<!-- Elementi target -->
<button data-onboarding="upload">📤 Upload</button>
<button data-onboarding="analyze">🧠 Analizza AI</button>
<button data-onboarding="sign">✍️ Firma</button>
<button data-onboarding="export">⬇️ Esporta</button>
<button data-onboarding="help">❓ Aiuto</button>

<!-- Ruolo utente -->
<body data-user-role="{{ current_user.role }}">
```

### Classi CSS
```html
<!-- Evidenziazione automatica -->
<div class="jack-onboarding-highlight">
    <!-- Elemento evidenziato -->
</div>

<!-- Overlay -->
<div class="jack-onboarding-overlay">
    <div class="jack-onboarding-container">
        <div class="jack-onboarding-content">
            <!-- Contenuto passo -->
        </div>
    </div>
</div>
```

## 🚀 Funzionalità Avanzate

### 1. Posizionamento Intelligente
```javascript
positionContent(targetElement, position) {
    const rect = targetElement.getBoundingClientRect();
    
    switch (position) {
        case 'top':    // Sopra l'elemento
        case 'bottom': // Sotto l'elemento
        case 'left':   // A sinistra
        case 'right':  // A destra
    }
}
```

### 2. Evidenziazione Multi-elemento
```javascript
highlightElement(element) {
    // Rimuovi evidenziazioni precedenti
    document.querySelectorAll('.jack-onboarding-highlight')
        .forEach(el => el.classList.remove('jack-onboarding-highlight'));
    
    // Aggiungi evidenziazione
    element.classList.add('jack-onboarding-highlight');
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
```

### 3. Messaggio di Completamento
```javascript
showCompletionMessage() {
    const message = document.createElement('div');
    message.className = 'alert alert-success position-fixed';
    message.innerHTML = `
        <div class="d-flex align-items-center">
            <img src="/static/img/jack_synthia_realistic.png" width="32" height="32" class="me-2 rounded-circle">
            <div>
                <strong>🎉 Onboarding completato!</strong><br>
                Ora sai come usare il modulo DOCS. Jack è sempre qui per aiutarti!
            </div>
        </div>
    `;
    
    document.body.appendChild(message);
    setTimeout(() => message.remove(), 5000);
}
```

## 📊 Configurazione

### Variabili d'Ambiente
```bash
# .env
JACK_ONBOARDING_ENABLED=true
JACK_ONBOARDING_AUTO_SHOW=true
JACK_ONBOARDING_DURATION=10000
```

### Configurazione JavaScript
```javascript
const ONBOARDING_CONFIG = {
    enabled: true,
    autoShow: true,
    duration: 10000,
    steps: [
        // Configurazione passi
    ]
};
```

## ✅ Checklist Implementazione

- [x] **File JavaScript** (`static/js/onboarding_jack.js`)
- [x] **File CSS** (`static/css/onboarding_jack.css`)
- [x] **Template base** con inclusione file
- [x] **Attributi data-onboarding** sui pulsanti
- [x] **Controllo ruoli** (USER/AUDITOR vs ADMIN/CEO)
- [x] **Persistenza localStorage** per completamento
- [x] **Pulsante riavvia** per admin/CEO
- [x] **Responsive design** per mobile
- [x] **Accessibilità** (focus states, keyboard nav)
- [x] **Animazioni** (fade, slide, pulse)
- [x] **Messaggio completamento** con auto-remove
- [x] **Documentazione completa**

## 🎯 Prossimi Passi

### 1. Estensioni Immediate
- **Onboarding per altri moduli** (FocusMe, QMS, Elevate)
- **Personalizzazione per ruolo** (messaggi specifici)
- **Progress indicator** (step X di Y)
- **Voice guidance** (sintesi vocale)

### 2. Funzionalità Avanzate
- **Onboarding contestuale** (basato su azioni utente)
- **Skip intelligente** (se utente esperto)
- **Analytics** (tracking completamento)
- **A/B testing** (diverse versioni)

### 3. Integrazione AI
- **Messaggi dinamici** basati su comportamento
- **Onboarding predittivo** (quando serve aiuto)
- **Chatbot integrato** per domande specifiche
- **Machine Learning** per ottimizzazione

## 🔧 Troubleshooting

### Problemi Comuni

1. **Onboarding non si avvia**
   - Verifica che i file CSS/JS siano caricati
   - Controlla che `data-user-role` sia presente
   - Verifica che `localStorage` funzioni

2. **Elementi non evidenziati**
   - Controlla che i selettori CSS siano corretti
   - Verifica che gli elementi target esistano
   - Controlla che non ci siano conflitti z-index

3. **Posizionamento errato**
   - Verifica che `getBoundingClientRect()` funzioni
   - Controlla che il container sia posizionato correttamente
   - Testa su diversi dispositivi

4. **Responsive non funziona**
   - Verifica le media queries CSS
   - Controlla che il viewport sia corretto
   - Testa su dispositivi reali

---

*Documentazione creata per SYNTHIA.DOCS.PROMPT.093 - Onboarding AI Interattivo Jack Synthia* 