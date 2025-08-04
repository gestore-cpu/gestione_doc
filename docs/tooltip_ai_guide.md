# 🤖 Tooltip AI Contestuali - Jack Synthia

## 📋 Panoramica

I tooltip AI contestuali di Jack Synthia forniscono assistenza intelligente agli utenti del modulo DOCS, spiegando le funzionalità e suggerendo le azioni più appropriate.

## 🎯 Obiettivi

- **Guida Contestuale**: Spiegazioni specifiche per ogni pulsante
- **Onboarding Progressivo**: Tooltip automatici per nuovi utenti
- **Accessibilità**: Supporto per screen reader e navigazione da tastiera
- **Personalizzazione**: Messaggi dinamici basati sul contesto

## 🔧 Implementazione Tecnica

### 1. Struttura HTML Base

```html
<button class="btn btn-outline-primary btn-sm"
        data-bs-toggle="tooltip"
        data-bs-placement="top"
        data-bs-html="true"
        title="🤖 <strong>Jack dice:</strong><br>Messaggio personalizzato qui">
    👁️
</button>
```

### 2. Tooltip Dinamici AI

```html
<button data-ai-tooltip="Messaggio dinamico dal backend">
    🧠
</button>
```

### 3. Inizializzazione JavaScript

```javascript
// Inizializza tooltip Bootstrap con supporto AI
const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl, {
        html: true,
        trigger: 'hover focus',
        animation: true,
        delay: { show: 300, hide: 100 }
    });
});

// Supporto per tooltip dinamici AI
document.querySelectorAll('[data-ai-tooltip]').forEach(function(element) {
    const aiMessage = element.getAttribute('data-ai-tooltip');
    if (aiMessage) {
        element.setAttribute('data-bs-toggle', 'tooltip');
        element.setAttribute('data-bs-html', 'true');
        element.setAttribute('title', `🤖 <strong>Jack dice:</strong><br>${aiMessage}`);
        element.setAttribute('aria-describedby', 'ai-tooltip');
        element.setAttribute('role', 'button');
        
        new bootstrap.Tooltip(element, {
            html: true,
            trigger: 'hover focus',
            animation: true,
            delay: { show: 300, hide: 100 }
        });
    }
});
```

## 📝 Messaggi Tooltip Implementati

### Pulsanti Principali

| Pulsante | Messaggio AI |
|----------|--------------|
| 👁️ Visualizza | "Visualizza il contenuto completo del documento e tutte le sue versioni. Qui puoi vedere il PDF, le firme e lo storico delle modifiche." |
| ✍️ Firma | "Firma il documento come Responsabile per validarlo ufficialmente. Questa azione è irreversibile e registra la tua identità digitale." |
| 🧠 Analizza AI | "Analizza il documento con la mia intelligenza: verifico scadenze, firme mancanti, criticità e genero suggerimenti automatici." |
| 🤖📄 PDF AI | "Scarica il PDF con il mio badge AI incorporato: stato, spiegazione e metadati invisibili per audit." |

### Pulsanti di Navigazione

| Pulsante | Messaggio AI |
|----------|--------------|
| 📄 Gestione Documenti | "Accedi alla gestione completa dei documenti: upload, revisioni, firme e configurazioni avanzate." |
| 🔍 Filtra | "Applica i filtri selezionati per trovare documenti specifici. Posso aiutarti a trovare documenti critici o incompleti." |
| ⬇️ Esporta | "Scarica l'elenco dei documenti critici in formato CSV per audit, riunioni o archiviazione esterna." |

### Pulsanti di Export

| Pulsante | Messaggio AI |
|----------|--------------|
| ⬇️ Esporta Incompleti | "Esporta tutti i documenti incompleti per identificare le lacune da colmare." |
| ⬇️ Esporta Scaduti | "Esporta i documenti scaduti per azioni immediate di aggiornamento e compliance." |
| ⬇️ Esporta Senza Firma | "Esporta i documenti senza firma per identificare chi deve firmare e completare la validazione." |
| ⬇️ Esporta Tutti i Critici | "Esporta tutti i documenti critici per una visione completa delle priorità da gestire." |

