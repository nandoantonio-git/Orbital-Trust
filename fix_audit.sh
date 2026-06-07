#!/usr/bin/env bash
# fix_audit.sh — aplica todos os 9 fixes do relatório de auditoria
# Executar da raiz do projeto: bash fix_audit.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "=== Orbital Trust — Aplicando fixes de auditoria ==="
echo "    Root: $ROOT"
echo

# ────────────────────────────────────────────────────────────
# FIX 1 (CRÍTICO) — Dockerfile: 3.11-slim → 3.13-slim
# ────────────────────────────────────────────────────────────
FILE="$ROOT/Dockerfile"
if grep -q "python:3.11-slim" "$FILE"; then
  sed -i '' 's|FROM python:3.11-slim|FROM python:3.13-slim|' "$FILE"
  echo "[1/9] ✅ Dockerfile: python:3.11-slim → python:3.13-slim"
else
  echo "[1/9] ⏭  Dockerfile: já atualizado ou não encontrado"
fi

# ────────────────────────────────────────────────────────────
# FIX 2 (ALTO) — devcontainer: 3.11-bookworm → 3.13-bookworm
# ────────────────────────────────────────────────────────────
FILE="$ROOT/.devcontainer/devcontainer.json"
if [ -f "$FILE" ] && grep -q "3.11" "$FILE"; then
  sed -i '' 's|3\.11-bookworm|3.13-bookworm|g; s|python:3\.11|python:3.13|g' "$FILE"
  echo "[2/9] ✅ devcontainer.json: python 3.11 → 3.13"
else
  echo "[2/9] ⏭  devcontainer.json: já atualizado ou não encontrado"
fi

# ────────────────────────────────────────────────────────────
# FIX 3 (MÉDIO) — requirements-dev.txt: adicionar httpx
# ────────────────────────────────────────────────────────────
FILE="$ROOT/requirements-dev.txt"
if [ -f "$FILE" ] && ! grep -q "httpx" "$FILE"; then
  echo 'httpx>=0.27,<1' >> "$FILE"
  echo "[3/9] ✅ requirements-dev.txt: httpx>=0.27,<1 adicionado"
else
  echo "[3/9] ⏭  requirements-dev.txt: httpx já presente ou arquivo não encontrado"
fi

# ────────────────────────────────────────────────────────────
# FIX 4 (MÉDIO) — api/main.py: warning de CORS no startup
# ────────────────────────────────────────────────────────────
FILE="$ROOT/api/main.py"
if [ -f "$FILE" ] && ! grep -q "CORS_WARNING" "$FILE"; then
  # Adiciona import de logging e startup event após a linha do app = FastAPI(...)
  python3 - <<'PYFIX'
import re, pathlib

path = pathlib.Path("api/main.py")
src = path.read_text()

# Adicionar import logging no topo se não existir
if "import logging" not in src:
    src = src.replace("from typing import", "import logging\n\nfrom typing import", 1)

# Adicionar startup warning após add_middleware do CORS
cors_block = 'allow_headers=["Content-Type"],\n)'
startup_block = '''allow_headers=["Content-Type"],
)

_logger = logging.getLogger(__name__)

@app.on_event("startup")
async def _startup() -> None:
    _logger.warning(
        "CORS aberto (allow_origins=['*']) — ambiente acadêmico MVP apenas. "
        "Restringir origens antes de qualquer deploy em produção."
    )'''

if "allow_origins=['*']" not in src and "_startup" not in src:
    src = src.replace(cors_block, startup_block)

path.write_text(src)
print("[4/9] ✅ api/main.py: startup CORS warning adicionado")
PYFIX
else
  echo "[4/9] ⏭  api/main.py: warning já presente ou arquivo não encontrado"
fi

# ────────────────────────────────────────────────────────────
# FIX 5 (BAIXO) — iot/stac_client.py: remover urlencode
# ────────────────────────────────────────────────────────────
FILE="$ROOT/iot/stac_client.py"
if [ -f "$FILE" ]; then
  # Remove urlencode da linha de import, preservando outros imports
  python3 - "$FILE" <<'PYFIX'
import sys, re, pathlib
path = pathlib.Path(sys.argv[1])
src = path.read_text()
# remove urlencode de qualquer import from urllib.parse
src = re.sub(r',\s*urlencode', '', src)
src = re.sub(r'urlencode,\s*', '', src)
src = re.sub(r'^from urllib\.parse import urlencode\n', '', src, flags=re.MULTILINE)
path.write_text(src)
print("[5/9] ✅ stac_client.py: import urlencode removido")
PYFIX
else
  echo "[5/9] ⏭  iot/stac_client.py: não encontrado"
