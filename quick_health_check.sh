#!/usr/bin/env bash
set -euo pipefail

echo "🧪 CHECK RAPIDI MANUS CORE"
echo "==========================="

# Configurazione - MODIFICA QUESTI VALORI
HOST="localhost:5000"  # Sostituisci con il tuo dominio/IP
SESSION_ID=""  # Inserisci il session ID se necessario
MANUS_WEBHOOK_SECRET="test_secret"  # Sostituisci con il secret reale

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }

echo "🔧 Configurazione:"
echo "  HOST: $HOST"
echo "  SESSION_ID: ${SESSION_ID:-'non impostato'}"
echo "  WEBHOOK_SECRET: ${MANUS_WEBHOOK_SECRET:+'impostato'}"
echo ""

# 1) Health GET/HEAD (no auth)
echo -e "\n1️⃣ Health GET/HEAD (no auth)..."
echo "=== GET ==="
HEALTH_GET=$(curl -s -w "%{http_code}" "http://$HOST/webhooks/manus/hooks/health")
HTTP_CODE_GET="${HEALTH_GET: -3}"
RESPONSE_BODY_GET="${HEALTH_GET%???}"

if [ "$HTTP_CODE_GET" = "200" ]; then
    log_success "GET OK (HTTP $HTTP_CODE_GET): $RESPONSE_BODY_GET"
else
    log_error "GET fallito (HTTP $HTTP_CODE_GET): $RESPONSE_BODY_GET"
fi

echo "=== HEAD ==="
HEALTH_HEAD=$(curl -s -I -w "%{http_code}" "http://$HOST/webhooks/manus/hooks/health")
HTTP_CODE_HEAD="${HEALTH_HEAD: -3}"
HEADERS_HEAD="${HEALTH_HEAD%???}"

if [ "$HTTP_CODE_HEAD" = "200" ]; then
    log_success "HEAD OK (HTTP $HTTP_CODE_HEAD)"
    echo "$HEADERS_HEAD" | head -n1
else
    log_error "HEAD fallito (HTTP $HTTP_CODE_HEAD)"
fi

# 2) Admin API (ricorda Cookie/Token se protette)
echo -e "\n2️⃣ Admin API (ricorda Cookie/Token se protette)..."
echo "=== Crea mapping ==="
MAPPING_RESPONSE=$(curl -s -w "%{http_code}" \
    -H "Content-Type: application/json" \
    ${SESSION_ID:+-H "Cookie: session=$SESSION_ID"} \
    -d '{"manus_user_id":"u_test","syn_user_id":42,"email":"test@example.com"}' \
    "http://$HOST/admin/manus/mapping/create")
HTTP_CODE_MAPPING="${MAPPING_RESPONSE: -3}"
RESPONSE_BODY_MAPPING="${MAPPING_RESPONSE%???}"

if [ "$HTTP_CODE_MAPPING" = "200" ]; then
    log_success "Mapping creato: $RESPONSE_BODY_MAPPING"
elif [ "$HTTP_CODE_MAPPING" = "401" ] || [ "$HTTP_CODE_MAPPING" = "403" ]; then
    log_warning "Mapping - autenticazione richiesta (HTTP $HTTP_CODE_MAPPING): $RESPONSE_BODY_MAPPING"
else
    log_error "Mapping fallito (HTTP $HTTP_CODE_MAPPING): $RESPONSE_BODY_MAPPING"
fi

echo "=== Lista mapping ==="
MAPPING_LIST=$(curl -s ${SESSION_ID:+-H "Cookie: session=$SESSION_ID"} "http://$HOST/admin/manus/mapping/list")
if echo "$MAPPING_LIST" | grep -q "u_test"; then
    log_success "Mapping u_test trovato nella lista"
    echo "$MAPPING_LIST" | jq '.' 2>/dev/null || echo "$MAPPING_LIST"
elif echo "$MAPPING_LIST" | grep -q "error"; then
    log_warning "Errore nella lista mapping: $MAPPING_LIST"
else
    log_warning "Mapping u_test non trovato nella lista"
    echo "$MAPPING_LIST"
fi

# 3) Coverage rebuild (admin)
echo -e "\n3️⃣ Coverage rebuild (admin)..."
COVERAGE_RESPONSE=$(curl -s -w "%{http_code}" -X POST \
    ${SESSION_ID:+-H "Cookie: session=$SESSION_ID"} \
    "http://$HOST/admin/manus/coverage/rebuild/42")
HTTP_CODE_COVERAGE="${COVERAGE_RESPONSE: -3}"
RESPONSE_BODY_COVERAGE="${COVERAGE_RESPONSE%???}"

if [ "$HTTP_CODE_COVERAGE" = "200" ]; then
    log_success "Coverage rebuild: $RESPONSE_BODY_COVERAGE"
elif [ "$HTTP_CODE_COVERAGE" = "401" ] || [ "$HTTP_CODE_COVERAGE" = "403" ]; then
    log_warning "Coverage - autenticazione richiesta (HTTP $HTTP_CODE_COVERAGE): $RESPONSE_BODY_COVERAGE"
