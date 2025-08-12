#!/bin/bash

# Script di esecuzione migrazione DOCS Mercury
# Esegue backup e migrazione in modo sicuro

set -e  # Exit on error

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzione per stampare messaggi colorati
print_message() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

print_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

print_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Verifica che siamo nella directory corretta
if [ ! -f "app.py" ]; then
    print_error "Eseguire lo script dalla directory root del progetto"
    exit 1
fi

# Verifica variabili ambiente
if [ -z "$SOURCE_DB_URL" ] || [ -z "$DEST_DB_URL" ]; then
    print_error "Variabili ambiente SOURCE_DB_URL e DEST_DB_URL non impostate"
    print_info "Carica le variabili ambiente:"
    print_info "source scripts/config_migrazione.env"
    exit 1
fi

print_message "🚀 AVVIO SCRIPT MIGRAZIONE DOCS MERCURY"
print_message "=========================================="

# Funzione per creare backup
create_backup() {
    local db_url=$1
    local backup_name=$2
    
    print_info "Creazione backup: $backup_name"
    
    if [[ $db_url == postgresql://* ]]; then
        # Backup PostgreSQL
        local db_name=$(echo $db_url | sed 's/.*\///')
        local host=$(echo $db_url | sed 's/.*@\([^:]*\).*/\1/')
        local user=$(echo $db_url | sed 's/.*:\/\/\([^:]*\):.*/\1/')
        
        pg_dump -h $host -U $user $db_name > "backups/${backup_name}_$(date +%Y%m%d_%H%M%S).sql"
        
    elif [[ $db_url == sqlite://* ]]; then
        # Backup SQLite
        local db_path=$(echo $db_url | sed 's/sqlite:\/\///')
        cp "$db_path" "backups/${backup_name}_$(date +%Y%m%d_%H%M%S).db"
        
    else
        print_warning "Tipo database non supportato per backup automatico: $db_url"
    fi
}

# Crea directory backup se non esiste
mkdir -p backups
mkdir -p logs

# Backup database destinazione
print_message "📦 Creazione backup database destinazione..."
create_backup "$DEST_DB_URL" "docs_mercury_backup"

# Test connessioni
print_message "🔍 Test connessioni database..."
python scripts/test_migrazione.py
if [ $? -ne 0 ]; then
    print_error "Test connessioni fallito!"
    exit 1
fi

# Chiedi conferma all'utente
echo
print_warning "ATTENZIONE: Stai per eseguire la migrazione dei dati!"
print_info "Database origine: $SOURCE_DB_URL"
print_info "Database destinazione: $DEST_DB_URL"
echo
read -p "Vuoi procedere con la migrazione? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Migrazione annullata dall'utente"
    exit 0
fi

# Esegui dry-run prima
print_message "🔍 Esecuzione dry-run..."
python scripts/migrazione_docs_mercury.py --dry-run
if [ $? -ne 0 ]; then
    print_error "Dry-run fallito! Controlla i log per dettagli"
    exit 1
fi

# Chiedi conferma per migrazione reale
echo
read -p "Dry-run completato. Procedere con la migrazione reale? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Migrazione reale annullata dall'utente"
    exit 0
fi

# Esegui migrazione reale
print_message "🚀 Esecuzione migrazione reale..."
python scripts/migrazione_docs_mercury.py
if [ $? -eq 0 ]; then
    print_message "✅ MIGRAZIONE COMPLETATA CON SUCCESSO!"
    
    # Mostra statistiche finali
    echo
    print_info "📊 STATISTICHE FINALI:"
    print_info "Controlla il file logs/migrazione_docs_mercury.log per dettagli"
    
    # Test finale
    print_message "🧪 Test finale connessioni..."
    python scripts/test_migrazione.py
    
else
    print_error "❌ MIGRAZIONE FALLITA!"
    print_error "Controlla il file logs/migrazione_docs_mercury.log per dettagli"
    exit 1
fi

print_message "🎉 Script completato!"
print_info "Backup disponibili in: backups/"
print_info "Log disponibili in: logs/" 