/**
 * 🧠 Tooltip Permanenti - Jack Synthia
 * Tooltip fissi accanto ai bottoni più usati del modulo DOCS
 */

class JackTooltips {
    constructor() {
        this.tooltips = [];
        this.isInitialized = false;
        this.init();
    }

    /**
     * Inizializza i tooltip
     */
    init() {
        if (this.isInitialized) return;
        
        this.setupTooltips();
        this.bindEvents();
        this.isInitialized = true;
    }

    /**
     * Configura i tooltip per ogni elemento
     */
    setupTooltips() {
        const tooltipConfigs = [
            {
                selector: '.btn-upload, [data-onboarding="upload"]',
                message: '📤 Carica qui il tuo documento PDF per iniziare il processo.',
                position: 'top'
            },
            {
                selector: '.btn-analyze-ai, [data-onboarding="analyze"]',
                message: '🧠 Usa l\'AI per verificare firme, scadenze, incompletezze.',
                position: 'left'
            },
            {
                selector: '.btn-sign, [data-onboarding="sign"]',
                message: '✍️ Firma il documento per validarlo ufficialmente.',
                position: 'top'
            },
            {
                selector: '.btn-approve, .btn-approval',
                message: '✅ Approvazione finale del documento da parte del responsabile.',
                position: 'top'
            },
            {
                selector: '.btn-export, [data-onboarding="export"]',
                message: '⬇️ Esporta i documenti critici per audit o report.',
                position: 'right'
            },
            {
                selector: '.btn-view, [data-onboarding="view"]',
                message: '🔍 Visualizza il documento completo prima di agire.',
                position: 'bottom'
            },
            {
                selector: '.btn-download, .btn-download-pdf',
                message: '📄 Scarica il PDF con badge AI incorporato per audit.',
                position: 'bottom'
            },
            {
                selector: '.btn-filter, .btn-search',
                message: '🔍 Filtra i documenti per trovare quelli specifici.',
                position: 'bottom'
            },
            {
                selector: '.btn-help, .btn-help-jack',
                message: '❓ Hai dubbi? Jack ti guida sempre da qui.',
                position: 'left'
            },
            {
                selector: '.btn-settings, .btn-config',
                message: '⚙️ Configura le impostazioni del sistema.',
                position: 'right'
            }
        ];

        tooltipConfigs.forEach(config => {
            this.createTooltipForSelector(config);
        });
    }

    /**
     * Crea tooltip per un selettore specifico
     */
    createTooltipForSelector(config) {
        const elements = document.querySelectorAll(config.selector);
        
        elements.forEach(element => {
            // Verifica se l'elemento ha già un tooltip
            if (element.querySelector('.jack-tooltip-box')) return;
            
            // Crea il tooltip
            const tooltip = this.createTooltipElement(config.message, config.position);
            
            // Aggiungi il tooltip all'elemento
            element.style.position = 'relative';
            element.appendChild(tooltip);
            
            // Salva riferimento
            this.tooltips.push({
                element: element,
                tooltip: tooltip,
                position: config.position
            });
        });
    }

    /**
     * Crea l'elemento tooltip
     */
    createTooltipElement(message, position) {
        const tooltip = document.createElement('div');
        tooltip.className = 'jack-tooltip-box';
        tooltip.setAttribute('data-position', position);
        
        tooltip.innerHTML = `
            <div class="jack-tooltip-content">
                <img src="/static/img/jack_synthia_realistic.png" class="jack-icon" alt="Jack Synthia">
                <span class="jack-text">${message}</span>
            </div>
            <div class="jack-tooltip-arrow"></div>
        `;
        
        return tooltip;
    }

