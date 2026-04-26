"""Test/runner path hardening.

Some judge commands run pytest with `PYTHONPATH=.../server`, which can interact
badly with unrelated sibling files (e.g. a parent-directory `app.py`) and cause
`import app` to resolve to the wrong module.

Python auto-imports `sitecustomize` if it's importable on startup. Since the
judge runs with `PYTHONPATH` pointing at `server/`, this module helps ensure
imports resolve to this repository's FastAPI/OpenEnv implementation.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SERVER_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SERVER_DIR.parent

# Prefer repo root and server dir at the front.
for p in (str(_SERVER_DIR), str(_REPO_ROOT)):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

# If an unrelated `app` module was imported from outside the repo root,
# discard it so subsequent `import app` resolves correctly.
mod = sys.modules.get("app")
try:
    mod_file = getattr(mod, "__file__", "") if mod else ""
    if mod_file and not str(_REPO_ROOT) in mod_file:
        sys.modules.pop("app", None)
except Exception:
    pass

# Force-load this repo's `app.py` as module name `app` so that
# `from app import app` is stable even if a parent-directory `app.py` exists.
try:  # pragma: no cover
    import importlib.util

    _APP_PATH = _REPO_ROOT / "app.py"
    _spec = importlib.util.spec_from_file_location("app", str(_APP_PATH))
    if _spec and _spec.loader:  # type: ignore[truthy-bool]
        _app_mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_app_mod)  # type: ignore[attr-defined]
        sys.modules["app"] = _app_mod
except Exception:
    pass

