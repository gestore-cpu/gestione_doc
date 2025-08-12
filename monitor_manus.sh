#!/usr/bin/env bash
set -euo pipefail

echo "📊 MONITORAGGIO MANUS CORE"
echo "=========================="

# Configurazione
LOG_FILE="/var/log/manus_monitoring.log"
ALERT_EMAIL="admin@example.com"  # Sostituisci con la tua email
ALERT_THRESHOLD_5XX=5
ALERT_THRESHOLD_401=10

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
log_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }

# Funzione per inviare alert
send_alert() {
    local subject="$1"
    local message="$2"
    
    echo "$(date): $subject - $message" >> "$LOG_FILE"
    
    # Invia email se configurato
    if command -v mail &> /dev/null && [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "Manus Alert: $subject" "$ALERT_EMAIL"
    fi
    
    log_warning "ALERT: $subject - $message"
}

# Funzione per monitorare log in tempo reale
monitor_logs() {
    log_info "Avvio monitoraggio log in tempo reale..."
    log_info "Premi Ctrl+C per fermare"
    echo ""
    
    # Monitora log Gunicorn per eventi Manus
    journalctl -u gunicorn -f | grep -i manus | while read -r line; do
        echo "$(date '+%H:%M:%S'): $line"
        
        # Controlla errori 5xx
        if echo "$line" | grep -q "5[0-9][0-9]"; then
            send_alert "Error 5xx" "Errore server rilevato: $line"
        fi
        
        # Controlla errori 401
        if echo "$line" | grep -q "401"; then
            send_alert "Error 401" "Errore autenticazione rilevato: $line"
        fi
        
        # Controlla fallimenti coverage
        if echo "$line" | grep -q "coverage.*fail\|rebuild.*fail"; then
            send_alert "Coverage Fail" "Fallimento coverage rilevato: $line"
        fi
        
        # Controlla rate limit
        if echo "$line" | grep -q "rate.*limit\|429"; then
            send_alert "Rate Limit" "Rate limit superato: $line"
        fi
        
        # Controlla webhook disabilitati
        if echo "$line" | grep -q "webhook.*disabled"; then
            send_alert "Webhook Disabled" "Webhook disabilitati: $line"
        fi
    done
}

# Funzione per statistiche rapide
quick_stats() {
    log_info "Statistiche rapide Manus:"
    echo ""
    
    # Conta eventi webhook negli ultimi 10 minuti
    webhook_count=$(journalctl -u gunicorn --since "10 minutes ago" | grep -i "webhook.*manus" | wc -l)
    echo "📨 Webhook ultimi 10 min: $webhook_count"
    
    # Conta errori 5xx negli ultimi 10 minuti
    errors_5xx=$(journalctl -u gunicorn --since "10 minutes ago" | grep -i "5[0-9][0-9]" | wc -l)
    echo "❌ Errori 5xx ultimi 10 min: $errors_5xx"
    
    # Conta errori 401 negli ultimi 10 minuti
    errors_401=$(journalctl -u gunicorn --since "10 minutes ago" | grep -i "401" | wc -l)
    echo "🔐 Errori 401 ultimi 10 min: $errors_401"
    
    # Conta fallimenti coverage
    coverage_fails=$(journalctl -u gunicorn --since "10 minutes ago" | grep -i "coverage.*fail\|rebuild.*fail" | wc -l)
    echo "📊 Fallimenti coverage ultimi 10 min: $coverage_fails"
    
    echo ""
    
    # Alert se troppi errori
    if [ "$errors_5xx" -gt "$ALERT_THRESHOLD_5XX" ]; then
        send_alert "High 5xx Errors" "Troppi errori 5xx: $errors_5xx"
    fi
    
    if [ "$errors_401" -gt "$ALERT_THRESHOLD_401" ]; then
        send_alert "High 401 Errors" "Troppi errori 401: $errors_401"
    fi
}

# Funzione per health check rapido
health_check() {
    log_info "Health check rapido:"
    echo ""
    
    # Test health endpoint
    if curl -s -f "http://localhost:5000/webhooks/manus/hooks/health" > /dev/null; then
        log_success "Health endpoint OK"
    else
        log_error "Health endpoint FAIL"
        send_alert "Health Check Fail" "Health endpoint non risponde"
    fi
    
    # Controlla se Gunicorn è attivo
    if systemctl is-active --quiet gunicorn; then
        log_success "Gunicorn attivo"
    else
        log_error "Gunicorn non attivo"
        send_alert "Gunicorn Down" "Servizio Gunicorn non attivo"
    fi
    
    # Controlla variabili ambiente
    if [ -n "${MANUS_WEBHOOK_SECRET:-}" ]; then
        log_success "MANUS_WEBHOOK_SECRET configurato"
    else
        log_warning "MANUS_WEBHOOK_SECRET non configurato"
    fi
    
    echo ""
}

# Funzione per controlli di sicurezza
security_check() {
    log_info "Controlli di sicurezza:"
    echo ""
    
    # Controlla se il secret è quello di default
    if [ "${MANUS_WEBHOOK_SECRET:-}" = "your_webhook_secret_here" ]; then
        log_warning "MANUS_WEBHOOK_SECRET è quello di default"
        send_alert "Security Warning" "Webhook secret è quello di default"
    else
        log_success "Webhook secret configurato correttamente"
    fi
    
    # Controlla feature flag
    if [ "${MANUS_WEBHOOK_ENABLED:-true}" = "true" ]; then
        log_success "Webhook abilitati"
    else
        log_warning "Webhook disabilitati via feature flag"
    fi
    
    echo ""
}

# Menu principale
show_menu() {
    echo "📊 MONITORAGGIO MANUS CORE - MENU"
    echo "================================"
    echo "1. Monitoraggio log in tempo reale"
    echo "2. Statistiche rapide (ultimi 10 min)"
    echo "3. Health check rapido"
    echo "4. Controlli di sicurezza"
    echo "5. Tutto (monitoraggio completo)"
    echo "6. Esci"
    echo ""
    read -p "Scegli opzione (1-6): " choice
    
    case $choice in
        1)
            monitor_logs
            ;;
        2)
            quick_stats
            ;;
        3)
            health_check
            ;;
        4)
            security_check
            ;;
        5)
            health_check
            security_check
            quick_stats
            echo ""
            log_info "Avvio monitoraggio continuo (Ctrl+C per fermare)..."
            monitor_logs
            ;;
        6)
            log_info "Uscita..."
            exit 0
            ;;
        *)
            log_error "Opzione non valida"
            show_menu
            ;;
    esac
}

# Funzione per monitoraggio automatico
auto_monitor() {
    log_info "Avvio monitoraggio automatico ogni 5 minuti..."
    log_info "Premi Ctrl+C per fermare"
    echo ""
    
    while true; do
        echo "=== $(date) ==="
        health_check
        quick_stats
        echo "Prossimo controllo tra 5 minuti..."
        echo ""
        sleep 300
    done
}

# Controlla argomenti
case "${1:-}" in
    "auto")
        auto_monitor
        ;;
    "stats")
        quick_stats
        ;;
    "health")
        health_check
        ;;
    "security")
        security_check
        ;;
    "logs")
        monitor_logs
        ;;
    *)
        show_menu
        ;;
esac
