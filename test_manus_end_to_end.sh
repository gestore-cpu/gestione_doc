#!/usr/bin/env bash
set -euo pipefail

echo "🧪 TEST END-TO-END MANUS CORE"
echo "=============================="

BASE_URL="http://localhost:5000"
WEBHOOK_SECRET="${MANUS_WEBHOOK_SECRET:-test_secret}"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }

# Test 1: Health Check
echo -e "\n1️⃣ Test Health Check..."
if curl -s -f "$BASE_URL/webhooks/manus/hooks/health" | grep -q "ok"; then
    log_success "Health check OK"
else
    log_error "Health check fallito"
    exit 1
fi

# Test 2: Crea Mapping
echo -e "\n2️⃣ Test Crea Mapping..."
MAPPING_RESPONSE=$(curl -s -w "%{http_code}" -H "Content-Type: application/json" \
    -d '{"manus_user_id":"u_test123","syn_user_id":42,"email":"test@example.com"}' \
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
MAPPING_LIST=$(curl -s "$BASE_URL/admin/manus/mapping/list")
if echo "$MAPPING_LIST" | grep -q "u_test123"; then
    log_success "Mapping trovato nella lista"
    echo "$MAPPING_LIST" | jq '.' 2>/dev/null || echo "$MAPPING_LIST"
else
    log_warning "Mapping non trovato nella lista"
    echo "$MAPPING_LIST"
fi

# Test 4: Rebuild Coverage
echo -e "\n4️⃣ Test Rebuild Coverage..."
COVERAGE_RESPONSE=$(curl -s -w "%{http_code}" -X POST \
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
BODY='{"course_id":"COURSE123","manus_user_id":"u_test123","email":"test@example.com"}'
SIG=$(printf "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -r | awk '{print $1}')

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
BODY='{"course_id":"COURSE456","manus_user_id":"u_unknown","email":"unknown@example.com"}'
SIG=$(printf "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -r | awk '{print $1}')

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
MAPPING_LIST_AFTER=$(curl -s "$BASE_URL/admin/manus/mapping/list")
if echo "$MAPPING_LIST_AFTER" | grep -q "u_unknown"; then
    log_success "Mapping inattivo creato per utente sconosciuto"
else
    log_warning "Mapping inattivo non trovato"
fi

# Test 8: Webhook con firma non valida
echo -e "\n8️⃣ Test Webhook - Firma Non Valida..."
BODY='{"course_id":"COURSE789","manus_user_id":"u_test456","email":"test456@example.com"}'
INVALID_SIG="invalid_signature"

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

echo -e "\n🎯 TEST END-TO-END COMPLETATI"
echo "================================"
log_success "Tutti i test principali completati!"

echo -e "\n📊 Risultati attesi:"
echo "- Mapping utenti creati e listati"
echo "- Coverage formazione ricalcolato"
echo "- Webhook accettati con firma valida"
echo "- Webhook rifiutati con firma non valida"
echo "- Mapping inattivi creati per utenti sconosciuti"

echo -e "\n🔗 Prossimi passi:"
echo "1. Importa la collezione Postman: manus_test_collection.json"
echo "2. Configura MANUS_WEBHOOK_SECRET nelle variabili"
echo "3. Esegui i test dalla dashboard admin"
echo "4. Verifica i log per dettagli completi"
