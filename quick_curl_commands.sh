#!/usr/bin/env bash
# Comandi cURL singoli per check rapidi Manus Core
# Copia e incolla questi comandi uno alla volta

# Configurazione - MODIFICA QUESTI VALORI
HOST="localhost:5000"  # Sostituisci con il tuo dominio/IP
SESSION_ID=""  # Inserisci il session ID se necessario
MANUS_WEBHOOK_SECRET="test_secret"  # Sostituisci con il secret reale

echo "🧪 COMANDI cURL SINGOLI PER CHECK RAPIDI"
echo "========================================"
echo "Modifica HOST, SESSION_ID e MANUS_WEBHOOK_SECRET all'inizio del file"
echo ""

# 1) Health GET/HEAD (no auth)
echo "=== 1) Health GET/HEAD (no auth) ==="
echo "# GET"
echo "curl -sS http://$HOST/webhooks/manus/hooks/health"
echo "Atteso: {\"status\":\"ok\"}"
echo ""
echo "# HEAD"
echo "curl -sS -I http://$HOST/webhooks/manus/hooks/health | head -n1"
echo "Atteso: HTTP/1.1 200 OK"
echo ""

# 2) Admin API (ricorda Cookie/Token se protette)
echo "=== 2) Admin API (ricorda Cookie/Token se protette) ==="
echo "# Crea mapping"
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
echo "Atteso: {\"ok\":true,...}"
echo ""
echo "# Lista mapping"
if [ -n "$SESSION_ID" ]; then
    echo "curl -sS http://$HOST/admin/manus/mapping/list \\"
    echo "  -H \"Cookie: session=$SESSION_ID\""
else
    echo "curl -sS http://$HOST/admin/manus/mapping/list"
fi
echo "Atteso: riga con u_test in lista"
echo ""

# 3) Coverage rebuild (admin)
echo "=== 3) Coverage rebuild (admin) ==="
if [ -n "$SESSION_ID" ]; then
    echo "curl -sS -X POST http://$HOST/admin/manus/coverage/rebuild/42 \\"
    echo "  -H \"Cookie: session=$SESSION_ID\""
else
    echo "curl -sS -X POST http://$HOST/admin/manus/coverage/rebuild/42"
fi
echo "Atteso: {\"ok\":true,\"updated\":<n>}"
echo ""

# 4) Webhook (HMAC reale)
echo "=== 4) Webhook (HMAC reale) ==="
echo "# Calcola firma HMAC:"
echo "SECRET='$MANUS_WEBHOOK_SECRET'"
echo "BODY='{\"course_id\":\"COURSE123\",\"manus_user_id\":\"u_test\",\"email\":\"test@example.com\"}'"
echo "SIG=\$(printf \"%s\" \"\$BODY\" | openssl dgst -sha256 -hmac \"\$SECRET\" -r | awk '{print \$1}')"
echo ""
echo "# Test webhook:"
echo "curl -sS -X POST http://$HOST/webhooks/manus/hooks \\"
echo "  -H \"X-Manus-Event: COURSE_COMPLETED\" \\"
echo "  -H \"X-Manus-Signature: \$SIG\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d \"\$BODY\""
echo "Atteso: {\"status\":\"ok\"}"
echo ""
echo "# Poi rifai lista mapping e verifica coverage aggiornato"
echo "# Con email sconosciuta → deve crearsi un mapping inattivo \"da revisionare\""
echo ""

# Test webhook con utente sconosciuto
echo "=== Test webhook con utente sconosciuto ==="
echo "# Calcola firma HMAC:"
echo "BODY_UNKNOWN='{\"course_id\":\"COURSE456\",\"manus_user_id\":\"u_unknown\",\"email\":\"unknown@example.com\"}'"
echo "SIG_UNKNOWN=\$(printf \"%s\" \"\$BODY_UNKNOWN\" | openssl dgst -sha256 -hmac \"\$SECRET\" -r | awk '{print \$1}')"
echo ""
echo "# Test webhook:"
echo "curl -sS -X POST http://$HOST/webhooks/manus/hooks \\"
echo "  -H \"X-Manus-Event: COURSE_COMPLETED\" \\"
echo "  -H \"X-Manus-Signature: \$SIG_UNKNOWN\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d \"\$BODY_UNKNOWN\""
echo "Atteso: {\"status\":\"ok\"} e mapping inattivo creato"
echo ""

echo "🔧 Quick Fix (se qualcosa stona):"
echo "• 401/403 admin → manca Cookie/Bearer"
echo "• 401 webhook → secret/firma non combaciano"
echo "• 200 ma coverage invariato → crea mapping → rifai rebuild"
echo "• Timeout/504 → riavvia Gunicorn e controlla log:"
echo "  journalctl -u gunicorn -n 100 --no-pager"
