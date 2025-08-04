/**
 * 🧠 Integrazione Jack Synthia - Tutti i Moduli SYNTHIA
 * Gestione centralizzata per Elevate, QMS, Docs, Service, Transport, Acquisti
 */

class SynthiaIntegration {
    constructor() {
        this.apiBase = 'http://64.226.70.28';
        this.currentModule = this.detectModule();
        this.userPreferences = null;
        this.init();
    }

    /**
     * Inizializza l'integrazione
     */
    async init() {
        await this.loadUserPreferences();
        this.setupModuleSpecificFeatures();
        this.initializeJackMessages();
    }

    /**
     * Rileva il modulo corrente
     */
    detectModule() {
        const path = window.location.pathname;
        
        if (path.includes('/elevate') || path.includes('/hr')) {
            return 'elevate';
        } else if (path.includes('/qms') || path.includes('/iso')) {
            return 'qms';
        } else if (path.includes('/docs') || path.includes('/documenti')) {
            return 'docs';
        } else if (path.includes('/service') || path.includes('/manutenzione')) {
            return 'service';
        } else if (path.includes('/transport') || path.includes('/logistica')) {
            return 'transport';
        } else if (path.includes('/acquisti') || path.includes('/buy')) {
            return 'acquisti';
        } else if (path.includes('/focus') || path.includes('/task')) {
            return 'focusme';
        } else {
            return 'default';
        }
    }

    /**
     * Carica le preferenze utente
     */
    async loadUserPreferences() {
        try {
            const userId = this.getCurrentUserId();
            const response = await fetch(`${this.apiBase}/api/utente/${userId}/preferenze`);
            this.userPreferences = await response.json();
        } catch (error) {
            console.log('Errore nel caricamento preferenze utente:', error);
            this.userPreferences = {
                jack_stile: 'default',
                jack_umore: 'neutral',
                jack_frequenza: 'medium'
            };
        }
    }

    /**
     * Ottiene l'ID utente corrente
     */
    getCurrentUserId() {
        // Prova diversi metodi per ottenere l'ID utente
        const userIdMeta = document.querySelector('meta[name="user-id"]');
        if (userIdMeta) {
            return userIdMeta.getAttribute('content');
        }
        
        const userIdData = document.querySelector('[data-user-id]');
        if (userIdData) {
            return userIdData.getAttribute('data-user-id');
        }
        
        // Fallback per test
        return 'default';
    }

    /**
     * Configura funzionalità specifiche per modulo
     */
    setupModuleSpecificFeatures() {
        switch (this.currentModule) {
            case 'elevate':
                this.setupElevateFeatures();
                break;
            case 'qms':
                this.setupQMSFeatures();
                break;
            case 'docs':
                this.setupDocsFeatures();
                break;
            case 'service':
                this.setupServiceFeatures();
                break;
            case 'transport':
                this.setupTransportFeatures();
                break;
            case 'acquisti':
                this.setupAcquistiFeatures();
                break;
            case 'focusme':
                this.setupFocusMeFeatures();
                break;
        }
    }

    /**
     * Configura funzionalità per Elevate
     */
    setupElevateFeatures() {
        // Eventi specifici per HR
        const events = [
            { trigger: '.btn-ferie', evento: 'apertura_ferie' },
            { trigger: '.btn-profilo', evento: 'apertura_profilo' },
            { trigger: '.btn-dashboard-hr', evento: 'apertura_dashboard_hr' },
            { trigger: '.btn-formazione', evento: 'apertura_formazione' }
        ];
        
        this.bindModuleEvents(events);
    }

    /**
     * Configura funzionalità per QMS
     */
    setupQMSFeatures() {
        const events = [
            { trigger: '.btn-procedure', evento: 'apertura_procedure' },
            { trigger: '.btn-audit', evento: 'apertura_audit' },
            { trigger: '.btn-formazione-iso', evento: 'apertura_formazione_iso' },
            { trigger: '.btn-certificazioni', evento: 'apertura_certificazioni' }
        ];
        
        this.bindModuleEvents(events);
    }