else
    log_error "Coverage rebuild fallito (HTTP $HTTP_CODE_COVERAGE): $RESPONSE_BODY_COVERAGE"
fi

# 4) Webhook (HMAC reale)
echo -e "\n4️⃣ Webhook (HMAC reale)..."
BODY='{"course_id":"COURSE123","manus_user_id":"u_test","email":"test@example.com"}'
SIG=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$MANUS_WEBHOOK_SECRET" -r | awk '{print $1}')

WEBHOOK_RESPONSE=$(curl -s -w "%{http_code}" \
    -H "X-Manus-Event: COURSE_COMPLETED" \
    -H "X-Manus-Signature: $SIG" \
    -H "Content-Type: application/json" \
    -d "$BODY" \
    "http://$HOST/webhooks/manus/hooks")
HTTP_CODE_WEBHOOK="${WEBHOOK_RESPONSE: -3}"
RESPONSE_BODY_WEBHOOK="${WEBHOOK_RESPONSE%???}"

if [ "$HTTP_CODE_WEBHOOK" = "200" ]; then
    log_success "Webhook OK: $RESPONSE_BODY_WEBHOOK"
elif [ "$HTTP_CODE_WEBHOOK" = "401" ]; then
    log_warning "Webhook - firma non valida (HTTP $HTTP_CODE_WEBHOOK): $RESPONSE_BODY_WEBHOOK"
else
    log_error "Webhook fallito (HTTP $HTTP_CODE_WEBHOOK): $RESPONSE_BODY_WEBHOOK"
fi

# Verifica mapping dopo webhook
echo -e "\n=== Verifica mapping dopo webhook ==="
MAPPING_LIST_AFTER=$(curl -s ${SESSION_ID:+-H "Cookie: session=$SESSION_ID"} "http://$HOST/admin/manus/mapping/list")
if echo "$MAPPING_LIST_AFTER" | grep -q "u_test"; then
    log_success "Mapping u_test ancora presente dopo webhook"
else
    log_warning "Mapping u_test non trovato dopo webhook"
fi

# Test webhook con utente sconosciuto
echo -e "\n=== Test webhook con utente sconosciuto ==="
BODY_UNKNOWN='{"course_id":"COURSE456","manus_user_id":"u_unknown","email":"unknown@example.com"}'
SIG_UNKNOWN=$(printf "%s" "$BODY_UNKNOWN" | openssl dgst -sha256 -hmac "$MANUS_WEBHOOK_SECRET" -r | awk '{print $1}')

WEBHOOK_UNKNOWN_RESPONSE=$(curl -s -w "%{http_code}" \
    -H "X-Manus-Event: COURSE_COMPLETED" \
    -H "X-Manus-Signature: $SIG_UNKNOWN" \
    -H "Content-Type: application/json" \
    -d "$BODY_UNKNOWN" \
    "http://$HOST/webhooks/manus/hooks")
HTTP_CODE_UNKNOWN="${WEBHOOK_UNKNOWN_RESPONSE: -3}"
RESPONSE_BODY_UNKNOWN="${WEBHOOK_UNKNOWN_RESPONSE%???}"

if [ "$HTTP_CODE_UNKNOWN" = "200" ]; then
    log_success "Webhook utente sconosciuto OK: $RESPONSE_BODY_UNKNOWN"
else
    log_warning "Webhook utente sconosciuto fallito (HTTP $HTTP_CODE_UNKNOWN): $RESPONSE_BODY_UNKNOWN"
fi

# Verifica mapping inattivo creato
echo -e "\n=== Verifica mapping inattivo creato ==="
MAPPING_FINAL=$(curl -s ${SESSION_ID:+-H "Cookie: session=$SESSION_ID"} "http://$HOST/admin/manus/mapping/list")
if echo "$MAPPING_FINAL" | grep -q "u_unknown"; then
    log_success "Mapping inattivo creato per utente sconosciuto"
else
    log_warning "Mapping inattivo non trovato per utente sconosciuto"
fi

echo -e "\n🎯 CHECK RAPIDI COMPLETATI"
echo "============================="
log_success "Tutti i check principali completati!"

echo -e "\n📊 Risultati attesi:"
echo "- Health check: {\"status\":\"ok\"} e HTTP/1.1 200 OK"
echo "- Mapping creato: {\"ok\":true,...}"
echo "- Mapping u_test in lista"
echo "- Coverage rebuild: {\"ok\":true,\"updated\":<n>}"
echo "- Webhook: {\"status\":\"ok\"}"
echo "- Mapping inattivo creato per utenti sconosciuti"

echo -e "\n🔧 Quick Fix (se qualcosa stona):"
echo "• 401/403 admin → manca Cookie/Bearer"
echo "• 401 webhook → secret/firma non combaciano"
echo "• 200 ma coverage invariato → crea mapping → rifai rebuild"
echo "• Timeout/504 → riavvia Gunicorn e controlla log:"
echo "  journalctl -u gunicorn -n 100 --no-pager"