## 🎨 Personalizzazione Stile

### CSS per Tooltip AI

```css
/* Stile personalizzato per tooltip AI */
.tooltip-inner {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    font-weight: 500;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.tooltip.bs-tooltip-top .tooltip-arrow::before {
    border-top-color: #667eea;
}
```

## 🚀 Funzionalità Avanzate

### 1. Onboarding Progressivo

I tooltip di onboarding vengono mostrati automaticamente ai nuovi utenti:

```javascript
const onboardingTooltips = [
    { id: 'uploadBtn', message: '🤖 <strong>Jack dice:</strong><br>Carica un nuovo documento. Assicurati che sia in formato PDF e chiaro.' },
    { id: 'aiAnalysisBtn', message: '🤖 <strong>Jack dice:</strong><br>Analizza il documento con la mia intelligenza per verificare compliance e criticità.' },
    { id: 'signatureBtn', message: '🤖 <strong>Jack dice:</strong><br>Firma il documento per validarlo ufficialmente. Questa azione è irreversibile.' }
];
```

### 2. Supporto Multi-lingua

Struttura per future estensioni i18n:

```javascript
const tooltipMessages = {
    'it': {
        'visualize': 'Visualizza il contenuto completo del documento...',
        'sign': 'Firma il documento come Responsabile...',
        'analyze': 'Analizza il documento con la mia intelligenza...'
    },
    'en': {
        'visualize': 'View the complete document content...',
        'sign': 'Sign the document as Manager...',
        'analyze': 'Analyze the document with my intelligence...'
    }
};
```

### 3. Accessibilità

Supporto completo per screen reader:

```html
<button data-bs-toggle="tooltip"
        aria-describedby="ai-tooltip"
        role="button"
        aria-label="Firma documento">
    ✍️
</button>
```

## 🔄 Aggiornamenti Futuri

### 1. Tooltip Dinamici dal Backend

```python
# Nel controller Python
def get_ai_tooltip_message(document, action):
    if document.ai_status == 'incompleto':
        return "⚠️ Questo documento è incompleto. Verifica le firme mancanti."
    elif document.ai_status == 'scaduto':
        return "🚨 Documento scaduto! Richiede aggiornamento immediato."
    else:
        return "✅ Documento completo e aggiornato."
```

### 2. Integrazione con Altri Moduli

Estendere i tooltip AI a:
- **FocusMe**: Suggerimenti per task e produttività
- **QMS**: Guida per compliance e audit
- **Elevate**: Consigli per formazione e sviluppo

## 📊 Metriche e Analytics

### Tracciamento Utilizzo

```javascript
// Traccia l'utilizzo dei tooltip
document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function(element) {
    element.addEventListener('shown.bs.tooltip', function() {
        // Invia analytics
        console.log('Tooltip mostrato:', this.getAttribute('title'));
    });
});
```

## ✅ Checklist Implementazione

- [x] Tooltip statici per tutti i pulsanti principali
- [x] Supporto HTML nei tooltip
- [x] Animazioni e delay personalizzati
- [x] Onboarding progressivo
- [x] Supporto accessibilità
- [x] Tooltip dinamici AI
- [x] Stile coerente con Synthia
- [x] Documentazione completa

## 🎯 Prossimi Passi

1. **Estensione ad altri moduli** (FocusMe, QMS, Elevate)
2. **Tooltip contestuali basati su AI** (analisi documento in tempo reale)
3. **Supporto multi-lingua** (it, en, fr, de)
4. **Analytics avanzati** per ottimizzare i messaggi
5. **Integrazione con chatbot** per assistenza più approfondita

---

*Documentazione creata per il modulo DOCS - Tooltip AI Contestuali Jack Synthia* 