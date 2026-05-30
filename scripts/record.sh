#!/usr/bin/env bash
# record.sh — convenience wrapper for memory/recorder.py
#
# Usage:
#   bash scripts/record.sh start          # start a new session
#   bash scripts/record.sh end [good|bad] # end session and signal quality (default: good)
#   bash scripts/record.sh status         # show active session ID
#   bash scripts/record.sh list           # list recent sessions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RECORDER="$REPO_ROOT/memory/recorder.py"
DB="$REPO_ROOT/memory/sessions.db"

CMD="${1:-}"

if [[ -z "$CMD" ]]; then
  echo "uso: bash scripts/record.sh start|end [good|bad]|status|list"
  exit 1
fi

# Auto-init db on first run
if [[ ! -f "$DB" ]]; then
  echo "→ Inicializando sessions.db..."
  python3 "$RECORDER" --init
fi

case "$CMD" in
  start)
    python3 "$RECORDER" --start
    ;;
  end)
    SIGNAL="${2:-good}"
    python3 "$RECORDER" --end
    python3 "$RECORDER" --signal "$SIGNAL"
    echo ""
    echo "→ Sessões recentes:"
    python3 "$RECORDER" --list --limit 5
    echo ""
    GOOD_COUNT=$(python3 - << 'EOF'
import sqlite3, pathlib
db = pathlib.Path("memory/sessions.db")
if not db.exists():
    print(0)
else:
    conn = sqlite3.connect(db)
    count = conn.execute("SELECT COUNT(*) FROM sessions WHERE quality_signal = 'good'").fetchone()[0]
    print(count)
EOF
)
    if [[ "$GOOD_COUNT" -ge 3 ]]; then
      echo "✓ $GOOD_COUNT sessões boas acumuladas — pronto para distilação!"
      echo "  Execute: bash loops/distill.sh"
    else
      echo "  Sessões boas: $GOOD_COUNT/3 (mínimo para distill.sh)"
    fi
    ;;
  status)
    STATE="$REPO_ROOT/memory/.active-session"
    if [[ -f "$STATE" ]]; then
      echo "Sessão ativa: $(cat "$STATE")"
    else
      echo "Nenhuma sessão ativa."
    fi
    ;;
  list)
    python3 "$RECORDER" --list --limit "${2:-10}"
    ;;
  *)
    echo "Comando desconhecido: $CMD"
    echo "uso: bash scripts/record.sh start|end [good|bad]|status|list"
    exit 1
    ;;
esac
