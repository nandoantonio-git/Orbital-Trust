#!/usr/bin/env bash
# =============================================================================
# Orbital Trust — Audit Script
# Roda na raiz do repositório: bash audit.sh
# =============================================================================

set -uo pipefail

RED='\033[0;31m'
YEL='\033[1;33m'
GRN='\033[0;32m'
BLU='\033[1;34m'
DIM='\033[2m'
NC='\033[0m'

PASS=0
WARN=0
FAIL=0

pass() { echo -e "  ${GRN}✔${NC}  $1"; ((PASS++)) || true; }
warn() { echo -e "  ${YEL}⚠${NC}  $1"; ((WARN++)) || true; }
fail() { echo -e "  ${RED}✘${NC}  $1"; ((FAIL++)) || true; }
section() { echo -e "\n${BLU}▸ $1${NC}"; }

# =============================================================================
# 0. AMBIENTE
# =============================================================================
section "Ambiente"

if command -v python3 >/dev/null 2>&1; then
  pass "python3 disponível ($(python3 --version 2>&1))"
else
  fail "python3 não encontrado"
fi

if command -v node >/dev/null 2>&1; then
  pass "node disponível ($(node --version 2>&1))"
else
  warn "node não encontrado — testes TypeScript não rodarão"
fi

if command -v npm >/dev/null 2>&1; then
  pass "npm disponível"
else
  warn "npm não encontrado"
fi

# =============================================================================
# 1. ESTRUTURA DE ARQUIVOS OBRIGATÓRIOS
# =============================================================================
section "Estrutura obrigatória"

check_file() {
  local f="$1" label="$2"
  if [[ -f "$f" ]]; then
    pass "$label presente ($f)"
  else
    fail "$label ausente: $f"
  fi
}

check_dir() {
  local d="$1" label="$2"
  if [[ -d "$d" ]]; then
    pass "$label presente ($d)"
  else
    fail "$label ausente: $d"
  fi
}

check_file "README.md"               "README.md"
check_file ".gitignore"              ".gitignore"
check_file "requirements.txt"        "requirements.txt (raiz)"
check_file "iot/requirements.txt"    "iot/requirements.txt"
check_dir  "iot/"                    "Diretório iot/"
check_dir  "api/"                    "Diretório api/"
check_dir  "mobile/"                 "Diretório mobile/"
check_dir  "tests/"                  "Diretório tests/"
check_file "api/main.py"             "api/main.py"
check_file "iot/pipeline.py"         "iot/pipeline.py"
check_file "iot/detector.py"         "iot/detector.py"
check_file "iot/payload.py"          "iot/payload.py"
check_file "mobile/package.json"     "mobile/package.json"

# =============================================================================
# 2. README — campos obrigatórios (Mobile/IoT)
# =============================================================================
section "README — campos obrigatórios (Mobile/IoT)"

readme_check() {
  local pattern="$1" label="$2"
  if grep -qi "$pattern" README.md 2>/dev/null; then
    pass "$label encontrado no README"
  else
    fail "$label ausente no README"
  fi
}

readme_check "RM5"                              "RMs dos integrantes"
readme_check "npm install\|pip install"         "Instruções de instalação"
readme_check "expo start\|uvicorn\|python"      "Instruções de execução"
readme_check "opencv\|mediapipe\|cv2"           "Bibliotecas de CV mencionadas"
readme_check "orbital\|satelite\|satellite\|frame" "Descrição da solução"

NAME_COUNT=$(grep -oiP '\b[A-Z][a-záàãâéêíóôõú]+\s+[A-Z][a-záàãâéêíóôõú]+\b' README.md 2>/dev/null | wc -l || echo 0)
if [[ "$NAME_COUNT" -ge 3 ]]; then
  pass "Nomes dos integrantes detectados (~${NAME_COUNT} ocorrências)"
else
  warn "Poucos nomes detectados no README — verifique se todos os integrantes estão listados"
fi

# =============================================================================
# 3. REQUIREMENTS — dependências críticas
# =============================================================================
section "Requirements — dependências críticas"

req_check() {
  local pkg="$1" file="$2"
  if grep -qi "^${pkg}" "$file" 2>/dev/null; then
    pass "$pkg em $file"
  else
    fail "$pkg ausente em $file"
  fi
}

req_check "opencv"   "iot/requirements.txt"
req_check "numpy"    "iot/requirements.txt"
req_check "fastapi"  "requirements.txt"
req_check "uvicorn"  "requirements.txt"

if [[ -f "requirements-dev.txt" ]]; then
  pass "requirements-dev.txt presente"
  req_check "pytest" "requirements-dev.txt"
else
  warn "requirements-dev.txt ausente — README o referencia em instruções de instalação"
fi

if grep -rq "certifi" requirements*.txt iot/requirements.txt 2>/dev/null; then
  pass "certifi declarado nos requirements"
