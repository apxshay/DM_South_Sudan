#!/usr/bin/env bash
# Bootstrap the project environment on a new machine.
# Usage: ./scripts/setup.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/data_env"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "==> Checking prerequisites..."
command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
  echo "ERROR: python3 not found. Install Python 3.11+ and retry." >&2
  exit 1
}

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info.major)')"
PY_MINOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info.minor)')"
if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 11 ]]; then
  echo "WARNING: Python $PY_VERSION detected. Python 3.11+ is recommended."
fi

for cmd in curl unzip; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "WARNING: '$cmd' not found. Required by scripts/download_datasets.sh."
  }
done

echo "==> Creating virtual environment at data_env/ ..."
if [[ ! -d "$VENV" ]]; then
  "$PYTHON_BIN" -m venv "$VENV"
else
  echo "    Virtual environment already exists, skipping creation."
fi

echo "==> Installing Python dependencies..."
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt"

echo "==> Creating data directories..."
mkdir -p "$ROOT/data/raw/roads/original"
mkdir -p "$ROOT/data/raw/roads_hotosm/original" "$ROOT/data/raw/roads_hotosm/filtered"
mkdir -p "$ROOT/data/raw/health_facilities/original"
mkdir -p "$ROOT/data/raw/idp/original"
mkdir -p "$ROOT/data/raw/displacement_sites/original"
mkdir -p "$ROOT/data/processed" "$ROOT/data/interim"
mkdir -p "$ROOT/output"

echo ""
echo "Setup complete."
echo ""
echo "Next steps:"
echo "  1. ./scripts/download_datasets.sh          # download HDX datasets"
echo "  2. data_env/bin/python scripts/explore_datasets.py"
echo "  3. data_env/bin/python scripts/visualize_data_validation.py"
