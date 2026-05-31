#!/usr/bin/env bash
# gate.sh — gate de validação configurável
# Substitui o py_compile hardcoded do projeto original.
# O ralph.sh chama: bash scripts/gate.sh <arquivo_ou_diretorio>
#
# Exit 0 = passou. Exit 1 = falhou. stderr recebe o motivo.

set -uo pipefail

TARGET="${1:-}"

if [[ -z "$TARGET" ]]; then
  echo "uso: bash scripts/gate.sh <arquivo_ou_diretorio>" >&2
  exit 1
fi

# ── Detecta tipo pelo contexto do projeto ─────────────────────────────────────
# Lê GATE_TYPE de .gate-config se existir, senão auto-detecta pela extensão

GATE_TYPE=""

if [[ -f "scripts/.gate-config" ]]; then
  GATE_TYPE=$(cat "scripts/.gate-config")
fi

if [[ -z "$GATE_TYPE" ]]; then
  case "$TARGET" in
    data|mock|mocks|data/mock|data-mock) GATE_TYPE="data" ;;
    *payloads_*.json|*generated_mock_tile_evidence.json|*generatedMockData.ts) GATE_TYPE="data" ;;
    *.py)   GATE_TYPE="python" ;;
    *.ts|*.tsx|*.jsx)   GATE_TYPE="typescript" ;;
    *.js)               GATE_TYPE="javascript" ;;
    *.sh)   GATE_TYPE="bash" ;;
    *.go)   GATE_TYPE="go" ;;
    *)      GATE_TYPE="python" ;; # padrão histórico
  esac
fi

# ── Executa o gate ─────────────────────────────────────────────────────────────

case "$GATE_TYPE" in

  python)
    # Gate 1: compila sem erros de sintaxe
    if [[ -f "$TARGET" ]]; then
      python3 -m py_compile "$TARGET" 2>&1 || { echo "py_compile falhou: $TARGET" >&2; exit 1; }
    else
      # diretório: verifica todos os .py
      # process substitution keeps the while loop in the current shell so exit 1 propagates
      while read -r f; do
        python3 -m py_compile "$f" 2>&1 || { echo "py_compile falhou: $f" >&2; exit 1; }
      done < <(find "$TARGET" -name "*.py")
    fi

    # Gate 2: testes da story se existirem
    if [[ -d "tests/" ]]; then
      python3 -m pytest tests/ -q --tb=short 2>&1 | tail -20 || {
        echo "pytest falhou" >&2; exit 1
      }
    fi
    ;;

  typescript)
    npx tsc --noEmit 2>&1 || { echo "tsc falhou" >&2; exit 1; }
    ;;

  javascript)
    node --check "$TARGET" 2>&1 || { echo "node --check falhou: $TARGET" >&2; exit 1; }
    ;;

  bash)
    bash -n "$TARGET" 2>&1 || { echo "bash syntax check falhou: $TARGET" >&2; exit 1; }
    ;;

  data)
    python3 scripts/semantic_data_gate.py "$TARGET" 2>&1 || { echo "semantic data gate falhou: $TARGET" >&2; exit 1; }
    ;;

  go)
    go build ./... 2>&1 || { echo "go build falhou" >&2; exit 1; }
    ;;

  custom)
    # Lê comando custom de scripts/.gate-custom
    if [[ -f "scripts/.gate-custom" ]]; then
      bash "scripts/.gate-custom" "$TARGET" 2>&1 || { echo "custom gate falhou" >&2; exit 1; }
    else
      echo "GATE_TYPE=custom mas scripts/.gate-custom não existe" >&2
      exit 1
    fi
    ;;

  *)
    echo "GATE_TYPE desconhecido: $GATE_TYPE" >&2
    exit 1
    ;;
esac

echo "gate: OK ($GATE_TYPE) → $TARGET"
exit 0
