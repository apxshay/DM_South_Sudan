#!/usr/bin/env bash
# Bootstrap the project environment on macOS/Linux (venv).
# For Windows + Miniforge, use: .\scripts\setup.ps1
# For conda on any OS: conda env create -f environment.yml && conda activate dm-south-sudan
# Usage: ./scripts/setup.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/data_env"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "==> Checking prerequisites..."
command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
  echo "ERROR: python3 not found. Install Python 3.11+ or use Miniforge with environment.yml." >&2
  exit 1
}

PY_MAJOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info.major)')"
PY_MINOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info.minor)')"
if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 11 ]]; then
  echo "WARNING: Python $PY_MAJOR.$PY_MINOR detected. Python 3.11+ is recommended."
fi

if command -v conda >/dev/null 2>&1; then
  echo "NOTE: Miniforge/Conda detected. On Windows, prefer: .\\scripts\\setup.ps1"
  echo "      On any OS you may instead run: conda env create -f environment.yml"
fi

echo "==> Creating virtual environment at data_env/ ..."
if [[ ! -d "$VENV" ]]; then
  "$PYTHON_BIN" -m venv "$VENV"
else
  echo "    Virtual environment already exists, skipping creation."
fi

PYTHON="$VENV/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$VENV/Scripts/python.exe"
fi

echo "==> Installing Python dependencies..."
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r "$ROOT/requirements.txt"

echo "==> Creating data directories..."
"$PYTHON" "$ROOT/scripts/create_dirs.py"

echo ""
echo "Setup complete."
echo ""
echo "Next steps:"
echo "  1. ./scripts/download_datasets.sh"
echo "  2. $PYTHON scripts/explore_datasets.py"
echo "  3. $PYTHON scripts/visualize_data_validation.py"
