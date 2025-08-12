#!/usr/bin/env bash
set -euo pipefail

echo "🚀 GO-LIVE MANUS CORE - ULTIMA PASSATA"
echo "======================================"

# Configurazione - MODIFICA QUESTI VALORI
HOST="localhost:5000"  # Sostituisci con il tuo dominio/IP
SESSION_ID=""  # Inserisci il session ID se necessario
MANUS_WEBHOOK_SECRET="test_secret"  # Sostituisci con il secret reale

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

echo "🔧 Configurazione:"
echo "  HOST: $HOST"
echo "  SESSION_ID: ${SESSION_ID:-'non impostato'}"
echo "  WEBHOOK_SECRET: ${MANUS_WEBHOOK_SECRET:+'impostato'}"
echo ""

# Funzione per aggiungere cookie se presente
add_cookie() {
    if [ -n "$SESSION_ID" ]; then
        echo "-H \"Cookie: session=$SESSION_ID\""
    fi
}

# Funzione per test con status code
test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local headers="$4"
    local data="$5"
    local expected_code="$6"
    
    echo -n "Test $name... "
    
    if [ -n "$data" ]; then
        response=$(curl -s -w "%{http_code}" $headers -X $method -d "$data" "$url")
    else
        response=$(curl -s -w "%{http_code}" $headers -X $method "$url")
    fi
    
    http_code="${response: -3}"
    response_body="${response%???}"
    
    if [ "$http_code" = "$expected_code" ]; then
        log_success "OK (HTTP $http_code)"
        return 0
    else
        log_error "FAIL (HTTP $http_code, atteso $expected_code)"
        echo "Response: $response_body"
        return 1
    fi
}

echo "🧪 MINI CHECK FINALE (ordine 1→6):"
echo "=================================="

# Test 1: Health GET + HEAD
echo -e "\n1️⃣ Health GET + HEAD:"
test_endpoint "Health GET" "GET" "http://$HOST/webhooks/manus/hooks/health" "" "" "200"
test_endpoint "Health HEAD" "HEAD" "http://$HOST/webhooks/manus/hooks/health" "" "" "200"

# Test 2: Admin senza auth (negativo)
echo -e "\n2️⃣ Admin senza auth (negativo):"
test_endpoint "Admin senza auth" "POST" "http://$HOST/admin/manus/mapping/create" \
    "-H \"Content-Type: application/json\"" \
    '{"manus_user_id":"u_test","syn_user_id":42,"email":"test@example.com"}' \
    "401"

# Test 3: Admin con auth (positivo)
echo -e "\n3️⃣ Admin con auth (positivo):"
test_endpoint "Admin con auth" "POST" "http://$HOST/admin/manus/mapping/create" \
    "-H \"Content-Type: application/json\" $(add_cookie)" \
    '{"manus_user_id":"u_test","syn_user_id":42,"email":"test@example.com"}' \
    "200"

# Test 4: Webhook firma sbagliata (negativo)
echo -e "\n4️⃣ Webhook firma sbagliata (negativo):"
BAD_SIG="deadbeef"
BODY='{"course_id":"COURSE123","manus_user_id":"u_test","email":"test@example.com"}'
test_endpoint "Webhook firma sbagliata" "POST" "http://$HOST/webhooks/manus/hooks" \
    "-H \"X-Manus-Event: COURSE_COMPLETED\" -H \"X-Manus-Signature: $BAD_SIG\" -H \"Content-Type: application/json\"" \
    "$BODY" "401"

# Test 5: Webhook firma corretta (positivo)
echo -e "\n5️⃣ Webhook firma corretta (positivo):"
SIG=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$MANUS_WEBHOOK_SECRET" -r | awk '{print $1}')
test_endpoint "Webhook firma corretta" "POST" "http://$HOST/webhooks/manus/hooks" \
    "-H \"X-Manus-Event: COURSE_COMPLETED\" -H \"X-Manus-Signature: $SIG\" -H \"Content-Type: application/json\"" \
    "$BODY" "200"

# Test 6: Coverage rebuild
echo -e "\n6️⃣ Coverage rebuild:"
test_endpoint "Coverage rebuild" "POST" "http://$HOST/admin/manus/coverage/rebuild/42" \
    "$(add_cookie)" "" "200"

echo -e "\n🎯 MINI CHECK COMPLETATO"
echo "=========================="

# Verifica se tutti i test sono passati
if [ $? -eq 0 ]; then
    log_success "TUTTI I TEST PASSATI! GO-LIVE PRONTO!"
    echo ""
    
    echo "📊 MONITORAGGIO PER 30-60 MINUTI:"
    echo "================================="
    echo "Comando per monitorare:"
    echo "journalctl -u gunicorn -f | grep -i manus"
    echo ""
    
    echo "🔍 METRICHE DA MONITORARE:"
    echo "=========================="
    echo "• webhook rate/secondi"
    echo "• errori (401/5xx)"
    echo "• fallimenti coverage/rebuild"
    echo ""
    
    echo "🚨 ALERT MINIMI:"
    echo "================"
    echo "• 5xx > 5/min su /webhooks/manus/hooks ⇒ avviso"
    echo "• fallimenti coverage/rebuild ⇒ avviso"
    echo ""
    
    echo "🔒 SAFETY SWITCHES:"
    echo "=================="
    echo "• Feature flag: MANUS_WEBHOOK_ENABLED=true/false"
    echo "• Rate limit: admin routes (già OK) + burst control webhook (60/min)"
    echo ""
    
    echo "🔐 SECURITY QUICKIES:"
    echo "===================="
    echo "• Rotazione periodica MANUS_WEBHOOK_SECRET"
    echo "• Verifica CORS/CSRF non necessari sulle admin JSON"
    echo "• Logga event_id/delivery_id se Manus li invia (per idempotenza)"
    echo ""
    
    echo "📋 PROSSIMI PASSI:"
    echo "=================="
    echo "1. Avvia monitoraggio: journalctl -u gunicorn -f | grep -i manus"
    echo "2. Configura alert se necessario"
    echo "3. Monitora per 30-60 minuti"
    echo "4. Verifica safety switches"
    echo "5. Pianifica rotazione secret"
    
else
    log_error "ALCUNI TEST FALLITI! RIVEDERE PRIMA DEL GO-LIVE!"
    echo ""
    echo "🔧 TROUBLESHOOTING:"
    echo "• 401/403 su admin → manca Cookie/Token"
    echo "• 401 su webhook → secret/firma: ricalcola SIG dal body identico"
    echo "• 200 ma coverage invariato → crea mapping → rifai rebuild"
    echo "• Timeout/504 → journalctl -u gunicorn -n 80 --no-pager e riprova"
fi
