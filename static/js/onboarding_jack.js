/**
 * 🤖 Onboarding AI Interattivo - Jack Synthia
 * Guida passo-passo automatica per il modulo DOCS
 */

class JackOnboarding {
    constructor() {
        this.currentStep = 0;
        this.steps = [];
        this.isActive = false;
        this.userRole = this.getUserRole();
        this.init();
    }

    /**
     * Inizializza l'onboarding
     */
    init() {
        // Verifica se l'onboarding è già stato mostrato
        if (this.shouldShowOnboarding()) {
            this.setupSteps();
            this.createOverlay();
            this.startOnboarding();
        }

        // Aggiungi pulsante per riavviare onboarding
        this.addRestartButton();
    }

    /**
     * Determina il ruolo utente
     */
    getUserRole() {
        // Estrai il ruolo dal DOM o da una variabile globale
        const roleElement = document.querySelector('[data-user-role]');
        return roleElement ? roleElement.getAttribute('data-user-role') : 'USER';
    }

    /**
     * Verifica se mostrare l'onboarding
     */
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

    /**
     * Configura i passi dell'onboarding
     */
    setupSteps() {
        this.steps = [
            {
                element: '#uploadBtn, .btn-upload, [data-onboarding="upload"]',
                title: '📤 Carica Documenti',
                content: `
                    <div class="jack-onboarding-step">
                        <div class="d-flex align-items-start">
                            <img src="/static/img/jack_synthia_realistic.png" width="48" height="48" class="me-3 rounded-circle" style="border: 2px solid white;">
                            <div>
                                <h6 class="mb-2"><strong>🎙 Jack Synthia ti guida</strong></h6>
                                <p class="mb-2">Carica un nuovo documento PDF, firmato e con nome chiaro. Assicurati che sia leggibile e completo.</p>
                                <small class="text-muted">💡 Suggerimento: Usa nomi descrittivi come "Manuale_HACCP_2024.pdf"</small>
                            </div>
                        </div>
                    </div>
                `,
                position: 'bottom'
            },
            {
                element: '.btn-analyze-ai, [data-onboarding="analyze"]',
                title: '🧠 Analisi AI',
                content: `
                    <div class="jack-onboarding-step">
                        <div class="d-flex align-items-start">
                            <img src="/static/img/jack_synthia_realistic.png" width="48" height="48" class="me-3 rounded-circle" style="border: 2px solid white;">
                            <div>
                                <h6 class="mb-2"><strong>🎙 Jack Synthia ti guida</strong></h6>
                                <p class="mb-2">Clicca qui per lanciare l'analisi AI automatica sul documento. Verifico scadenze, firme mancanti e criticità.</p>
                                <small class="text-muted">🔍 Analizzo: conformità, completezza, rischi</small>
                            </div>
                        </div>
                    </div>
                `,
                position: 'left'
            },
            {
                element: '.btn-sign, [data-onboarding="sign"]',
                title: '✍️ Firma Digitale',
                content: `
                    <div class="jack-onboarding-step">
                        <div class="d-flex align-items-start">
                            <img src="/static/img/jack_synthia_realistic.png" width="48" height="48" class="me-3 rounded-circle" style="border: 2px solid white;">
                            <div>
                                <h6 class="mb-2"><strong>🎙 Jack Synthia ti guida</strong></h6>
                                <p class="mb-2">Firma il documento se hai l'autorizzazione. Serve per validarlo ufficialmente e renderlo audit-ready.</p>
                                <small class="text-muted">🔐 Firma sicura con 2FA e hash SHA256</small>
                            </div>
                        </div>
                    </div>
                `,
                position: 'top'
            },
            {
                element: '.btn-export, [data-onboarding="export"]',
                title: '⬇️ Esporta Dati',
                content: `
                    <div class="jack-onboarding-step">
                        <div class="d-flex align-items-start">
                            <img src="/static/img/jack_synthia_realistic.png" width="48" height="48" class="me-3 rounded-circle" style="border: 2px solid white;">
                            <div>
                                <h6 class="mb-2"><strong>🎙 Jack Synthia ti guida</strong></h6>
                                <p class="mb-2">Esporta l'elenco documenti critici per audit, riunioni o archiviazione esterna.</p>
                                <small class="text-muted">📊 Formati: CSV, PDF, Excel per diversi usi</small>
                            </div>
                        </div>
                    </div>
                `,
                position: 'right'
            },
            {
                element: '.btn-help-jack, [data-onboarding="help"]',
                title: '❓ Aiuto Jack',
                content: `
                    <div class="jack-onboarding-step">
                        <div class="d-flex align-items-start">
                            <img src="/static/img/jack_synthia_realistic.png" width="48" height="48" class="me-3 rounded-circle" style="border: 2px solid white;">
                            <div>
                                <h6 class="mb-2"><strong>🎙 Jack Synthia ti guida</strong></h6>
                                <p class="mb-2">Hai bisogno d'aiuto? Jack ti guida sempre da qui. Questo pulsante è il tuo alleato per ogni dubbio.</p>
                                <small class="text-muted">🎯 Guida contestuale, tooltip, messaggi automatici</small>
                            </div>
                        </div>
                    </div>
                `,
                position: 'bottom'
            }
        ];
    }

