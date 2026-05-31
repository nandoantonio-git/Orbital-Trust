#!/usr/bin/env bash
set -euo pipefail

mkdir -p notebooks src/pipeline data/raw data/processed models reports tests

# Codex/Gemini auth dirs are bind-mounted from the host when available.
# If the host dir didn't exist, Docker creates the mount target owned by root — fix that.
for _dir in ~/.codex ~/.gemini; do
  if [ -d "$_dir" ] && [ "$(stat -c '%U' "$_dir")" = "root" ]; then
    sudo chown -R vscode:vscode "$_dir"
  fi
done
unset _dir

echo "Container criado."
echo "User: $(whoami)"
echo "PWD: $(pwd)"

command -v python && python --version || true
command -v python3 && python3 --version || true
command -v node && node --version || true
command -v npm && npm --version || true
command -v codex && codex --version || true
command -v claude && claude --version || true
command -v gemini && gemini --version || true