else
  warn "certifi usado em scripts/generate_mock_data.py mas não declarado nos requirements"
fi

# =============================================================================
# 4. PYTHON — sintaxe e testes
# =============================================================================
section "Python — sintaxe"

py_syntax() {
  local f="$1"
  if python3 -m py_compile "$f" 2>/dev/null; then
    pass "Sintaxe OK: $f"
  else
    fail "Erro de sintaxe: $f"
  fi
}

for f in iot/pipeline.py iot/detector.py iot/payload.py iot/quality.py \
          iot/change_detector.py api/main.py \
          scripts/generate_mock_data.py scripts/regenerate_sample_payloads.py; do
  if [[ -f "$f" ]]; then
    py_syntax "$f"
  else
    warn "Arquivo não encontrado para checar sintaxe: $f"
  fi
done

section "Python — testes unitários"

if python3 -c "import cv2, numpy, fastapi" 2>/dev/null; then
  pass "Dependências Python instaladas — rodando pytest"
  python3 -m pytest tests/ -q --tb=short 2>&1 | tail -8
  PYTEST_EXIT="${PIPESTATUS[0]}"
  if [[ "$PYTEST_EXIT" -eq 0 ]]; then
    pass "pytest passou"
  else
    fail "pytest falhou (exit $PYTEST_EXIT)"
  fi
else
  warn "Dependências não instaladas — pulando pytest"
  echo -e "  ${DIM}→ rode: pip install -r requirements.txt -r requirements-dev.txt -r iot/requirements.txt${NC}"
fi

# =============================================================================
# 5. TYPESCRIPT — checagem de tipos
# =============================================================================
section "TypeScript — checagem de tipos"

if [[ -d "mobile" ]] && command -v npx >/dev/null 2>&1; then
  if [[ -f "mobile/tsconfig.json" ]]; then
    TS_OUT=$(cd mobile && npx tsc --noEmit 2>&1 | tail -5 || true)
    if [[ -z "$TS_OUT" ]]; then
      pass "TypeScript sem erros"
    else
      fail "TypeScript com erros de tipo"
      echo -e "  ${DIM}$TS_OUT${NC}"
    fi
  else
    warn "mobile/tsconfig.json não encontrado"
  fi
else
  warn "npx não disponível — pulando checagem TypeScript"
fi

# =============================================================================
# 6. CONTRATO JSON IoT → ML
# =============================================================================
section "Contrato JSON — campos obrigatórios IoT → ML"

REQUIRED_FIELDS=("event_id" "timestamp" "area_id" "source" "detected_class"
  "class_percentage" "change_score" "cloud_score" "shadow_score"
  "image_quality" "cv_confidence")

for field in "${REQUIRED_FIELDS[@]}"; do
  if grep -q "\"$field\"" iot/payload.py 2>/dev/null; then
    pass "Campo contratual '$field' em payload.py"
  else
    fail "Campo contratual '$field' AUSENTE em payload.py"
  fi
done

if grep -q "0-100\|<= 100" iot/payload.py 2>/dev/null; then
  pass "class_percentage validada na escala 0-100"
else
  warn "Não encontrada validação explícita de escala 0-100 em payload.py"
fi

# =============================================================================
# 7. PONTO DE TROCA ML — derive_risk_level
# =============================================================================
section "Ponto de troca ML"

if grep -q "derive_risk_level" api/main.py 2>/dev/null; then
  pass "Função derive_risk_level encontrada em api/main.py (ponto de substituição pelo modelo ML)"
  LINE=$(grep -n "derive_risk_level" api/main.py | head -1)
  echo -e "  ${DIM}→ $LINE${NC}"
else
  fail "derive_risk_level não encontrada — ponto de troca ML pode estar em outro local"
fi

