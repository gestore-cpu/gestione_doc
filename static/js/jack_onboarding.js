// 📁 File: static/js/jack_onboarding.js

// Configurazione onboarding per modulo DOCS
const onboardingConfig = {
  module: 'docs',
  messages: [
    {
      text: "Ciao {{nome}}! 👋 Benvenuto nel modulo documenti!",
      action: null,
      highlight: null
    },
    {
      text: "Qui puoi caricare, firmare e controllare i documenti.",
      action: null,
      highlight: '.upload-section'
    },
    {
      text: "Vuoi un esempio? Carica un file e ti guiderò io! 🧠",
      action: '/upload',
      actionText: 'Carica Documento',
      highlight: '.upload-section'
    },
    {
      text: "Ti mostrerò anche i documenti in scadenza… ⏰",
      action: '/docs/scadenziario',
      actionText: 'Vedi Scadenze',
      highlight: '.scadenze-section'
    },
    {
      text: "Puoi chiedermi aiuto in ogni momento con '💬 Chiedi a Jack'",
      action: null,
      highlight: '.jack-help-button'
    },
    {
      text: "Iniziamo! Ti tengo d'occhio da qui 🐾",
      action: null,
      highlight: null
    }
  ],
  userRole: null,
  userName: null
};

let onboardingIndex = 0;
let currentHighlight = null;

// Funzione per ottenere il nome utente dal DOM o localStorage
function getUserInfo() {
  const userElement = document.querySelector('[data-user-name]');
  const roleElement = document.querySelector('[data-user-role]');
  
  onboardingConfig.userName = userElement ? userElement.dataset.userName : 'Utente';
  onboardingConfig.userRole = roleElement ? roleElement.dataset.userRole : 'USER';
  
  // Personalizza messaggi in base al ruolo
  if (onboardingConfig.userRole === 'ADMIN') {
    onboardingConfig.messages[1].text = "Come amministratore, hai accesso completo a tutti i documenti.";
  } else if (onboardingConfig.userRole === 'CEO') {
    onboardingConfig.messages[1].text = "Come CEO, puoi visualizzare tutti i documenti critici dell'azienda.";
  }
}

// Funzione per evidenziare elementi
function highlightElement(selector) {
  // Rimuovi evidenziazione precedente
  if (currentHighlight) {
    currentHighlight.classList.remove('jack-highlight');
  }
  
  if (selector) {
    const element = document.querySelector(selector);
    if (element) {
      element.classList.add('jack-highlight');
      currentHighlight = element;
      
      // Scroll all'elemento
      element.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center' 
      });
    }
  }
}

// Funzione per sostituire placeholder nei messaggi
function processMessage(message) {
  return message
    .replace('{{nome}}', onboardingConfig.userName)
    .replace('{{ruolo}}', onboardingConfig.userRole);
}

function showOnboardingStep() {
  const box = document.getElementById("jack-onboarding-box");
  const btnNext = document.getElementById("jack-onboarding-next");
  const btnAction = document.getElementById("jack-onboarding-action");

  if (onboardingIndex < onboardingConfig.messages.length) {
    const step = onboardingConfig.messages[onboardingIndex];
    
    // Aggiorna messaggio
    box.innerHTML = `<div class="jack-message-text">${processMessage(step.text)}</div>`;
    
    // Gestisci azione
    if (step.action) {
      btnAction.style.display = 'inline-block';
      btnAction.textContent = step.actionText || 'Azione';
      btnAction.onclick = () => {
        window.location.href = step.action;
      };
    } else {
      btnAction.style.display = 'none';
    }
    
    // Evidenzia elemento
    highlightElement(step.highlight);
    
    onboardingIndex++;
  } else {
    completeOnboarding();
  }
}

function completeOnboarding() {
  const wrapper = document.getElementById("jack-onboarding-wrapper");
  
  // Rimuovi evidenziazione
  if (currentHighlight) {
    currentHighlight.classList.remove('jack-highlight');
  }
  
  // Animazione di completamento
  wrapper.classList.add('onboarding-complete');
  
  setTimeout(() => {
    localStorage.setItem("onboarding_docs_completato", "true");
    wrapper.style.display = "none";
    
    // Mostra messaggio di completamento
    showCompletionMessage();
  }, 800);
}

function showCompletionMessage() {
  const messageArea = document.getElementById("jack-message-area");
  if (messageArea) {
    const completionMsg = document.createElement('div');
    completionMsg.className = 'jack-message-container';
    completionMsg.innerHTML = `
      <div class="card shadow-sm p-3 mb-3 border-0" style="background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); color: white;">
        <div class="d-flex align-items-center">
          <img src="/static/img/jack_synthia_realistic.png" width="48" height="48" class="me-3 rounded-circle" style="border: 2px solid white;">
          <div class="flex-grow-1">
            <p class="mb-2"><strong>🎉 Perfetto!</strong> Ora sei pronto per usare il modulo documenti!</p>
            <small>Puoi sempre richiamare l'aiuto con il pulsante "💬 Chiedi a Jack"</small>
          </div>
          <button type="button" class="btn-close btn-close-white" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
      </div>
    `;
    
    messageArea.prepend(completionMsg);
    
    // Auto-remove dopo 8 secondi
    setTimeout(() => {
      if (completionMsg.parentElement) {
        completionMsg.remove();
      }
    }, 8000);
  }
}

function initOnboarding() {
  // Controlla se l'onboarding è già stato completato
  if (localStorage.getItem("onboarding_docs_completato")) {
    return;
  }
  
  // Controlla se siamo nel modulo DOCS
  const isDocsModule = window.location.pathname.includes('/docs') || 
                      window.location.pathname.includes('/admin/doc') ||
                      window.location.pathname.includes('/upload');
  
  if (!isDocsModule) {
    return;
  }

  // Ottieni informazioni utente
  getUserInfo();

  // Crea wrapper onboarding
  const wrapper = document.createElement("div");
  wrapper.id = "jack-onboarding-wrapper";
  wrapper.innerHTML = `
    <div id="jack-onboarding-box" class="jack-box onboarding"></div>
    <div class="jack-onboarding-buttons">
      <button id="jack-onboarding-action" class="btn btn-success" style="display: none;">Azione</button>
      <button id="jack-onboarding-next" class="btn btn-primary">Avanti</button>
      <button id="jack-onboarding-skip" class="btn btn-secondary">Salta</button>
    </div>
  `;
  document.body.appendChild(wrapper);

  // Event listeners
  document.getElementById("jack-onboarding-next").onclick = showOnboardingStep;
  document.getElementById("jack-onboarding-skip").onclick = () => {
    localStorage.setItem("onboarding_docs_completato", "true");
    wrapper.style.display = "none";
    
    if (currentHighlight) {
      currentHighlight.classList.remove('jack-highlight');
    }
  };

  // Inizia onboarding
  showOnboardingStep();
}

// Inizializza quando il DOM è pronto
document.addEventListener("DOMContentLoaded", initOnboarding);

// Esporta funzioni per uso esterno
window.JackOnboarding = {
  init: initOnboarding,
  reset: () => {
    localStorage.removeItem("onboarding_docs_completato");
    initOnboarding();
  },
  showStep: showOnboardingStep,
  complete: completeOnboarding
}; 