    /**
     * Configura funzionalità per Docs
     */
    setupDocsFeatures() {
        const events = [
            { trigger: '.btn-upload', evento: 'apertura_upload' },
            { trigger: '.btn-scadenze', evento: 'apertura_scadenze' },
            { trigger: '.btn-audit-check', evento: 'apertura_audit_check' },
            { trigger: '.btn-export', evento: 'apertura_export' }
        ];
        
        this.bindModuleEvents(events);
    }

    /**
     * Configura funzionalità per Service
     */
    setupServiceFeatures() {
        const events = [
            { trigger: '.btn-incidenti', evento: 'apertura_incidenti' },
            { trigger: '.btn-manutenzioni', evento: 'apertura_manutenzioni' },
            { trigger: '.btn-asset', evento: 'apertura_asset' },
            { trigger: '.btn-ticket', evento: 'apertura_ticket' }
        ];
        
        this.bindModuleEvents(events);
    }

    /**
     * Configura funzionalità per Transport
     */
    setupTransportFeatures() {
        const events = [
            { trigger: '.btn-logistica', evento: 'apertura_logistica' },
            { trigger: '.btn-spedizioni', evento: 'apertura_spedizioni' },
            { trigger: '.btn-veicoli', evento: 'apertura_veicoli' },
            { trigger: '.btn-route', evento: 'apertura_route' }
        ];
        
        this.bindModuleEvents(events);
    }

    /**
     * Configura funzionalità per Acquisti
     */
    setupAcquistiFeatures() {
        const events = [
            { trigger: '.btn-fornitori', evento: 'apertura_fornitori' },
            { trigger: '.btn-ordini', evento: 'apertura_ordini' },
            { trigger: '.btn-inventario', evento: 'apertura_inventario' },
            { trigger: '.btn-budget', evento: 'apertura_budget' }
        ];
        
        this.bindModuleEvents(events);
    }

    /**
     * Configura funzionalità per FocusMe
     */
    setupFocusMeFeatures() {
        const events = [
            { trigger: '.btn-task', evento: 'apertura_task' },
            { trigger: '.btn-planner', evento: 'apertura_planner' },
            { trigger: '.btn-review', evento: 'apertura_review' },
            { trigger: '.btn-analytics', evento: 'apertura_analytics' }
        ];
        
        this.bindModuleEvents(events);
    }

    /**
     * Collega eventi per modulo
     */
    bindModuleEvents(events) {
        events.forEach(({ trigger, evento }) => {
            const elements = document.querySelectorAll(trigger);
            elements.forEach(element => {
                element.addEventListener('click', () => {
                    this.setJackEvento(evento);
                });
            });
        });
    }

    /**
     * Inizializza messaggi Jack
     */
    initializeJackMessages() {
        // Crea area messaggi se non esiste
        if (!document.getElementById('jack-message-area')) {
            const messageArea = document.createElement('div');
            messageArea.id = 'jack-message-area';
            messageArea.className = 'mb-3';
            
            // Inserisci all'inizio del contenuto principale
            const mainContent = document.querySelector('.main-content, .container, main');
            if (mainContent) {
                mainContent.insertBefore(messageArea, mainContent.firstChild);
            }
        }

        // Carica messaggio automatico
        this.loadAutoMessage();
    }

    /**
     * Carica messaggio automatico
     */
    async loadAutoMessage() {
        try {
            const evento = sessionStorage.getItem("jack_evento") || "login";
            sessionStorage.removeItem("jack_evento");
            
            const params = new URLSearchParams({
                user_role: this.getUserRole(),
                modulo: this.currentModule,
                stile: this.userPreferences?.jack_stile || 'default',
                umore: this.userPreferences?.jack_umore || 'neutral'
            });
            
            const response = await fetch(`${this.apiBase}/synthia/ai/evento/${evento}?${params}`);
            const data = await response.json();
            
            if (data.messaggio) {
                this.showJackMessage(data.messaggio, data.azione_url, data.azione_testo, data.tipo || 'info');
            }
        } catch (error) {
            console.log('Errore nel caricamento messaggio Jack:', error);
        }
    }