    /**
     * Crea l'overlay per l'onboarding
     */
    createOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'jack-onboarding-overlay';
        overlay.className = 'jack-onboarding-overlay';
        overlay.innerHTML = `
            <div class="jack-onboarding-container">
                <div class="jack-onboarding-content">
                    <div id="jack-onboarding-step-content"></div>
                    <div class="jack-onboarding-controls">
                        <button id="jack-onboarding-prev" class="btn btn-outline-light btn-sm me-2">
                            ← Indietro
                        </button>
                        <button id="jack-onboarding-next" class="btn btn-primary btn-sm me-2">
                            Avanti →
                        </button>
                        <button id="jack-onboarding-skip" class="btn btn-outline-warning btn-sm me-2">
                            Salta Guida
                        </button>
                        <button id="jack-onboarding-close" class="btn btn-outline-danger btn-sm">
                            ✕ Chiudi
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        this.bindEvents();
    }

    /**
     * Collega gli eventi ai controlli
     */
    bindEvents() {
        document.getElementById('jack-onboarding-prev').addEventListener('click', () => this.prevStep());
        document.getElementById('jack-onboarding-next').addEventListener('click', () => this.nextStep());
        document.getElementById('jack-onboarding-skip').addEventListener('click', () => this.skipOnboarding());
        document.getElementById('jack-onboarding-close').addEventListener('click', () => this.closeOnboarding());
    }

    /**
     * Avvia l'onboarding
     */
    startOnboarding() {
        this.isActive = true;
        this.showStep(0);
    }

    /**
     * Mostra un passo specifico
     */
    showStep(stepIndex) {
        if (stepIndex < 0 || stepIndex >= this.steps.length) {
            this.completeOnboarding();
            return;
        }

        this.currentStep = stepIndex;
        const step = this.steps[stepIndex];
        
        // Trova l'elemento target
        const targetElement = document.querySelector(step.element);
        if (!targetElement) {
            console.warn(`Elemento target non trovato: ${step.element}`);
            this.nextStep();
            return;
        }

        // Evidenzia l'elemento target
        this.highlightElement(targetElement);
        
        // Mostra il contenuto del passo
        const contentContainer = document.getElementById('jack-onboarding-step-content');
        contentContainer.innerHTML = step.content;
        
        // Posiziona il contenuto
        this.positionContent(targetElement, step.position);
        
        // Aggiorna i controlli
        this.updateControls();
    }

    /**
     * Evidenzia un elemento
     */
    highlightElement(element) {
        // Rimuovi evidenziazioni precedenti
        document.querySelectorAll('.jack-onboarding-highlight').forEach(el => {
            el.classList.remove('jack-onboarding-highlight');
        });
        
        // Aggiungi evidenziazione
        element.classList.add('jack-onboarding-highlight');
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    /**
     * Posiziona il contenuto dell'onboarding
     */
    positionContent(targetElement, position) {
        const container = document.querySelector('.jack-onboarding-container');
        const rect = targetElement.getBoundingClientRect();
        
        let top, left;
        
        switch (position) {
            case 'top':
                top = rect.top - 200;
                left = rect.left + rect.width / 2 - 200;
                break;
            case 'bottom':
                top = rect.bottom + 20;
                left = rect.left + rect.width / 2 - 200;
                break;
            case 'left':
                top = rect.top + rect.height / 2 - 100;
                left = rect.left - 420;
                break;
            case 'right':
                top = rect.top + rect.height / 2 - 100;
                left = rect.right + 20;
                break;
            default:
                top = rect.bottom + 20;
                left = rect.left + rect.width / 2 - 200;
        }
        
        container.style.top = `${Math.max(20, top)}px`;
        container.style.left = `${Math.max(20, left)}px`;
    }

    /**
     * Aggiorna i controlli
     */
    updateControls() {
        const prevBtn = document.getElementById('jack-onboarding-prev');
        const nextBtn = document.getElementById('jack-onboarding-next');
        
        prevBtn.disabled = this.currentStep === 0;
        nextBtn.textContent = this.currentStep === this.steps.length - 1 ? 'Fine' : 'Avanti →';
    }

    /**
     * Passo successivo
     */
    nextStep() {
        this.showStep(this.currentStep + 1);
    }

    /**
     * Passo precedente
     */
    prevStep() {
        this.showStep(this.currentStep - 1);
    }

    /**
     * Salta l'onboarding
     */
    skipOnboarding() {
        this.completeOnboarding();
    }

    /**
     * Chiudi l'onboarding
     */
    closeOnboarding() {
        this.completeOnboarding();
    }

    /**
     * Completa l'onboarding
     */
    completeOnboarding() {
        localStorage.setItem('docs_onboarding_shown', 'true');
        this.removeOverlay();
        this.isActive = false;
        
        // Mostra messaggio di completamento
        this.showCompletionMessage();
    }

    /**
     * Rimuovi l'overlay
     */
    removeOverlay() {
        const overlay = document.getElementById('jack-onboarding-overlay');
        if (overlay) {
            overlay.remove();
        }
        
        // Rimuovi evidenziazioni
        document.querySelectorAll('.jack-onboarding-highlight').forEach(el => {
            el.classList.remove('jack-onboarding-highlight');
        });
    }

    /**
     * Mostra messaggio di completamento
     */
    showCompletionMessage() {
        const message = document.createElement('div');
        message.className = 'alert alert-success alert-dismissible fade show position-fixed';
        message.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
        message.innerHTML = `
            <div class="d-flex align-items-center">
                <img src="/static/img/jack_synthia_realistic.png" width="32" height="32" class="me-2 rounded-circle">
                <div>
                    <strong>🎉 Onboarding completato!</strong><br>
                    Ora sai come usare il modulo DOCS. Jack è sempre qui per aiutarti!
                </div>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(message);
        
        // Auto-remove dopo 5 secondi
        setTimeout(() => {
            if (message.parentElement) {
                message.remove();
            }
        }, 5000);
    }

    /**
     * Aggiungi pulsante per riavviare onboarding
     */
    addRestartButton() {
        // Cerca un posto appropriato per il pulsante
        const container = document.querySelector('.container, .main-content, .dashboard-container');
        if (container) {
            const button = document.createElement('button');
            button.id = 'restartOnboarding';
            button.className = 'btn btn-outline-info btn-sm position-fixed';
            button.style.cssText = 'bottom: 20px; right: 20px; z-index: 1000;';
            button.innerHTML = '🎙 Jack ti guida di nuovo';
            
            button.addEventListener('click', () => {
                localStorage.removeItem('docs_onboarding_shown');
                location.reload();
            });
            
            document.body.appendChild(button);
        }
    }

    /**
     * Riavvia l'onboarding manualmente
     */
    restartOnboarding() {
        localStorage.removeItem('docs_onboarding_shown');
        location.reload();
    }
}

// Inizializza l'onboarding quando il DOM è pronto
document.addEventListener('DOMContentLoaded', function() {
    new JackOnboarding();
});

// Esporta per uso globale
window.JackOnboarding = JackOnboarding; 