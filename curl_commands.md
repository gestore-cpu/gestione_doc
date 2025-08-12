# Comandi cURL per Test Manus Core

## Configurazione
```bash
# Imposta variabili
BASE_URL="http://localhost:5000"
SESSION_ID="your_session_id_here"  # Se necessario
WEBHOOK_SECRET="your_webhook_secret_here"
```

## Test Health Check
```bash
# Health check webhook
curl -sS "$BASE_URL/webhooks/manus/hooks/health"

# Health check generale (se disponibile)
curl -sS "$BASE_URL/admin/manus/status"
```

## Test Mapping Utenti
```bash
# Crea mapping
curl -sS -X POST "$BASE_URL/admin/manus/mapping/create" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=$SESSION_ID" \
  -d '{
    "manus_user_id": "u_curl123",
    "syn_user_id": 42,
    "email": "curl@example.com"
  }'

# Lista mapping
curl -sS "$BASE_URL/admin/manus/mapping/list" \
  -H "Cookie: session=$SESSION_ID"
```

## Test Coverage Formazione
```bash
# Rebuild coverage per utente
curl -sS -X POST "$BASE_URL/admin/manus/coverage/rebuild/42" \
  -H "Cookie: session=$SESSION_ID"
```

## Test Webhook HMAC
```bash
# Calcola firma HMAC
BODY='{"course_id":"COURSE_CURL123","manus_user_id":"u_curl123","email":"curl@example.com"}'
SIG=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -r | awk '{print $1}')

# Test webhook con utente mappato
curl -sS -X POST "$BASE_URL/webhooks/manus/hooks" \
  -H "X-Manus-Event: COURSE_COMPLETED" \
  -H "X-Manus-Signature: $SIG" \
  -H "Content-Type: application/json" \
  -d "$BODY"

# Test webhook con utente non mappato
BODY_UNKNOWN='{"course_id":"COURSE_CURL456","manus_user_id":"u_unknown","email":"unknown@example.com"}'
SIG_UNKNOWN=$(printf "%s" "$BODY_UNKNOWN" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -r | awk '{print $1}')

curl -sS -X POST "$BASE_URL/webhooks/manus/hooks" \
  -H "X-Manus-Event: COURSE_COMPLETED" \
  -H "X-Manus-Signature: $SIG_UNKNOWN" \
  -H "Content-Type: application/json" \
  -d "$BODY_UNKNOWN"

# Test webhook con firma non valida
curl -sS -X POST "$BASE_URL/webhooks/manus/hooks" \
  -H "X-Manus-Event: COURSE_COMPLETED" \
  -H "X-Manus-Signature: invalid_signature" \
  -H "Content-Type: application/json" \
  -d '{"course_id":"COURSE_INVALID"}'
```

## Test Eventi Webhook
```bash
# Test MANUAL_UPDATED
BODY_MANUAL='{"azienda_id":1,"azienda_ref":"mercury"}'
SIG_MANUAL=$(printf "%s" "$BODY_MANUAL" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -r | awk '{print $1}')

curl -sS -X POST "$BASE_URL/webhooks/manus/hooks" \
  -H "X-Manus-Event: MANUAL_UPDATED" \
  -H "X-Manus-Signature: $SIG_MANUAL" \
  -H "Content-Type: application/json" \
  -d "$BODY_MANUAL"

# Test COURSE_UPDATED
curl -sS -X POST "$BASE_URL/webhooks/manus/hooks" \
  -H "X-Manus-Event: COURSE_UPDATED" \
  -H "X-Manus-Signature: $SIG_MANUAL" \
  -H "Content-Type: application/json" \
  -d "$BODY_MANUAL"
```

## Test con Output Dettagliato
```bash
# Test con verbose e headers
curl -v -X POST "$BASE_URL/admin/manus/mapping/create" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=$SESSION_ID" \
  -d '{"manus_user_id":"u_verbose","syn_user_id":42,"email":"verbose@example.com"}'

# Test con timeout
curl --max-time 10 -X POST "$BASE_URL/webhooks/manus/hooks" \
  -H "X-Manus-Event: COURSE_COMPLETED" \
  -H "X-Manus-Signature: $SIG" \
  -H "Content-Type: application/json" \
  -d "$BODY"
```

## Script di Test Completo
```bash
#!/bin/bash
# Test completo in un colpo solo

BASE_URL="http://localhost:5000"
WEBHOOK_SECRET="test_secret"

echo "🧪 Test completo Manus Core..."

# 1. Health check
echo "1. Health check..."
curl -s "$BASE_URL/webhooks/manus/hooks/health" | jq '.'

# 2. Crea mapping
echo "2. Crea mapping..."
curl -s -X POST "$BASE_URL/admin/manus/mapping/create" \
  -H "Content-Type: application/json" \
  -d '{"manus_user_id":"u_test","syn_user_id":42,"email":"test@example.com"}' | jq '.'

# 3. Lista mapping
echo "3. Lista mapping..."
curl -s "$BASE_URL/admin/manus/mapping/list" | jq '.'

# 4. Webhook test
echo "4. Webhook test..."
BODY='{"course_id":"COURSE_TEST","manus_user_id":"u_test","email":"test@example.com"}'
SIG=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -r | awk '{print $1}')
curl -s -X POST "$BASE_URL/webhooks/manus/hooks" \
  -H "X-Manus-Event: COURSE_COMPLETED" \
  -H "X-Manus-Signature: $SIG" \
  -H "Content-Type: application/json" \
  -d "$BODY" | jq '.'

echo "✅ Test completati!"
```

## Troubleshooting
```bash
# Verifica se il server risponde
curl -I "$BASE_URL/"

# Verifica headers della risposta
curl -D - "$BASE_URL/webhooks/manus/hooks/health"

# Test con proxy (se necessario)
curl -x http://proxy:port "$BASE_URL/webhooks/manus/hooks/health"

# Test con certificato SSL (se HTTPS)
curl -k "$BASE_URL/webhooks/manus/hooks/health"
```
