#!/usr/bin/env python3
"""Create required project directories."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from project_paths import ensure_project_dirs

if __name__ == "__main__":
    ensure_project_dirs()
    print("Project directories ready.")