    /**
     * Collega gli eventi
     */
    bindEvents() {
        this.tooltips.forEach(({ element, tooltip, position }) => {
            let showTimeout;
            let hideTimeout;
            
            // Mouse enter
            element.addEventListener('mouseenter', () => {
                clearTimeout(hideTimeout);
                showTimeout = setTimeout(() => {
                    this.showTooltip(tooltip, position);
                }, 300); // Delay di 300ms
            });
            
            // Mouse leave
            element.addEventListener('mouseleave', () => {
                clearTimeout(showTimeout);
                hideTimeout = setTimeout(() => {
                    this.hideTooltip(tooltip);
                }, 100); // Delay di 100ms
            });
            
            // Focus per accessibilità
            element.addEventListener('focus', () => {
                clearTimeout(hideTimeout);
                showTimeout = setTimeout(() => {
                    this.showTooltip(tooltip, position);
                }, 300);
            });
            
            element.addEventListener('blur', () => {
                clearTimeout(showTimeout);
                hideTimeout = setTimeout(() => {
                    this.hideTooltip(tooltip);
                }, 100);
            });
        });
    }

    /**
     * Mostra il tooltip
     */
    showTooltip(tooltip, position) {
        // Posiziona il tooltip
        this.positionTooltip(tooltip, position);
        
        // Mostra con animazione
        tooltip.style.opacity = '0';
        tooltip.style.visibility = 'visible';
        tooltip.style.transform = 'translateY(10px)';
        
        requestAnimationFrame(() => {
            tooltip.style.opacity = '1';
            tooltip.style.transform = 'translateY(0)';
        });
    }

    /**
     * Nasconde il tooltip
     */
    hideTooltip(tooltip) {
        tooltip.style.opacity = '0';
        tooltip.style.transform = 'translateY(10px)';
        
        setTimeout(() => {
            tooltip.style.visibility = 'hidden';
        }, 300);
    }

    /**
     * Posiziona il tooltip
     */
    positionTooltip(tooltip, position) {
        const element = tooltip.parentElement;
        const elementRect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        
        let top, left;
        
        switch (position) {
            case 'top':
                top = elementRect.top - tooltipRect.height - 10;
                left = elementRect.left + (elementRect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'bottom':
                top = elementRect.bottom + 10;
                left = elementRect.left + (elementRect.width / 2) - (tooltipRect.width / 2);
                break;
            case 'left':
                top = elementRect.top + (elementRect.height / 2) - (tooltipRect.height / 2);
                left = elementRect.left - tooltipRect.width - 10;
                break;
            case 'right':
                top = elementRect.top + (elementRect.height / 2) - (tooltipRect.height / 2);
                left = elementRect.right + 10;
                break;
            default:
                top = elementRect.bottom + 10;
                left = elementRect.left + (elementRect.width / 2) - (tooltipRect.width / 2);
        }
        
        // Assicurati che il tooltip sia visibile
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        // Correggi posizione se va fuori viewport
        if (left < 10) left = 10;
        if (left + tooltipRect.width > viewportWidth - 10) {
            left = viewportWidth - tooltipRect.width - 10;
        }
        if (top < 10) top = 10;
        if (top + tooltipRect.height > viewportHeight - 10) {
            top = viewportHeight - tooltipRect.height - 10;
        }
        
        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;
    }

    /**
     * Aggiungi tooltip personalizzato
     */
    addCustomTooltip(selector, message, position = 'top') {
        const config = {
            selector: selector,
            message: message,
            position: position
        };
        
        this.createTooltipForSelector(config);
        this.bindEvents(); // Ricollega eventi per i nuovi tooltip
    }

    /**
     * Rimuovi tutti i tooltip
     */
    removeAllTooltips() {
        this.tooltips.forEach(({ tooltip }) => {
            if (tooltip.parentElement) {
                tooltip.remove();
            }
        });
        this.tooltips = [];
    }

    /**
     * Aggiorna posizioni tooltip (per responsive)
     */
    updatePositions() {
        this.tooltips.forEach(({ tooltip, position }) => {
            if (tooltip.style.visibility === 'visible') {
                this.positionTooltip(tooltip, position);
            }
        });
    }
}

// Inizializza i tooltip quando il DOM è pronto
document.addEventListener('DOMContentLoaded', () => {
    window.jackTooltips = new JackTooltips();
});

// Aggiorna posizioni al resize
window.addEventListener('resize', () => {
    if (window.jackTooltips) {
        window.jackTooltips.updatePositions();
    }
});

// Esporta per uso globale
window.JackTooltips = JackTooltips; 