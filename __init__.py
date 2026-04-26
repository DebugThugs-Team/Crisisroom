"""Crisis Room package.

This repository contains multiple artifacts (FastAPI Space app + OpenEnv env).
Avoid importing optional client/model helpers at import time so that tooling
and test runners can import the package even when optional symbols drift.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["CrisisRoomEnv", "CrisisRoomAction", "CrisisRoomObservation"]

# Optional exports (best-effort). If they don't exist, keep package importable.
try:
    from .client import CrisisRoomEnv  # type: ignore
except Exception:  # pragma: no cover
    CrisisRoomEnv = None  # type: ignore

try:
    from .models import CrisisRoomAction, CrisisRoomObservation  # type: ignore
except Exception:  # pragma: no cover
    CrisisRoomAction = None  # type: ignore
    CrisisRoomObservation = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    CrisisRoomEnv: Any
    CrisisRoomAction: Any
    CrisisRoomObservation: Any