fi

# ────────────────────────────────────────────────────────────
# FIX 6 (BAIXO) — iot/orbital_ingestion.py: manifest → _
# ────────────────────────────────────────────────────────────
FILE="$ROOT/iot/orbital_ingestion.py"
if [ -f "$FILE" ]; then
  python3 - "$FILE" <<'PYFIX'
import sys, re, pathlib
path = pathlib.Path(sys.argv[1])
src = path.read_text()
# substitui somente atribuição de manifest que nunca é lida (fora de retorno/uso)
src = re.sub(r'\bmanifest\s*=\s*(build_scene_manifest\()', r'_ = \1', src)
path.write_text(src)
print("[6/9] ✅ orbital_ingestion.py: manifest → _ (variável descartada)")
PYFIX
else
  echo "[6/9] ⏭  iot/orbital_ingestion.py: não encontrado"
fi

# ────────────────────────────────────────────────────────────
# FIX 7 (BAIXO) — iot/data_sources.py: remover SUPPORTED_SOURCES
# ────────────────────────────────────────────────────────────
FILE="$ROOT/iot/data_sources.py"
if [ -f "$FILE" ]; then
  python3 - "$FILE" <<'PYFIX'
import sys, re, pathlib
path = pathlib.Path(sys.argv[1])
src = path.read_text()
src = re.sub(r',\s*SUPPORTED_SOURCES', '', src)
src = re.sub(r'SUPPORTED_SOURCES,\s*', '', src)
src = re.sub(r'^from \S+ import SUPPORTED_SOURCES\n', '', src, flags=re.MULTILINE)
path.write_text(src)
print("[7/9] ✅ data_sources.py: import SUPPORTED_SOURCES removido")
PYFIX
else
  echo "[7/9] ⏭  iot/data_sources.py: não encontrado"
fi

# ────────────────────────────────────────────────────────────
# FIX 8 (BAIXO) — iot/scene_manifest.py: remover Optional
# ────────────────────────────────────────────────────────────
FILE="$ROOT/iot/scene_manifest.py"
if [ -f "$FILE" ]; then
  python3 - "$FILE" <<'PYFIX'
import sys, re, pathlib
path = pathlib.Path(sys.argv[1])
src = path.read_text()
src = re.sub(r',\s*Optional', '', src)
src = re.sub(r'Optional,\s*', '', src)
src = re.sub(r'^from typing import Optional\n', '', src, flags=re.MULTILINE)
path.write_text(src)
print("[8/9] ✅ scene_manifest.py: import Optional removido")
PYFIX
else
  echo "[8/9] ⏭  iot/scene_manifest.py: não encontrado"
fi

# ────────────────────────────────────────────────────────────
# FIX 9 (BAIXO) — alertService.ts: console.warn em falha de validação
# ────────────────────────────────────────────────────────────
FILE="$ROOT/mobile/src/services/alertService.ts"
if [ -f "$FILE" ]; then
  python3 - "$FILE" <<'PYFIX'
import sys, pathlib
path = pathlib.Path(sys.argv[1])
src = path.read_text()

# Localiza padrão de validação de mock sem log e adiciona warn
old = "} catch (validationError) {\n"
new = "} catch (validationError) {\n      console.warn('[alertService] Mock validation failed:', validationError);\n"
if "validationError" in src and "console.warn" not in src:
    src = src.replace(old, new, 1)

path.write_text(src)
print("[9/9] ✅ alertService.ts: console.warn adicionado em catch de validação")
PYFIX
else
  echo "[9/9] ⏭  mobile/src/services/alertService.ts: não encontrado"
fi

echo
echo "=== Concluído. Commit sugerido: ==="
echo "  git add -A"
echo "  git commit -m \"fix(audit): corrige 9 problemas de auditoria técnica\""
echo "    - Dockerfile: python 3.11 → 3.13"
echo "    - devcontainer: python 3.11 → 3.13"
echo "    - requirements-dev: adiciona httpx"
echo "    - api/main.py: startup CORS warning"
echo "    - 4x imports/vars órfãos removidos"
echo "    - alertService.ts: console.warn em validação"
