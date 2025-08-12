# 🚀 Manus Core - Go-Live Checklist

## 📋 Checklist Pre-Go-Live

### 1. Migrazioni Database
```bash
# Attiva ambiente virtuale
source .venv/bin/activate

# Genera migrazione
alembic revision --autogenerate -m "QMS Manus models"

# Applica migrazione
alembic upgrade head

# Verifica tabelle create
sqlite3 gestione.db ".tables" | grep manus
```

**✅ Tabelle attese:**
- `manus_manual_link`
- `manus_course_link` 
- `training_completion_manus`

### 2. Configurazione Ambiente

#### Opzione A: Systemd (Consigliato)
```bash
# Modifica configurazione gunicorn
sudo systemctl edit gunicorn

# Aggiungi in [Service]:
Environment=MANUS_BASE_URL=https://api.manus.example/v1
Environment=MANUS_API_KEY=your_real_api_key
Environment=MANUS_WEBHOOK_SECRET=your_real_webhook_secret

# Ricarica configurazione
sudo systemctl daemon-reload
```

#### Opzione B: File .env
```bash
# Aggiungi al file .env
MANUS_BASE_URL=https://api.manus.example/v1
MANUS_API_KEY=your_real_api_key
MANUS_WEBHOOK_SECRET=your_real_webhook_secret
```

### 3. Riavvio Server
```bash
# Riavvio completo
sudo systemctl restart gunicorn

# Verifica status
sudo systemctl status gunicorn --no-pager

# Controlla log per errori
sudo journalctl -u gunicorn -f
```

### 4. Test Funzionalità

#### Test Rapido Automatico
```bash
# Esegui script di test
./test_manus_quick.sh
```

#### Test Manuale
```bash
# 1. Health check webhook
curl -X GET http://localhost:5000/webhooks/manus/hooks/health

# 2. Sync manuale manuali
curl -X POST http://localhost:5000/admin/manus/sync/manuals \
  -H "Content-Type: application/json" \
  -d '{"azienda_id":1,"azienda_ref":"mercury"}'

# 3. Sync manuale corsi
curl -X POST http://localhost:5000/admin/manus/sync/courses \
  -H "Content-Type: application/json" \
  -d '{"azienda_id":1,"azienda_ref":"mercury"}'

# 4. Status sistema
curl -X GET http://localhost:5000/admin/manus/status
```

### 5. Test Webhook HMAC
```bash
# Calcola firma HMAC
BODY='{"course_id":"COURSE123"}'
SECRET="your_real_webhook_secret"
SIG=$(printf "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -r | awk '{print $1}')

# Test webhook
curl -X POST http://localhost:5000/webhooks/manus/hooks \
  -H "X-Manus-Event: COURSE_COMPLETED" \
  -H "X-Manus-Signature: $SIG" \
  -H "Content-Type: application/json" \
  -d "$BODY"
```

### 6. Verifica Database
```sql
-- Verifica tabelle
.tables

-- Controlla manuali sincronizzati
SELECT COUNT(*) FROM manus_manual_link;

-- Controlla corsi sincronizzati  
SELECT COUNT(*) FROM manus_course_link;

-- Controlla completamenti
SELECT COUNT(*) FROM training_completion_manus;
```

### 7. Verifica Scheduler
```bash
# Controlla job registrati
sqlite3 jobs.db "SELECT id, next_run_time FROM apscheduler_jobs WHERE id LIKE '%manus%';"

# Monitora log job
sudo journalctl -u gunicorn -f | grep -E "manus_sync_nightly|manus_compl_hourly"
```

## 🎯 Criteri di Accettazione (DoD)

### ✅ Funzionalità Core
- [ ] Migrazioni applicate senza errori
- [ ] Server riavviato e operativo
- [ ] Endpoint `/admin/manus/status` risponde
- [ ] Sync manuale manuali funziona
- [ ] Sync manuale corsi funziona
- [ ] Webhook con firma HMAC accettato
- [ ] Job scheduler registrati e operativi

### ✅ Database
- [ ] Tabelle `manus_*` create correttamente
- [ ] Indici e vincoli applicati
- [ ] Relazioni foreign key funzionanti

### ✅ Sicurezza
- [ ] Autenticazione admin richiesta per sync
- [ ] Verifica firma HMAC webhook attiva
- [ ] Rate limiting applicato
- [ ] Log audit attivi

### ✅ Monitoraggio
- [ ] Log job scheduler visibili
- [ ] Errori catturati e loggati
- [ ] Metriche performance disponibili

## 🚨 Piano B - Troubleshooting

### Problemi Comuni

#### 401 Unauthorized ai webhook
```bash
# Verifica secret configurato
echo $MANUS_WEBHOOK_SECRET

# Controlla firma calcolata
BODY='{"test":"data"}'
SECRET="your_secret"
echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET"
```

#### 404 Completamenti non trovati
```sql
-- Verifica link corso esistente
SELECT * FROM manus_course_link WHERE manus_course_id = 'COURSE123';
```

#### Nessun documento creato
```sql
-- Verifica mapping titolo
SELECT * FROM documents WHERE title LIKE '%Manual%';

-- Controlla permessi utente
SELECT * FROM users WHERE id = 1;
```

#### Job scheduler non operativi
```bash
# Riavvia scheduler
sudo systemctl restart gunicorn

# Verifica job registrati
sqlite3 jobs.db "SELECT * FROM apscheduler_jobs;"
```

### Log di Debug
```bash
# Log completi gunicorn
sudo journalctl -u gunicorn -f

# Log specifici Manus
sudo journalctl -u gunicorn -f | grep -i manus

# Log errori
sudo journalctl -u gunicorn -f | grep -i error
```

## 📊 Metriche Post-Go-Live

### Monitoraggio Continuo
- **Sync Rate**: Numero sync completati/ora
- **Error Rate**: Errori sync per giorno
- **Webhook Rate**: Webhook ricevuti/ora
- **Job Success**: Job scheduler completati con successo

### Alert da Configurare
- Sync falliti consecutivi > 3
- Webhook con firma non valida
- Job scheduler non eseguiti
- Errori database persistenti

## 🔄 Prossimi Passi

### Fase 2: Mapping Utenti
- Implementare mapping SSO/HR per `user_id_internal`
- Gestire utenti non trovati
- Logica fallback per completamenti

### Fase 3: UI Enhancement
- Badge "Origine: Manus" nei documenti
- Colonna "Corso Manus" nei requisiti
- Report copertura formazione integrato

### Fase 4: Multi-Tenant
- Supporto multiple aziende
- Configurazione per-tenant
- Isolamento dati per azienda

---

**📞 Supporto:** In caso di problemi, controlla i log e consulta la sezione troubleshooting.
