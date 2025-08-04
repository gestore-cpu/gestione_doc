#!/usr/bin/env bash
cd /var/www/gestione_doc

# Esporta tutte le variabili da .env
set -o allexport
source /var/www/gestione_doc/.env
set +o allexport

# DEBUG: verifica che FERNET_KEY sia impostata
echo "DEBUG: FERNET_KEY=${FERNET_KEY}" >&2

# Avvia Gunicorn
exec /var/www/gestione_doc/venv/bin/gunicorn \
  --workers 3 \
  --bind 127.0.0.1:8000 \
  --access-logfile /var/www/gestione_doc/logs/access.log \
  --error-logfile  /var/www/gestione_doc/logs/error.log \
  app:app
