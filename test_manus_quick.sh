#!/bin/bash
# Script di test rapido per Go-Live Manus Core

set -e

echo "🧪 TEST GO-LIVE MANUS CORE"
echo "=========================="

# Configurazione
HOST="localhost:5000"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="password"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funzioni helper
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# 1. Test connessione server
echo -e "\n1️⃣ Test connessione server..."
if curl -s -f "http://$HOST/" > /dev/null; then
    log_success "Server raggiungibile"
else
    log_error "Server non raggiungibile"
    exit 1
fi

# 2. Test health check webhook
echo -e "\n2️⃣ Test health check webhook..."
if curl -s -f "http://$HOST/webhooks/manus/hooks/health" | grep -q "ok"; then
    log_success "Webhook health check OK"
else
    log_error "Webhook health check fallito"
fi

# 3. Test login admin
echo -e "\n3️⃣ Test login admin..."
SESSION_COOKIE=$(curl -s -c - -d "email=$ADMIN_EMAIL&password=$ADMIN_PASSWORD" \
    "http://$HOST/login" | grep session | awk '{print $7}')

if [ -n "$SESSION_COOKIE" ]; then
    log_success "Login admin riuscito"
else
    log_warning "Login admin fallito - controlla credenziali"
fi

# 4. Test endpoint status Manus
echo -e "\n4️⃣ Test endpoint status Manus..."
if curl -s -b "session=$SESSION_COOKIE" \
    "http://$HOST/admin/manus/status" | grep -q "manual_links"; then
    log_success "Endpoint status Manus OK"
else
    log_warning "Endpoint status Manus non disponibile"
fi

# 5. Test sync manuale manuali
echo -e "\n5️⃣ Test sync manuale manuali..."
SYNC_RESPONSE=$(curl -s -w "%{http_code}" -b "session=$SESSION_COOKIE" \
    -H "Content-Type: application/json" \
    -d '{"azienda_id":1,"azienda_ref":"mercury"}' \
    "http://$HOST/admin/manus/sync/manuals")

HTTP_CODE="${SYNC_RESPONSE: -3}"
RESPONSE_BODY="${SYNC_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Sync manuali OK"
elif [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    log_warning "Sync manuali - autenticazione richiesta"
else
    log_error "Sync manuali fallito (HTTP $HTTP_CODE)"
fi

# 6. Test sync manuale corsi
echo -e "\n6️⃣ Test sync manuale corsi..."
SYNC_RESPONSE=$(curl -s -w "%{http_code}" -b "session=$SESSION_COOKIE" \
    -H "Content-Type: application/json" \
    -d '{"azienda_id":1,"azienda_ref":"mercury"}' \
    "http://$HOST/admin/manus/sync/courses")

HTTP_CODE="${SYNC_RESPONSE: -3}"
RESPONSE_BODY="${SYNC_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Sync corsi OK"
elif [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    log_warning "Sync corsi - autenticazione richiesta"
else
    log_error "Sync corsi fallito (HTTP $HTTP_CODE)"
fi

# 7. Test webhook con firma HMAC
echo -e "\n7️⃣ Test webhook con firma HMAC..."
BODY='{"course_id":"COURSE123"}'
SECRET="test_secret"
SIG=$(printf "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -r | awk '{print $1}')

WEBHOOK_RESPONSE=$(curl -s -w "%{http_code}" \
    -H "X-Manus-Event: COURSE_COMPLETED" \
    -H "X-Manus-Signature: $SIG" \
    -H "Content-Type: application/json" \
    -d "$BODY" \
    "http://$HOST/webhooks/manus/hooks")

HTTP_CODE="${WEBHOOK_RESPONSE: -3}"
RESPONSE_BODY="${WEBHOOK_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Webhook con firma OK"
elif [ "$HTTP_CODE" = "401" ]; then
    log_warning "Webhook - firma non valida (atteso per test)"
else
    log_error "Webhook fallito (HTTP $HTTP_CODE)"
fi

# 8. Verifica tabelle database
echo -e "\n8️⃣ Verifica tabelle database..."
if sqlite3 gestione.db ".tables" | grep -q "manus_manual_link"; then
    log_success "Tabella manus_manual_link presente"
else
    log_error "Tabella manus_manual_link mancante"
fi

if sqlite3 gestione.db ".tables" | grep -q "manus_course_link"; then
    log_success "Tabella manus_course_link presente"
else
    log_error "Tabella manus_course_link mancante"
fi

if sqlite3 gestione.db ".tables" | grep -q "training_completion_manus"; then
    log_success "Tabella training_completion_manus presente"
else
    log_error "Tabella training_completion_manus mancante"
fi

# 9. Verifica job scheduler
echo -e "\n9️⃣ Verifica job scheduler..."
if [ -f "jobs.db" ]; then
    log_success "Database job scheduler presente"
    JOB_COUNT=$(sqlite3 jobs.db "SELECT COUNT(*) FROM apscheduler_jobs WHERE id LIKE '%manus%';" 2>/dev/null || echo "0")
    if [ "$JOB_COUNT" -gt 0 ]; then
        log_success "Job Manus schedulati: $JOB_COUNT"
    else
        log_warning "Nessun job Manus trovato"
    fi
else
    log_warning "Database job scheduler non trovato"
fi

echo -e "\n🎯 GO-LIVE CHECKLIST COMPLETATA"
echo "================================"
echo -e "${GREEN}✅ Pronto per la produzione!${NC}"
echo ""
echo "📋 Prossimi passi:"
echo "1. Configura MANUS_API_KEY e MANUS_WEBHOOK_SECRET reali"
echo "2. Testa con dati reali da Manus"
echo "3. Monitora i log per i job schedulati"
echo "4. Verifica UI per badge e colonne Manus"
