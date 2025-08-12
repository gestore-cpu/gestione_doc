#!/usr/bin/env bash
set -euo pipefail

echo "🔧 SETUP SESSIONE STABILE PER GO-LIVE"
echo "======================================"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }

# Verifica se tmux è installato
if ! command -v tmux &> /dev/null; then
    log_error "tmux non è installato. Installalo con: sudo apt install tmux"
    exit 1
fi

# Verifica se esiste già una sessione go-live
if tmux has-session -t go-live 2>/dev/null; then
    log_warning "Sessione go-live già esistente. Attaccandosi..."
    tmux attach-session -t go-live
    exit 0
fi

# Crea nuova sessione tmux
log_success "Creando nuova sessione tmux 'go-live'..."
tmux new-session -d -s go-live -c /var/www/gestione_doc

# Configura la sessione con più finestre
tmux rename-window -t go-live:0 'main'
tmux new-window -t go-live:1 -n 'logs' -c /var/www/gestione_doc
tmux new-window -t go-live:2 -n 'tests' -c /var/www/gestione_doc

# Configura finestra principale
tmux send-keys -t go-live:main 'echo "=== SESSIONE GO-LIVE MANUS ==="' Enter
tmux send-keys -t go-live:main 'echo "Directory: $(pwd)"' Enter
tmux send-keys -t go-live:main 'echo "Ambiente: source .venv/bin/activate"' Enter
tmux send-keys -t go-live:main 'source .venv/bin/activate' Enter
tmux send-keys -t go-live:main 'echo "Pronto per eseguire comandi!"' Enter

# Configura finestra logs
tmux send-keys -t go-live:logs 'echo "=== MONITORING LOGS ==="' Enter
tmux send-keys -t go-live:logs 'echo "Comandi utili:"' Enter
tmux send-keys -t go-live:logs 'echo "  journalctl -u gunicorn -f"' Enter
tmux send-keys -t go-live:logs 'echo "  tail -f /var/log/go-live-mapping.log"' Enter
tmux send-keys -t go-live:logs 'echo "  sudo systemctl status gunicorn --no-pager"' Enter

# Configura finestra tests
tmux send-keys -t go-live:tests 'echo "=== TEST MANUS ==="' Enter
tmux send-keys -t go-live:tests 'echo "Script disponibili:"' Enter
tmux send-keys -t go-live:tests 'echo "  ./go_live_mapping.sh"' Enter
tmux send-keys -t go-live:tests 'echo "  ./test_manus_http.sh"' Enter
tmux send-keys -t go-live:tests 'echo "  ./test_manus_end_to_end.sh"' Enter

# Attacca alla sessione
log_success "Sessione creata! Attaccandosi..."
tmux attach-session -t go-live

echo -e "\n📋 COMANDI UTILI NELLA SESSIONE:"
echo "=================================="
echo "• Ctrl+b c     - Nuova finestra"
echo "• Ctrl+b n     - Prossima finestra"
echo "• Ctrl+b p     - Finestra precedente"
echo "• Ctrl+b d     - Stacca dalla sessione"
echo "• Ctrl+b %     - Dividi verticalmente"
echo "• Ctrl+b \"     - Dividi orizzontalmente"
echo ""
echo "• tmux attach-session -t go-live  # Riconnetti"
echo "• tmux kill-session -t go-live    # Termina sessione"
