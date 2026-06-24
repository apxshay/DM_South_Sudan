#!/usr/bin/env bash
# Bootstrap the project with Conda/Miniforge on macOS or Linux (recommended).
# Equivalent to scripts/setup.ps1 on Windows.
# Usage: ./scripts/setup_conda.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Checking conda ..."
if ! command -v conda >/dev/null 2>&1; then
  cat >&2 <<'EOF'
ERROR: conda not found.

Install Miniforge (recommended), then restart your shell:
  macOS (Apple Silicon): https://github.com/conda-forge/miniforge/releases
  macOS (Intel) / Linux: same release page — choose the matching installer

Then run:
  ./scripts/setup_conda.sh
EOF
  exit 1
fi

echo "==> Creating/updating conda environment 'dm-south-sudan' ..."
if conda env list | awk '{print $1}' | grep -qx "dm-south-sudan"; then
  conda env update -f "$ROOT/environment.yml" --prune
else
  conda env create -f "$ROOT/environment.yml"
fi

echo "==> Creating project directories ..."
conda run --no-capture-output -n dm-south-sudan python "$ROOT/scripts/create_dirs.py"

cat <<EOF

Setup complete.

Next steps:
  1. conda activate dm-south-sudan
  2. ./scripts/bootstrap.sh              # full pipeline from zero
     # or run individual scripts — see README.md

To resume on a machine that already has raw/processed data, use:
  ./scripts/bootstrap.sh --skip-download
EOF
