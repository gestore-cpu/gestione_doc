# 📦 Script Migrazione DOCS Mercury

> Script per migrare utenti e guest dal modulo DOCS standard al modulo DOCS Mercury

## 📋 Panoramica

Questi script permettono di migrare in modo sicuro i dati dal modulo DOCS standard al modulo DOCS Mercury (IP 138.68.80.169).

## 🚀 Avvio Rapido

### 1. Configurazione

```bash
# Copia file di configurazione
cp scripts/config_migrazione.env.example scripts/config_migrazione.env

# Modifica le variabili ambiente
nano scripts/config_migrazione.env
```

### 2. Test Connessioni

```bash
# Carica variabili ambiente
source scripts/config_migrazione.env

# Test connessioni
python scripts/test_migrazione.py
```

### 3. Esecuzione Migrazione

```bash
# Esecuzione sicura con backup
./scripts/run_migrazione.sh

# Oppure manuale
python scripts/migrazione_docs_mercury.py --dry-run
python scripts/migrazione_docs_mercury.py
```

## 📁 File Script

### `migrazione_docs_mercury.py`
Script principale di migrazione.

**Funzionalità:**
- Migrazione utenti Mercury
- Migrazione guest Mercury
- Controllo duplicati
- Logging dettagliato
- Statistiche migrazione

**Opzioni:**
- `--dry-run`: Simula migrazione senza scrivere
- `--overwrite`: Aggiorna record esistenti
- `--verbose`: Output dettagliato

### `test_migrazione.py`
Script di test per verificare connessioni e dati.

**Funzionalità:**
- Test connessioni database
- Analisi dati origine
- Analisi dati destinazione
- Verifica duplicati
- Statistiche pre-migrazione

### `run_migrazione.sh`
Script bash per esecuzione sicura.

**Funzionalità:**
- Backup automatico
- Test pre-migrazione
- Conferme utente
- Dry-run automatico
- Logging colorato

## ⚙️ Configurazione

### Variabili Ambiente

```bash
# Database origine (DOCS standard)
SOURCE_DB_URL=postgresql://user:pass@localhost:5432/docs_standard

# Database destinazione (DOCS Mercury)
DEST_DB_URL=postgresql://user:pass@localhost:5432/docs_mercury

# Configurazione logging
LOG_LEVEL=INFO
LOG_FILE=logs/migrazione_docs_mercury.log
```

### Tipi Database Supportati

- **PostgreSQL**: `postgresql://user:pass@host:port/db`
- **MySQL**: `mysql://user:pass@host:port/db`
- **SQLite**: `sqlite:///path/to/database.db`

## 🔍 Cosa Viene Migrato

### Utenti
- **Criteri**: Utenti con `azienda="Mercury Surgelati"` o `modulo="Mercury"`
- **Campi**: id, username, email, password (hash), first_name, last_name, role, created_at, access_expiration
- **Controlli**: Evita duplicati su email

### Guest
- **Criteri**: Guest che hanno accesso a documenti Mercury
- **Campi**: id, email, password_hash, registered_at
- **Controlli**: Evita duplicati su email

## 🛡️ Sicurezza

### Protezioni Implementate
- ✅ **Password**: Mantiene hash esistenti, mai in chiaro
- ✅ **Connessioni**: Protette da variabili ambiente
- ✅ **Logging**: Solo info necessarie, no dati sensibili
- ✅ **Backup**: Automatico prima della migrazione
- ✅ **Dry-run**: Simulazione prima dell'esecuzione reale

### Controlli Duplicati
- Verifica esistenza utente/guest su email
- Opzione `--overwrite` per aggiornamento
- Log dettagliato di skip e aggiornamenti

## 📊 Report e Log

### File di Log
- `logs/migrazione_docs_mercury.log`: Log dettagliato migrazione
- `logs/test_migrazione.log`: Log test connessioni

### Statistiche Migrazione
```
📊 STATISTICHE MIGRAZIONE
==================================================
👥 Utenti importati: 25
⏭️ Utenti saltati: 3
🔄 Utenti aggiornati: 2
👤 Guest importati: 15
⏭️ Guest saltati: 1
🔄 Guest aggiornati: 0
==================================================
```

### Backup
- `backups/docs_mercury_backup_YYYYMMDD_HHMMSS.sql`: Backup PostgreSQL
- `backups/docs_mercury_backup_YYYYMMDD_HHMMSS.db`: Backup SQLite

## 🔧 Troubleshooting

### Problemi Comuni

#### 1. Errore Connessione Database
```bash
# Verifica variabili ambiente
echo $SOURCE_DB_URL
echo $DEST_DB_URL

# Test connessione manuale
psql $SOURCE_DB_URL -c "SELECT 1"
```

#### 2. Permessi File
```bash
# Rendi eseguibili gli script
chmod +x scripts/*.py scripts/*.sh
```

#### 3. Dipendenze Python
```bash
# Installa dipendenze
pip install sqlalchemy psycopg2-binary
```

#### 4. Log Dettagliati
```bash
# Esegui con logging verboso
python scripts/migrazione_docs_mercury.py --verbose
```

### Debug Avanzato

#### Analisi Dati Origine
```bash
# Query manuale utenti Mercury
psql $SOURCE_DB_URL -c "
SELECT COUNT(*) as user_count
FROM users 
WHERE company_id IN (
    SELECT id FROM companies WHERE name LIKE '%Mercury%'
);
"
```

#### Verifica Destinazione
```bash
# Query manuale utenti destinazione
psql $DEST_DB_URL -c "
SELECT COUNT(*) as user_count, role
FROM users 
GROUP BY role;
"
```

## 📈 Monitoraggio

### Metriche da Controllare
- **Utenti migrati**: Numero utenti trasferiti
- **Guest migrati**: Numero guest trasferiti
- **Duplicati**: Email già esistenti
- **Errori**: Problemi durante migrazione
- **Performance**: Tempo di esecuzione

### Comandi Utili
```bash
# Controlla log in tempo reale
tail -f logs/migrazione_docs_mercury.log

# Statistiche rapide
grep "importati\|saltati\|aggiornati" logs/migrazione_docs_mercury.log

# Errori
grep "ERROR" logs/migrazione_docs_mercury.log
```

## 🔄 Riutilizzo

### Migrazione Altri Moduli
Gli script sono progettati per essere riutilizzabili:

1. **Modifica criteri**: Cambia query per altri moduli
2. **Aggiorna mapping**: Adatta campi per altri database
3. **Estendi funzioni**: Aggiungi nuove entità da migrare

### Esempio Altro Modulo
```python
# Modifica in migrazione_docs_mercury.py
def get_other_module_users(self) -> List[Dict]:
    query = """
        SELECT * FROM users 
        WHERE company_id IN (
            SELECT id FROM companies WHERE name LIKE '%AltroModulo%'
        )
    """
    # ... resto del codice
```

## 📞 Supporto

### Contatti
- **Email**: support@synthia-ai.com
- **Documentazione**: [docs.synthia-ai.com](https://docs.synthia-ai.com)
- **Issues**: [GitHub Issues](https://github.com/synthia-ai/docs-mercury/issues)

### Log Files
- `logs/migrazione_docs_mercury.log`: Log principale
- `logs/test_migrazione.log`: Log test
- `backups/`: Backup database

---

**Versione**: 2.0.0  
**Ultimo aggiornamento**: 2025-01-27  
**Compatibilità**: PostgreSQL, MySQL, SQLite 