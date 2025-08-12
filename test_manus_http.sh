#!/usr/bin/env bash
set -euo pipefail

echo "🧪 TEST HTTP DIRETTI MANUS CORE"
echo "================================"

BASE_URL="http://localhost:5000"
SESSION_ID=""  # Inserisci qui il session ID se necessario
WEBHOOK_SECRET="${MANUS_WEBHOOK_SECRET:-test_secret}"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }

# Funzione per aggiungere cookie se presente
add_cookie() {
    if [ -n "$SESSION_ID" ]; then
        echo "-H \"Cookie: session=$SESSION_ID\""
    fi
}

# Test 1: Health Check Webhook
echo -e "\n1️⃣ Test Health Check Webhook..."
HEALTH_RESPONSE=$(curl -s -w "%{http_code}" "$BASE_URL/webhooks/manus/hooks/health")
HTTP_CODE="${HEALTH_RESPONSE: -3}"
RESPONSE_BODY="${HEALTH_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Health check OK: $RESPONSE_BODY"
else
    log_warning "Health check fallito (HTTP $HTTP_CODE): $RESPONSE_BODY"
fi

# Test 2: Crea Mapping
echo -e "\n2️⃣ Test Crea Mapping..."
MAPPING_RESPONSE=$(curl -s -w "%{http_code}" \
    -H "Content-Type: application/json" \
    $(add_cookie) \
    -d '{"manus_user_id":"u_http123","syn_user_id":42,"email":"http@example.com"}' \
    "$BASE_URL/admin/manus/mapping/create")
HTTP_CODE="${MAPPING_RESPONSE: -3}"
RESPONSE_BODY="${MAPPING_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Mapping creato: $RESPONSE_BODY"
else
    log_warning "Mapping non creato (HTTP $HTTP_CODE): $RESPONSE_BODY"
fi

# Test 3: Lista Mapping
echo -e "\n3️⃣ Test Lista Mapping..."
MAPPING_LIST=$(curl -s $(add_cookie) "$BASE_URL/admin/manus/mapping/list")
if echo "$MAPPING_LIST" | grep -q "u_http123"; then
    log_success "Mapping trovato nella lista"
    echo "$MAPPING_LIST" | jq '.' 2>/dev/null || echo "$MAPPING_LIST"
else
    log_warning "Mapping non trovato nella lista"
    echo "$MAPPING_LIST"
fi

# Test 4: Rebuild Coverage
echo -e "\n4️⃣ Test Rebuild Coverage..."
COVERAGE_RESPONSE=$(curl -s -w "%{http_code}" -X POST \
    $(add_cookie) \
    "$BASE_URL/admin/manus/coverage/rebuild/42")
HTTP_CODE="${COVERAGE_RESPONSE: -3}"
RESPONSE_BODY="${COVERAGE_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Coverage rebuild: $RESPONSE_BODY"
else
    log_warning "Coverage rebuild fallito (HTTP $HTTP_CODE): $RESPONSE_BODY"
fi

# Test 5: Webhook con utente mappato
echo -e "\n5️⃣ Test Webhook - Utente Mappato..."
BODY='{"course_id":"COURSE_HTTP123","manus_user_id":"u_http123","email":"http@example.com"}'
SIG=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -r | awk '{print $1}')

WEBHOOK_RESPONSE=$(curl -s -w "%{http_code}" \
    -H "X-Manus-Event: COURSE_COMPLETED" \
    -H "X-Manus-Signature: $SIG" \
    -H "Content-Type: application/json" \
    -d "$BODY" \
    "$BASE_URL/webhooks/manus/hooks")
HTTP_CODE="${WEBHOOK_RESPONSE: -3}"
RESPONSE_BODY="${WEBHOOK_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Webhook utente mappato OK: $RESPONSE_BODY"
else
    log_warning "Webhook utente mappato fallito (HTTP $HTTP_CODE): $RESPONSE_BODY"
fi

# Test 6: Webhook con utente non mappato
echo -e "\n6️⃣ Test Webhook - Utente Non Mappato..."
BODY='{"course_id":"COURSE_HTTP456","manus_user_id":"u_unknown_http","email":"unknown_http@example.com"}'
SIG=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -r | awk '{print $1}')

WEBHOOK_RESPONSE=$(curl -s -w "%{http_code}" \
    -H "X-Manus-Event: COURSE_COMPLETED" \
    -H "X-Manus-Signature: $SIG" \
    -H "Content-Type: application/json" \
    -d "$BODY" \
    "$BASE_URL/webhooks/manus/hooks")
HTTP_CODE="${WEBHOOK_RESPONSE: -3}"
RESPONSE_BODY="${WEBHOOK_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Webhook utente non mappato OK: $RESPONSE_BODY"
else
    log_warning "Webhook utente non mappato fallito (HTTP $HTTP_CODE): $RESPONSE_BODY"
fi

# Test 7: Verifica mapping inattivo creato
echo -e "\n7️⃣ Verifica Mapping Inattivo..."
MAPPING_LIST_AFTER=$(curl -s $(add_cookie) "$BASE_URL/admin/manus/mapping/list")
if echo "$MAPPING_LIST_AFTER" | grep -q "u_unknown_http"; then
    log_success "Mapping inattivo creato per utente sconosciuto"
else
    log_warning "Mapping inattivo non trovato"
fi

# Test 8: Webhook con firma non valida
echo -e "\n8️⃣ Test Webhook - Firma Non Valida..."
BODY='{"course_id":"COURSE_HTTP789","manus_user_id":"u_test789","email":"test789@example.com"}'
INVALID_SIG="invalid_signature_http"

WEBHOOK_RESPONSE=$(curl -s -w "%{http_code}" \
    -H "X-Manus-Event: COURSE_COMPLETED" \
    -H "X-Manus-Signature: $INVALID_SIG" \
    -H "Content-Type: application/json" \
    -d "$BODY" \
    "$BASE_URL/webhooks/manus/hooks")
HTTP_CODE="${WEBHOOK_RESPONSE: -3}"
RESPONSE_BODY="${WEBHOOK_RESPONSE%???}"

if [ "$HTTP_CODE" = "401" ]; then
    log_success "Webhook con firma non valida correttamente rifiutato"
else
    log_warning "Webhook con firma non valida non rifiutato (HTTP $HTTP_CODE): $RESPONSE_BODY"
fi

echo -e "\n🎯 TEST HTTP DIRETTI COMPLETATI"
echo "=================================="
log_success "Tutti i test HTTP principali completati!"

echo -e "\n📊 Risultati attesi:"
echo "- Health check webhook funzionante"
echo "- Mapping utenti creati e listati"
echo "- Coverage formazione ricalcolato"
echo "- Webhook accettati con firma valida"
echo "- Webhook rifiutati con firma non valida"
echo "- Mapping inattivi creati per utenti sconosciuti"

echo -e "\n🔧 Per configurare:"
echo "1. Imposta SESSION_ID nel file se necessario"
echo "2. Imposta MANUS_WEBHOOK_SECRET per test reali"
echo "3. Modifica BASE_URL se necessario"
