#!/usr/bin/env bash
set -euo pipefail

echo "🧪 TEST HTTP DIRETTI MANUS CORE"
echo "================================"

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

# Funzione per aggiungere cookie se presente
add_cookie() {
    if [ -n "$SESSION_ID" ]; then
        echo "-H \"Cookie: session=$SESSION_ID\""
    fi
}

echo "🔧 Configurazione:"
echo "  HOST: $HOST"
echo "  SESSION_ID: ${SESSION_ID:-'non impostato'}"
echo "  WEBHOOK_SECRET: ${MANUS_WEBHOOK_SECRET:+'impostato'}"
echo ""

# A) Health webhook (no auth)
echo -e "\n1️⃣ A) Health webhook (no auth)..."
HEALTH_RESPONSE=$(curl -s -w "%{http_code}" "http://$HOST/webhooks/manus/hooks/health")
HTTP_CODE="${HEALTH_RESPONSE: -3}"
RESPONSE_BODY="${HEALTH_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Health check OK: $RESPONSE_BODY"
else
    log_error "Health check fallito (HTTP $HTTP_CODE): $RESPONSE_BODY"
fi

# B) Crea mapping (admin)
echo -e "\n2️⃣ B) Crea mapping (admin)..."
MAPPING_RESPONSE=$(curl -s -w "%{http_code}" \
    -H "Content-Type: application/json" \
    $(add_cookie) \
    -d '{"manus_user_id":"u_test","syn_user_id":42,"email":"test@example.com"}' \
    "http://$HOST/admin/manus/mapping/create")
HTTP_CODE="${MAPPING_RESPONSE: -3}"
RESPONSE_BODY="${MAPPING_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Mapping creato: $RESPONSE_BODY"
elif [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    log_warning "Mapping - autenticazione richiesta (HTTP $HTTP_CODE): $RESPONSE_BODY"
else
    log_error "Mapping fallito (HTTP $HTTP_CODE): $RESPONSE_BODY"
fi

# C) Lista mapping (admin)
echo -e "\n3️⃣ C) Lista mapping (admin)..."
MAPPING_LIST=$(curl -s $(add_cookie) "http://$HOST/admin/manus/mapping/list")
if echo "$MAPPING_LIST" | grep -q "u_test"; then
    log_success "Mapping trovato nella lista"
    echo "$MAPPING_LIST" | jq '.' 2>/dev/null || echo "$MAPPING_LIST"
elif echo "$MAPPING_LIST" | grep -q "error"; then
    log_warning "Errore nella lista mapping: $MAPPING_LIST"
else
    log_warning "Mapping non trovato nella lista"
    echo "$MAPPING_LIST"
fi

# D) Ricalcola coverage per utente (admin)
echo -e "\n4️⃣ D) Ricalcola coverage per utente (admin)..."
COVERAGE_RESPONSE=$(curl -s -w "%{http_code}" -X POST \
    $(add_cookie) \
    "http://$HOST/admin/manus/coverage/rebuild/42")
HTTP_CODE="${COVERAGE_RESPONSE: -3}"
RESPONSE_BODY="${COVERAGE_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Coverage rebuild: $RESPONSE_BODY"
elif [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    log_warning "Coverage - autenticazione richiesta (HTTP $HTTP_CODE): $RESPONSE_BODY"
else
    log_error "Coverage rebuild fallito (HTTP $HTTP_CODE): $RESPONSE_BODY"
fi

# E) Webhook completamento (HMAC)
echo -e "\n5️⃣ E) Webhook completamento (HMAC)..."
BODY='{"course_id":"COURSE123","manus_user_id":"u_test","email":"test@example.com"}'
SIG=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$MANUS_WEBHOOK_SECRET" -r | awk '{print $1}')

WEBHOOK_RESPONSE=$(curl -s -w "%{http_code}" \
    -H "X-Manus-Event: COURSE_COMPLETED" \
    -H "X-Manus-Signature: $SIG" \
    -H "Content-Type: application/json" \
    -d "$BODY" \
    "http://$HOST/webhooks/manus/hooks")
HTTP_CODE="${WEBHOOK_RESPONSE: -3}"
RESPONSE_BODY="${WEBHOOK_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Webhook OK: $RESPONSE_BODY"
elif [ "$HTTP_CODE" = "401" ]; then
    log_warning "Webhook - firma non valida (HTTP $HTTP_CODE): $RESPONSE_BODY"
else
    log_error "Webhook fallito (HTTP $HTTP_CODE): $RESPONSE_BODY"
fi

# Verifica mapping dopo webhook
echo -e "\n6️⃣ Verifica mapping dopo webhook..."
MAPPING_LIST_AFTER=$(curl -s $(add_cookie) "http://$HOST/admin/manus/mapping/list")
if echo "$MAPPING_LIST_AFTER" | grep -q "u_test"; then
    log_success "Mapping u_test ancora presente"
else
    log_warning "Mapping u_test non trovato dopo webhook"
fi

# Test webhook con utente sconosciuto
echo -e "\n7️⃣ Test webhook con utente sconosciuto..."
BODY_UNKNOWN='{"course_id":"COURSE456","manus_user_id":"u_unknown","email":"unknown@example.com"}'
SIG_UNKNOWN=$(printf "%s" "$BODY_UNKNOWN" | openssl dgst -sha256 -hmac "$MANUS_WEBHOOK_SECRET" -r | awk '{print $1}')

WEBHOOK_UNKNOWN_RESPONSE=$(curl -s -w "%{http_code}" \
    -H "X-Manus-Event: COURSE_COMPLETED" \
    -H "X-Manus-Signature: $SIG_UNKNOWN" \
    -H "Content-Type: application/json" \
    -d "$BODY_UNKNOWN" \
    "http://$HOST/webhooks/manus/hooks")
HTTP_CODE="${WEBHOOK_UNKNOWN_RESPONSE: -3}"
RESPONSE_BODY="${WEBHOOK_UNKNOWN_RESPONSE%???}"

if [ "$HTTP_CODE" = "200" ]; then
    log_success "Webhook utente sconosciuto OK: $RESPONSE_BODY"
else
    log_warning "Webhook utente sconosciuto fallito (HTTP $HTTP_CODE): $RESPONSE_BODY"
fi

# Verifica mapping inattivo creato
echo -e "\n8️⃣ Verifica mapping inattivo creato..."
MAPPING_FINAL=$(curl -s $(add_cookie) "http://$HOST/admin/manus/mapping/list")
if echo "$MAPPING_FINAL" | grep -q "u_unknown"; then
    log_success "Mapping inattivo creato per utente sconosciuto"
else
    log_warning "Mapping inattivo non trovato per utente sconosciuto"
fi

echo -e "\n🎯 TEST HTTP DIRETTI COMPLETATI"
echo "=================================="
log_success "Tutti i test principali completati!"

echo -e "\n📊 Risultati attesi:"
echo "- Health check: {\"status\":\"ok\"}"
echo "- Mapping creati e listati"
echo "- Coverage formazione ricalcolato"
echo "- Webhook accettati con firma valida"
echo "- Mapping inattivi creati per utenti sconosciuti"

echo -e "\n🔧 Troubleshooting:"
echo "• 401 al webhook → Secret errato o firma non calcolata bene"
echo "• 403/401 alle admin routes → aggiungi Cookie/Token valido"
echo "• 200 ma coverage non cambia → l'utente non è mappato: crea mapping e ripeti"
