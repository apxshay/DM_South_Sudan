#!/usr/bin/env bash
# Bootstrap the project with a local venv on macOS/Linux.
# For geospatial + road topology (osmium-tool), prefer Conda instead:
#   ./scripts/setup_conda.sh
# Usage: ./scripts/setup.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/data_env"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "==> Checking prerequisites..."
command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
  echo "ERROR: python3 not found. Install Python 3.11+ or use ./scripts/setup_conda.sh." >&2
  exit 1
}

PY_MAJOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info.major)')"
PY_MINOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info.minor)')"
if [[ "$PY_MAJOR" -lt 3 ]] || [[ "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 11 ]]; then
  echo "WARNING: Python $PY_MAJOR.$PY_MINOR detected. Python 3.11+ is recommended."
fi

if command -v conda >/dev/null 2>&1; then
  cat <<EOF
NOTE: Miniforge/Conda detected.
      For full pipeline support (GeoPandas/GDAL + osmium-tool), prefer:
        ./scripts/setup_conda.sh
EOF
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

cat <<EOF

Setup complete (venv).

WARNING: pip-only installs may not include osmium-tool, required by
         scripts/build_road_network_topology.py. If road topology fails,
         use ./scripts/setup_conda.sh instead.

Next steps:
  1. ./scripts/bootstrap.sh
     # or ./scripts/download_datasets.sh and run scripts individually
EOF
