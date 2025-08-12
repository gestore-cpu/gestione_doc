#!/usr/bin/env bash
set -euo pipefail

echo "🚀 GO-LIVE MAPPING MANUS"
echo "=========================="

echo "[1/3] Migrations..."
source .venv/bin/activate
alembic upgrade head

echo "[2/3] Restart gunicorn..."
sudo systemctl restart gunicorn
sleep 3
sudo systemctl status gunicorn --no-pager | head -10

echo "[3/3] Smoke test..."
echo "Test 1: Crea mapping..."
curl -sS -X POST http://localhost:5000/admin/manus/mapping/create \
  -H "Content-Type: application/json" \
  -d '{"manus_user_id":"u_abc123","syn_user_id":42,"email":"user@example.com"}' | tee /tmp/mapping_create.json

echo -e "\nTest 2: Lista mapping..."
curl -sS http://localhost:5000/admin/manus/mapping/list | tee /tmp/mapping_list.json

echo -e "\nTest 3: Ricalcola coverage..."
curl -sS -X POST http://localhost:5000/admin/manus/coverage/rebuild/42 | tee /tmp/coverage_rebuild.json

echo -e "\n✅ DONE."
echo "📊 Risultati salvati in:"
echo "   /tmp/mapping_create.json"
echo "   /tmp/mapping_list.json" 
echo "   /tmp/coverage_rebuild.json"
