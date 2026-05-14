"""Backend package bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path


_backend_dir = Path(__file__).resolve().parent
_backend_path = str(_backend_dir)

if _backend_path not in sys.path:
	sys.path.insert(0, _backend_path)
