#!/usr/bin/env bash
# init.sh — bootstrap de um novo projeto a partir do loom-template
# Uso: bash init.sh

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════╗${NC}"
echo -e "${BLUE}║       loom — init            ║${NC}"
echo -e "${BLUE}╚══════════════════════════════╝${NC}"
echo ""

# ── Coleta de informações ─────────────────────────────────────────────────────

read -rp "Nome do projeto (ex: kandrive, meu-projeto): " PROJECT_NAME
PROJECT_NAME=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

read -rp "Linguagem principal (python/typescript/bash): " LANGUAGE
LANGUAGE="${LANGUAGE:-python}"

read -rp "Descrição do projeto (1-2 frases): " PROJECT_DESCRIPTION

echo ""
echo "Gate de validação:"
echo "  1) py_compile   (Python — padrão)"
echo "  2) tsc --noEmit (TypeScript)"
echo "  3) bash lint    (Bash/shell)"
echo "  4) custom       (você define depois)"
read -rp "Escolha [1-4]: " GATE_CHOICE

case "$GATE_CHOICE" in
  1) GATE_COMMAND="python3 -m py_compile" ;;
  2) GATE_COMMAND="npx tsc --noEmit" ;;
  3) GATE_COMMAND="bash -n" ;;
  *) GATE_COMMAND="# TODO: defina o gate em scripts/gate.sh" ;;
esac

INIT_DATE=$(date +"%Y-%m-%d")

# ── Substitui placeholders no AGENTS.md ──────────────────────────────────────

echo ""
echo -e "${YELLOW}→ Configurando AGENTS.md...${NC}"

sed -i \
  -e "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" \
  -e "s/{{INIT_DATE}}/$INIT_DATE/g" \
  -e "s/{{LANGUAGE}}/$LANGUAGE/g" \
  -e "s|{{PROJECT_DESCRIPTION}}|$PROJECT_DESCRIPTION|g" \
  -e "s|{{GATE_COMMAND}}|$GATE_COMMAND|g" \
  AGENTS.md

# ── Limpa estado de execução anterior ────────────────────────────────────────

echo -e "${YELLOW}→ Limpando estado do loop...${NC}"

rm -f scripts/.current-provider \
      scripts/.last-story \
      scripts/.story-attempts \
      scripts/.prompt.md \
      scripts/.last-message.md \
      scripts/.model-check.log

# Reseta prd.json para estrutura vazia
cat > scripts/prd.json << EOF
{
  "project": "$PROJECT_NAME",
  "branchName": "loom/initial",
  "description": "Backlog inicial — use /prd para gerar as user stories",
  "userStories": []
}
EOF

# ── Inicializa sessions.db ────────────────────────────────────────────────────

echo -e "${YELLOW}→ Inicializando banco de trajectories...${NC}"

python3 memory/recorder.py --init

# ── Cria .gitignore local dos arquivos de estado ─────────────────────────────

cat > scripts/.gitignore << 'EOF'
.current-provider
.last-story
.story-attempts
.prompt.md
.last-message.md
.model-check.log
run.log
events.log
audit/
EOF

cat > memory/.gitignore << 'EOF'
sessions.db
EOF

# ── Resumo ────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}✓ Projeto '$PROJECT_NAME' inicializado${NC}"
echo ""
echo "Próximos passos:"
echo "  1. Edite AGENTS.md — preencha as Regras críticas do domínio"
echo "  2. Use /prd para gerar o backlog inicial"
echo "  3. Execute o pipeline de IoT: python3 iot/demo_video.py --input seu_video.mp4"
echo "  4. Execute a API: uvicorn api.main:app --reload"
echo ""
echo "Skill learning:"
echo "  - Marque sessões com /good ou /bad ao terminar"
echo "  - Skills candidatas aparecem em skills/pending/"
echo "  - bash loops/distill.sh  → destila padrões de sessões boas"
echo "  - bash loops/compact.sh  → comprime AGENTS.md quando crescer demais"
