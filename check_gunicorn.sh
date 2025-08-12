#!/usr/bin/env bash
set -euo pipefail

echo "🔍 VERIFICA GUNICORN E CONFIGURAZIONE"
echo "======================================"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }

# Test 1: Status Gunicorn
echo -e "\n1️⃣ Status Gunicorn..."
if sudo systemctl is-active --quiet gunicorn; then
    log_success "Gunicorn è attivo"
    sudo systemctl status gunicorn --no-pager | head -10
else
    log_error "Gunicorn non è attivo"
    sudo systemctl status gunicorn --no-pager
fi

# Test 2: Configurazione Gunicorn
echo -e "\n2️⃣ Configurazione Gunicorn..."
echo "=== Configurazione systemd ==="
sudo systemctl cat gunicorn | sed -n '1,50p' || log_warning "Impossibile leggere configurazione"

echo -e "\n=== Variabili ambiente ==="
sudo systemctl show gunicorn --property=Environment | grep -E "(MANUS|WEB_CONCURRENCY|TIMEOUT)" || log_warning "Nessuna variabile Manus trovata"

# Test 3: Log recenti
echo -e "\n3️⃣ Log recenti Gunicorn..."
echo "=== Ultimi 20 log ==="
sudo journalctl -u gunicorn -n 20 --no-pager || log_warning "Impossibile leggere log"

# Test 4: Porte in ascolto
echo -e "\n4️⃣ Porte in ascolto..."
if netstat -tlnp 2>/dev/null | grep -E ":5000|:8000|:80|:443"; then
    log_success "Porte trovate"
else
    log_warning "Nessuna porta trovata per l'applicazione"
fi

# Test 5: Test connessione HTTP
echo -e "\n5️⃣ Test connessione HTTP..."
if curl -s -f http://localhost:5000/ > /dev/null 2>&1; then
    log_success "Server HTTP raggiungibile su localhost:5000"
else
    log_error "Server HTTP non raggiungibile su localhost:5000"
fi

# Test 6: Variabili ambiente applicazione
echo -e "\n6️⃣ Variabili ambiente applicazione..."
echo "=== Variabili Manus ==="
echo "MANUS_BASE_URL: ${MANUS_BASE_URL:-'non impostata'}"
echo "MANUS_API_KEY: ${MANUS_API_KEY:+'impostata'}"
echo "MANUS_WEBHOOK_SECRET: ${MANUS_WEBHOOK_SECRET:+'impostata'}"

# Test 7: File di configurazione
echo -e "\n7️⃣ File di configurazione..."
if [ -f "manus_env.conf" ]; then
    log_success "File manus_env.conf presente"
    cat manus_env.conf
else
    log_warning "File manus_env.conf non trovato"
fi

# Test 8: Processi Python
echo -e "\n8️⃣ Processi Python attivi..."
if pgrep -f "gunicorn.*app" > /dev/null; then
    log_success "Processi Gunicorn attivi"
    ps aux | grep -E "gunicorn.*app" | grep -v grep
else
    log_error "Nessun processo Gunicorn trovato"
fi

echo -e "\n🎯 VERIFICA COMPLETATA"
echo "========================"

echo -e "\n📋 PROSSIMI PASSI:"
echo "1. Se Gunicorn non è attivo: sudo systemctl start gunicorn"
echo "2. Se variabili mancanti: sudo systemctl edit gunicorn"
echo "3. Se errori nei log: sudo journalctl -u gunicorn -f"
echo "4. Per riavviare: sudo systemctl restart gunicorn"
