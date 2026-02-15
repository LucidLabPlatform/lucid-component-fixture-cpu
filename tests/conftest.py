"""Pytest configuration: ensure the package under test is importable."""
from __future__ import annotations

import sys
from pathlib import Path

# Project root (parent of tests/)
_root = Path(__file__).resolve().parent.parent
# This package's src so "lucid_component_fixture_cpu" can be imported
_src = _root / "src"
# Prefer local lucid-component-base when present (e.g. in LUCID monorepo)
_base_src = _root.parent / "lucid-component-base" / "src"

for path in (_base_src, _src):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))