    /**
     * Mostra messaggio Jack
     */
    showJackMessage(messaggio, azione_url = null, azione_testo = null, tipo = 'info') {
        const messageArea = document.getElementById('jack-message-area');
        if (!messageArea) return;
        
        const messageId = `jack-message-${Date.now()}`;
        const messageHtml = `
            <div class="jack-message-container" id="${messageId}">
                <div class="card shadow-sm p-3 mb-3 border-0 jack-message-${tipo}" 
                     style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                    <div class="d-flex align-items-start">
                        <img src="/static/img/jack_synthia_realistic.png" 
                             width="48" height="48" 
                             class="me-3 rounded-circle jack-avatar" 
                             style="border: 2px solid white; flex-shrink: 0;">
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-center justify-content-between">
                                <h6 class="mb-2 fw-bold">
                                    <span class="jack-icon me-2">🎙</span>
                                    <span class="jack-title">Jack Synthia</span>
                                </h6>
                                <button type="button" 
                                        class="btn-close btn-close-white jack-dismiss" 
                                        onclick="synthiaIntegration.dismissMessage('${messageId}')"
                                        aria-label="Chiudi messaggio">
                                </button>
                            </div>
                            <p class="mb-2 jack-text">${messaggio}</p>
                            ${azione_url ? `<a href="${azione_url}" class="btn btn-sm btn-outline-light jack-action">${azione_testo}</a>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        messageArea.insertAdjacentHTML('afterbegin', messageHtml);
        
        // Auto-remove dopo 10 secondi
        setTimeout(() => {
            this.dismissMessage(messageId);
        }, 10000);
    }

    /**
     * Nasconde messaggio Jack
     */
    dismissMessage(messageId) {
        const container = document.getElementById(messageId);
        if (container) {
            container.classList.add('removing');
            setTimeout(() => {
                if (container.parentElement) {
                    container.remove();
                }
            }, 300);
        }
    }

    /**
     * Imposta evento Jack
     */
    setJackEvento(evento) {
        sessionStorage.setItem("jack_evento", evento);
    }

    /**
     * Ottiene il ruolo utente
     */
    getUserRole() {
        const roleElement = document.querySelector('[data-user-role]');
        return roleElement ? roleElement.getAttribute('data-user-role') : 'USER';
    }

    /**
     * Aggiunge tooltip Jack a elementi
     */
    addJackTooltips() {
        const tooltipConfigs = [
            { selector: '.btn-primary', message: 'Azione principale del modulo.' },
            { selector: '.btn-success', message: 'Azione di conferma o completamento.' },
            { selector: '.btn-warning', message: 'Azione di attenzione o modifica.' },
            { selector: '.btn-danger', message: 'Azione critica o eliminazione.' },
            { selector: '.btn-info', message: 'Informazioni o dettagli aggiuntivi.' }
        ];
        
        tooltipConfigs.forEach(config => {
            const elements = document.querySelectorAll(config.selector);
            elements.forEach(element => {
                if (!element.querySelector('.jack-tooltip-box')) {
                    this.createTooltip(element, config.message);
                }
            });
        });
    }

    /**
     * Crea tooltip per elemento
     */
    createTooltip(element, message) {
        const tooltip = document.createElement('div');
        tooltip.className = 'jack-tooltip-box';
        tooltip.innerHTML = `
            <div class="jack-tooltip-content">
                <img src="/static/img/jack_synthia_realistic.png" class="jack-icon" alt="Jack Synthia">
                <span class="jack-text">${message}</span>
            </div>
            <div class="jack-tooltip-arrow"></div>
        `;
        
        element.style.position = 'relative';
        element.appendChild(tooltip);
    }
}

// Inizializza l'integrazione quando il DOM è pronto
document.addEventListener('DOMContentLoaded', () => {
    window.synthiaIntegration = new SynthiaIntegration();
});

// Esporta per uso globale
window.SynthiaIntegration = SynthiaIntegration; 