if ls models/*.joblib models/*.pkl models/*.pkl.gz 2>/dev/null | grep -q .; then
  pass "Modelo ML serializado encontrado em models/"
else
  warn "Nenhum modelo ML em models/ — heurística ainda ativa (esperado nesta fase)"
fi

# =============================================================================
# 8. GITIGNORE — limpeza de artefatos de template
# =============================================================================
section ".gitignore — artefatos de template Ralph/Athena"

TEMPLATE_DIRS=("skills/" "loops/" "memory/" "AGENTS.md")
for item in "${TEMPLATE_DIRS[@]}"; do
  if [[ -e "$item" ]]; then
    if grep -q "^${item%/}" .gitignore 2>/dev/null; then
      warn "$item existe no repo e está no .gitignore — idealmente remover do repo"
    else
      warn "$item existe no repo mas NÃO está no .gitignore — considere remover ou ignorar"
    fi
  else
    pass "$item não existe no repo (limpo)"
  fi
done

SHOULD_IGNORE=("scripts/run.log" "scripts/.current-provider" "scripts/.last-story"
               "memory/sessions.db" "memory/trajectories.jsonl")
for item in "${SHOULD_IGNORE[@]}"; do
  if [[ -e "$item" ]]; then
    if grep -q "$(basename "$item")\|$(dirname "$item")" .gitignore 2>/dev/null; then
      warn "$item existe mas está no .gitignore — verificar se foi commitado"
    else
      fail "$item existe e NÃO está no .gitignore"
    fi
  fi
done

# =============================================================================
# 9. MICROSERVIÇO — prontidão REST → Java
# =============================================================================
section "Prontidão para microserviço ML (REST → Java)"

if grep -q "@app.post\|POST" api/main.py 2>/dev/null; then
  pass "Endpoint POST em api/main.py"
else
  fail "Nenhum endpoint POST encontrado em api/main.py"
fi

if grep -qi "cors\|CORSMiddleware" api/main.py 2>/dev/null; then
  pass "CORS configurado em api/main.py"
else
  fail "CORS ausente em api/main.py — Java não consegue chamar o FastAPI sem isso"
  echo -e "  ${DIM}→ adicionar em api/main.py:"
  echo -e "     from fastapi.middleware.cors import CORSMiddleware"
  echo -e "     app.add_middleware(CORSMiddleware, allow_origins=[\"*\"])${NC}"
fi

if [[ -f "Dockerfile" ]] || [[ -f "docker-compose.yml" ]] || [[ -f "docker-compose.yaml" ]]; then
  pass "Dockerfile/docker-compose encontrado — containerização pronta"
else
  fail "Sem Dockerfile/docker-compose — Java precisa de URL fixa para chamar o FastAPI"
  echo -e "  ${DIM}→ criar Dockerfile mínimo na raiz para a API FastAPI (porta 8000)${NC}"
fi

if grep -q "BaseModel\|ConfigDict" api/main.py 2>/dev/null; then
  pass "Pydantic BaseModel usado — contrato tipado e seguro"
else
  warn "Pydantic não detectado em api/main.py"
fi

if grep -qi "health\|ping\|/status" api/main.py 2>/dev/null; then
  pass "Health check endpoint detectado"
else
  warn "Sem endpoint /health — Java precisa checar se FastAPI está vivo antes de rotear"
fi

if [[ -f "mobile/.env.example" ]]; then
  pass "mobile/.env.example presente"
  if grep -q "EXPO_PUBLIC_ALERTS_BASE_URL" mobile/.env.example 2>/dev/null; then
    pass "EXPO_PUBLIC_ALERTS_BASE_URL documentada em .env.example"
  else
    fail "EXPO_PUBLIC_ALERTS_BASE_URL ausente em mobile/.env.example — URL do Java não documentada"
  fi
  if grep -q "EXPO_PUBLIC_ALERTS_API_MODE" mobile/.env.example 2>/dev/null; then
    pass "EXPO_PUBLIC_ALERTS_API_MODE documentada em .env.example"
  else
    fail "EXPO_PUBLIC_ALERTS_API_MODE ausente em mobile/.env.example"
  fi
else
  fail "mobile/.env.example ausente — nenhum membro novo do time sabe qual URL configurar"
  echo -e "  ${DIM}→ criar mobile/.env.example com:"
  echo -e "     EXPO_PUBLIC_ALERTS_API_MODE=api"
  echo -e "     EXPO_PUBLIC_ALERTS_BASE_URL=http://[java-host]:8080/api/v1${NC}"
fi

# =============================================================================
# 10. RESUMO
# =============================================================================
echo ""
echo -e "${BLU}════════════════════════════════════════${NC}"
echo -e "${BLU}  RESUMO DO AUDIT — Orbital Trust${NC}"
echo -e "${BLU}════════════════════════════════════════${NC}"
echo -e "  ${GRN}✔ Passou:   $PASS${NC}"
echo -e "  ${YEL}⚠ Avisos:   $WARN${NC}"
echo -e "  ${RED}✘ Falhou:   $FAIL${NC}"
echo ""

if [[ "$FAIL" -eq 0 && "$WARN" -le 3 ]]; then
  echo -e "  ${GRN}Repositório em boa forma para entrega.${NC}"
elif [[ "$FAIL" -eq 0 ]]; then
  echo -e "  ${YEL}Repositório aceitável — resolva os avisos antes da entrega.${NC}"
else
  echo -e "  ${RED}Há falhas críticas — corrija antes de entregar.${NC}"
fi

echo ""
echo -e "${DIM}Próximos passos sugeridos:"
echo -e "  1. Corrigir todos os itens ✘ acima"
echo -e "  2. Adicionar integrantes no README (nome completo + RM)"
echo -e "  3. Consolidar requirements em um único arquivo na raiz"
echo -e "  4. Adicionar CORS + /health em api/main.py para o microserviço Java"
echo -e "  5. Criar Dockerfile para containerizar a API ML${NC}"
echo ""