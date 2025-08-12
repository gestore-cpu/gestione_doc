#!/usr/bin/env bash

echo "🧪 TEST SPRINT F - REALTIME + REDIS + POLICY + EXPORT"
echo "====================================================="

HOST="localhost:5000"
SESSION_ID=""

echo "🔧 Configurazione:"
echo "  HOST: $HOST"
echo "  SESSION_ID: ${SESSION_ID:-'non impostato'}"
echo ""

echo "🧪 SMOKE TEST:"
echo "=============="

echo "1️⃣ KPI Summary:"
curl -s -X GET "http://$HOST/api/approvals/stats/summary" -w " → %{http_code}\n"

echo "2️⃣ Export CSV:"
curl -s -X GET "http://$HOST/agents/audit-log/export?fmt=csv" -w " → %{http_code}\n"

echo "3️⃣ Idempotency (prima chiamata):"
curl -s -X POST "http://$HOST/api/approvals/bulk-decision?idempotency_key=test123" \
  -H "Content-Type: application/json" \
  -d '{"ids":[1,2,3],"decision":"approve"}' \
  -w " → %{http_code}\n"

echo "4️⃣ Idempotency (seconda chiamata - duplicato):"
curl -s -X POST "http://$HOST/api/approvals/bulk-decision?idempotency_key=test123" \
  -H "Content-Type: application/json" \
  -d '{"ids":[1,2,3],"decision":"approve"}' \
  -w " → %{http_code}\n"

echo "5️⃣ Create Approval Request:"
curl -s -X POST "http://$HOST/api/approvals/create?idempotency_key=create123" \
  -H "Content-Type: application/json" \
  -d '{"risk_score":45,"amount":500,"request_type":"access_request","description":"Test request"}' \
  -w " → %{http_code}\n"

echo "6️⃣ List Approvals:"
curl -s -X GET "http://$HOST/api/approvals/list" -w " → %{http_code}\n"

echo ""
echo "🎯 SMOKE TEST COMPLETATO"
echo "=========================="
echo "✅ Se tutti i test passano → SPRINT F PRONTO!"
echo ""
echo "🔍 VERIFICHE AGGIUNTIVE:"
echo "• Redis: redis-cli ping"
echo "• WebSocket: apri dashboard in due browser"
echo "• Policy: testa approvazioni con diversi ruoli"
echo "• Export: scarica file CSV/NDJSON"
