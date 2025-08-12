# 🚀 GO-LIVE MANUS CORE - COMANDI RAPIDI

## 1. MINI CHECK FINALE (ordine 1→6)

```bash
# Esegui il mini check completo
chmod +x go_live_final.sh
./go_live_final.sh
```

**Se tutto → 200/expected, vai al punto 2.**

## 2. MONITORAGGIO PER 30-60 MINUTI

```bash
# Monitoraggio log in tempo reale
journalctl -u gunicorn -f | grep -i manus

# Oppure usa lo script di monitoraggio
chmod +x monitor_manus.sh
./monitor_manus.sh

# Monitoraggio automatico ogni 5 minuti
./monitor_manus.sh auto
```

## 3. METRICHE DA MONITORARE

- ✅ **webhook rate/secondi**
- ✅ **errori (401/5xx)**
- ✅ **fallimenti coverage/rebuild**

## 4. ALERT MINIMI

- 🚨 **5xx > 5/min su /webhooks/manus/hooks** ⇒ avviso
- 🚨 **fallimenti coverage/rebuild** ⇒ avviso

## 5. SAFETY SWITCHES

### Feature Flag per Webhook Processing
```bash
# Disabilita webhook (emergenza)
export MANUS_WEBHOOK_ENABLED=false
sudo systemctl restart gunicorn

# Riabilita webhook
export MANUS_WEBHOOK_ENABLED=true
sudo systemctl restart gunicorn
```

### Rate Limit
- ✅ **Admin routes**: già protette
- ✅ **Webhook**: burst control 60/min (configurato in safety_switches.py)

## 6. SECURITY QUICKIES

### Rotazione Periodica MANUS_WEBHOOK_SECRET
```bash
# Genera nuovo secret
python3 -c "
from safety_switches import rotate_webhook_secret
new_secret = rotate_webhook_secret()
print(f'Nuovo secret: {new_secret}')
"

# Aggiorna configurazione
sudo systemctl edit gunicorn
# Aggiungi: Environment=MANUS_WEBHOOK_SECRET=new_secret_here
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

### Verifica CORS/CSRF
- ✅ **Admin JSON routes**: CORS/CSRF non necessari (API interne)
- ✅ **Webhook routes**: HMAC già protegge

### Log Event ID/Delivery ID
- ✅ **Configurato**: logga `X-Manus-Event-ID` e `X-Manus-Delivery-ID` se inviati

## 7. COMANDI RAPIDI DI EMERGENZA

### Disabilita Webhook (Emergenza)
```bash
export MANUS_WEBHOOK_ENABLED=false
sudo systemctl restart gunicorn
```

### Controlla Status
```bash
# Status Gunicorn
sudo systemctl status gunicorn --no-pager

# Log recenti
journalctl -u gunicorn -n 50 --no-pager

# Health check
curl -s http://localhost:5000/webhooks/manus/hooks/health
```

### Rotazione Secret (Sicurezza)
```bash
# Genera e applica nuovo secret
python3 -c "from safety_switches import rotate_webhook_secret; print(rotate_webhook_secret())"
```

## 8. MONITORAGGIO AVANZATO

### Statistiche Rapide
```bash
./monitor_manus.sh stats
```

### Health Check Completo
```bash
./monitor_manus.sh health
```

### Controlli Sicurezza
```bash
./monitor_manus.sh security
```

### Monitoraggio Continuo
```bash
./monitor_manus.sh auto
```

## 9. TROUBLESHOOTING RAPIDO

### 401/403 su Admin
```bash
# Verifica session ID
curl -s http://localhost:5000/admin/manus/mapping/list -H "Cookie: session=YOUR_SESSION_ID"
```

### 401 su Webhook
```bash
# Verifica secret e firma
SECRET='your_secret_here'
BODY='{"course_id":"TEST","manus_user_id":"u_test","email":"test@example.com"}'
SIG=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -r | awk '{print $1}')
echo "Firma calcolata: $SIG"
```

### Timeout/504
```bash
# Controlla log
journalctl -u gunicorn -n 80 --no-pager

# Riavvia se necessario
sudo systemctl restart gunicorn
```

## 10. CHECKLIST GO-LIVE

- ✅ **Mini check passato** (tutti i test 200/expected)
- ✅ **Monitoraggio attivo** (30-60 min)
- ✅ **Alert configurati** (5xx > 5/min, coverage fails)
- ✅ **Safety switches pronti** (feature flag, rate limit)
- ✅ **Security verificata** (secret non default, CORS/CSRF OK)
- ✅ **Logging configurato** (event_id, delivery_id)

## 🎯 GO-LIVE COMPLETATO!

Se tutto è verde → **Manus Core è in produzione!** 🚀
