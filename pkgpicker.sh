#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# 1) venv
if [[ ! -d .venv ]]; then
  python -m venv .venv
fi
source .venv/bin/activate

# 2) python deps (Textual)
python -c "import textual" >/dev/null 2>&1 || pip install -U textual

# 3) optional system deps hint (no auto-install, but you can extend)
missing=()
command -v pacman >/dev/null || missing+=("pacman")
command -v sudo >/dev/null || missing+=("sudo")
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "Missing required tools: ${missing[*]}"
  exit 1
fi

exec python ./pkgpicker_app.py --data packages.json

