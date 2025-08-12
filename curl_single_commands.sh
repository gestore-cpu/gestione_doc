#!/usr/bin/env bash
# Comandi cURL singoli per test Manus Core
# Copia e incolla questi comandi uno alla volta

# Configurazione - MODIFICA QUESTI VALORI
HOST="localhost:5000"  # Sostituisci con il tuo dominio/IP
SESSION_ID=""  # Inserisci il session ID se necessario
MANUS_WEBHOOK_SECRET="test_secret"  # Sostituisci con il secret reale

echo "🧪 COMANDI cURL SINGOLI PER TEST MANUS"
echo "======================================"
echo "Modifica HOST, SESSION_ID e MANUS_WEBHOOK_SECRET all'inizio del file"
echo ""

# A) Health webhook (no auth)
echo "=== A) Health webhook (no auth) ==="
echo "curl -sS http://$HOST/webhooks/manus/hooks/health"
echo "Atteso: {\"status\":\"ok\"}"
echo ""

# B) Crea mapping (admin)
echo "=== B) Crea mapping (admin) ==="
if [ -n "$SESSION_ID" ]; then
    echo "curl -sS -X POST http://$HOST/admin/manus/mapping/create \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -H \"Cookie: session=$SESSION_ID\" \\"
    echo "  -d '{\"manus_user_id\":\"u_test\",\"syn_user_id\":42,\"email\":\"test@example.com\"}'"
else
    echo "curl -sS -X POST http://$HOST/admin/manus/mapping/create \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"manus_user_id\":\"u_test\",\"syn_user_id\":42,\"email\":\"test@example.com\"}'"
fi
echo ""

# C) Lista mapping (admin)
echo "=== C) Lista mapping (admin) ==="
if [ -n "$SESSION_ID" ]; then
    echo "curl -sS http://$HOST/admin/manus/mapping/list \\"
    echo "  -H \"Cookie: session=$SESSION_ID\""
else
    echo "curl -sS http://$HOST/admin/manus/mapping/list"
fi
echo ""

# D) Ricalcola coverage per utente (admin)
echo "=== D) Ricalcola coverage per utente (admin) ==="
if [ -n "$SESSION_ID" ]; then
    echo "curl -sS -X POST http://$HOST/admin/manus/coverage/rebuild/42 \\"
    echo "  -H \"Cookie: session=$SESSION_ID\""
else
    echo "curl -sS -X POST http://$HOST/admin/manus/coverage/rebuild/42"
fi
echo ""

# E) Webhook completamento (HMAC)
echo "=== E) Webhook completamento (HMAC) ==="
echo "# Calcola firma HMAC:"
echo "BODY='{\"course_id\":\"COURSE123\",\"manus_user_id\":\"u_test\",\"email\":\"test@example.com\"}'"
echo "SIG=\$(printf \"%s\" \"\$BODY\" | openssl dgst -sha256 -hmac \"$MANUS_WEBHOOK_SECRET\" -r | awk '{print \$1}')"
echo ""
echo "# Test webhook:"
echo "curl -sS -X POST http://$HOST/webhooks/manus/hooks \\"
echo "  -H \"X-Manus-Event: COURSE_COMPLETED\" \\"
echo "  -H \"X-Manus-Signature: \$SIG\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d \"\$BODY\""
echo "Atteso: {\"status\":\"ok\"}"
echo ""

# Test webhook con utente sconosciuto
echo "=== Test webhook con utente sconosciuto ==="
echo "# Calcola firma HMAC:"
echo "BODY_UNKNOWN='{\"course_id\":\"COURSE456\",\"manus_user_id\":\"u_unknown\",\"email\":\"unknown@example.com\"}'"
echo "SIG_UNKNOWN=\$(printf \"%s\" \"\$BODY_UNKNOWN\" | openssl dgst -sha256 -hmac \"$MANUS_WEBHOOK_SECRET\" -r | awk '{print \$1}')"
echo ""
echo "# Test webhook:"
echo "curl -sS -X POST http://$HOST/webhooks/manus/hooks \\"
echo "  -H \"X-Manus-Event: COURSE_COMPLETED\" \\"
echo "  -H \"X-Manus-Signature: \$SIG_UNKNOWN\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d \"\$BODY_UNKNOWN\""
echo "Atteso: {\"status\":\"ok\"} e mapping inattivo creato"
echo ""

# Test webhook con firma non valida
echo "=== Test webhook con firma non valida ==="
echo "curl -sS -X POST http://$HOST/webhooks/manus/hooks \\"
echo "  -H \"X-Manus-Event: COURSE_COMPLETED\" \\"
echo "  -H \"X-Manus-Signature: invalid_signature\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"course_id\":\"COURSE_INVALID\"}'"
echo "Atteso: 401 Unauthorized"
echo ""

echo "🔧 TROUBLESHOOTING:"
echo "• 401 al webhook → Secret errato o firma non calcolata bene"
echo "• 403/401 alle admin routes → aggiungi Cookie/Token valido"
echo "• 200 ma coverage non cambia → l'utente non è mappato: crea mapping e ripeti"
