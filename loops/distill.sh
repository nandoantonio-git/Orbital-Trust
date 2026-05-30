#!/usr/bin/env bash
# distill.sh — Ralph loop para skill distillation
# Lê trajectories boas e gera SKILL.md candidatas em skills/pending/
#
# Uso: bash loops/distill.sh [--min-sessions N] [--dry-run]

set -euo pipefail

MIN_SESSIONS="${MIN_SESSIONS:-3}"   # mínimo de sessões boas para distilação
MAX_ATTEMPTS=3
DRY_RUN=false
FORCED_PROVIDER=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --min-sessions) MIN_SESSIONS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --provider) FORCED_PROVIDER="$2"; shift 2 ;;
    *) shift ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PENDING_DIR="$REPO_ROOT/skills/pending"
ACTIVE_DIR="$REPO_ROOT/skills/active"
TRAJECTORIES="$REPO_ROOT/memory/trajectories.jsonl"

echo "╔══════════════════════════════╗"
echo "║   loom — distill loop        ║"
echo "╚══════════════════════════════╝"
echo ""

# ── Exporta trajectories boas ─────────────────────────────────────────────────

echo "→ Exportando sessões boas..."
python3 "$REPO_ROOT/memory/recorder.py" --export

if [[ ! -f "$TRAJECTORIES" ]]; then
  echo "✗ nenhuma trajectory encontrada em $TRAJECTORIES"
  echo "  Marque sessões com /good primeiro: python3 memory/recorder.py --signal good"
  exit 0
fi

SESSION_COUNT=$(wc -l < "$TRAJECTORIES")
echo "  $SESSION_COUNT sessão(ões) boas disponíveis"

if [[ "$SESSION_COUNT" -lt "$MIN_SESSIONS" ]]; then
  echo "✗ mínimo de $MIN_SESSIONS sessões necessárias (atual: $SESSION_COUNT)"
  echo "  Continue usando e marcando sessões com /good"
  exit 0
fi

# ── Monta contexto para o agente ──────────────────────────────────────────────

mkdir -p "$PENDING_DIR"

AGENTS_CONTENT=$(cat "$REPO_ROOT/AGENTS.md")
ACTIVE_SKILLS=""
if ls "$ACTIVE_DIR"/*.md &>/dev/null 2>&1; then
  ACTIVE_SKILLS=$(cat "$ACTIVE_DIR"/*.md)
fi

# Usa últimas N trajectories para não exceder contexto
TRAJECTORY_SAMPLE=$(tail -10 "$TRAJECTORIES")

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CANDIDATE_NAME="skill_${TIMESTAMP}"
CANDIDATE_PATH="$PENDING_DIR/${CANDIDATE_NAME}.md"

# ── Detecta provider ──────────────────────────────────────────────────────────

detect_provider() {
  if [[ -n "$FORCED_PROVIDER" ]]; then
    echo "$FORCED_PROVIDER"
    return
  fi
  for p in codex gemini claude; do
    if command -v "$p" &>/dev/null; then echo "$p"; return; fi
  done
  echo "none"
}

PROVIDER=$(detect_provider)

if [[ "$PROVIDER" == "none" ]]; then
  echo "✗ nenhum provider disponível (codex/gemini/claude)"
  exit 1
fi

echo "→ Provider: $PROVIDER"

# ── Loop de distilação ────────────────────────────────────────────────────────

attempt=0
passed=false

while [[ $attempt -lt $MAX_ATTEMPTS ]] && [[ "$passed" == "false" ]]; do
  attempt=$((attempt + 1))
  echo ""
  echo "→ Tentativa $attempt/$MAX_ATTEMPTS..."

  # Monta prompt
  PROMPT_FILE=$(mktemp)
  cat > "$PROMPT_FILE" << PROMPT
Você é um especialista em design de skills para agentes LLM.

Analise as trajectories de sessões bem-sucedidas abaixo e identifique
UM padrão repetível que poderia ser encapsulado como uma skill reutilizável.

## Contexto do projeto (AGENTS.md)
${AGENTS_CONTENT}

## Skills já ativas (NÃO duplique)
${ACTIVE_SKILLS:-"(nenhuma skill ativa ainda)"}

## Trajectories de sessões boas
${TRAJECTORY_SAMPLE}

## Tarefa
Gere UMA skill candidata no formato SKILL.md abaixo.
A skill deve:
1. Ter uma trigger condition inequívoca (quando o agente deve usar)
2. Cobrir um padrão que aparece em MÚLTIPLAS sessões
3. Ter instruções acionáveis (o quê fazer, não só o quê evitar)
4. Ser focada em UMA coisa só (máx 400 palavras)
5. NÃO duplicar as skills já ativas

## Formato de saída (APENAS o SKILL.md, sem texto adicional)
---
name: [nome-da-skill-em-kebab-case]
description: "[1 frase descrevendo quando usar]"
user-invocable: false
---

# [Título da Skill]

[Trigger condition clara]

## O que fazer

[Instruções acionáveis]

## O que evitar

[Anti-padrões identificados nas trajectories]
PROMPT

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "  [dry-run] prompt gerado em $PROMPT_FILE"
    cat "$PROMPT_FILE"
    rm -f "$PROMPT_FILE"
    exit 0
  fi

  # Executa provider
  case "$PROVIDER" in
    codex)
      codex -a never exec -C "$REPO_ROOT" \
        -m "gpt-5.5" \
        -c "model_reasoning_effort=\"medium\"" \
        -s danger-full-access \
        --output-last-message "$CANDIDATE_PATH" \
        < "$PROMPT_FILE" 2>/dev/null || true
      ;;
    gemini)
      PROMPT_CONTENT=$(cat "$PROMPT_FILE")
      gemini --yolo -p "$PROMPT_CONTENT" 2>/dev/null | tail -200 > "$CANDIDATE_PATH" || true
      ;;
    claude)
      PROMPT_CONTENT=$(cat "$PROMPT_FILE")
      claude -p "$PROMPT_CONTENT" 2>/dev/null > "$CANDIDATE_PATH" || true
      ;;
  esac

  rm -f "$PROMPT_FILE"

  if [[ ! -s "$CANDIDATE_PATH" ]]; then
    echo "  ✗ provider não gerou output"
    continue
  fi

  # ── Quality gate ──────────────────────────────────────────────────────────
  echo "  → Validando com score.py..."
  if python3 "$REPO_ROOT/loops/score.py" "$CANDIDATE_PATH" \
       --existing "$ACTIVE_DIR" 2>/dev/null; then
    passed=true
    echo "  ✓ skill candidata aprovada"
  else
    echo "  ✗ skill não passou o quality gate — nova tentativa"
    rm -f "$CANDIDATE_PATH"
    CANDIDATE_NAME="skill_${TIMESTAMP}_attempt${attempt}"
    CANDIDATE_PATH="$PENDING_DIR/${CANDIDATE_NAME}.md"
  fi
done

echo ""
if [[ "$passed" == "true" ]]; then
  echo "✓ Skill candidata gerada: $CANDIDATE_PATH"
  echo ""
  echo "Próximo passo — revise e promova:"
  echo "  cat $CANDIDATE_PATH"
  echo "  cp $CANDIDATE_PATH skills/active/"
  echo "  rm $CANDIDATE_PATH"
else
  echo "✗ Não foi possível gerar uma skill válida após $MAX_ATTEMPTS tentativas"
  echo "  Acumule mais sessões boas antes de rodar distill novamente"
fi
