from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Action(BaseModel):
    action_type: Literal[
        "triage",
        "delegate",
        "synthesise",
        "communicate",
        "command",
        "declare_resolved",
    ]
    payload: str


class Observation(BaseModel):
    incident_alert: str = ""
    available_specialists: List[str] = Field(default_factory=list)
    stakeholder_history: Dict[str, Any] = Field(default_factory=dict)
    step_count: int = 0
    max_steps: int = 20
    last_response: str = ""
    history: List[Dict[str, Any]] = Field(default_factory=list)
    done: bool = False


class State(BaseModel):
    scenario_id: str
    ground_truth_root_cause: str
    ground_truth_fix_command: str
    correct_specialist_mappings: Dict[str, str] = Field(default_factory=dict)
    extracted_findings: List[str] = Field(default_factory=list)
    hypothesis: str = ""
    stakeholder_updates: Dict[str, int] = Field(default_factory=dict)
    step_count: int = 0
    done: bool = False

    # Tracking for scoring
    issued_commands: List[str] = Field(default_factory=list)
    delegations: List[Dict[str, Any]] = Field(default_factory=list)  # {specialist, correct, payload}
    wrong_escalations: int = 0
    declared_resolved_text: str = ""


# Compatibility exports for the FastAPI/OpenEnv environment implementation.
# Some tooling/test setups put `server/` first on `PYTHONPATH`, which makes
# `import models` resolve to `server/models.py`. Provide the expected symbols
# (`IncidentAction`, `IncidentObservation`) by loading the repo-root `models.py`.
try:  # pragma: no cover
    from pathlib import Path
    import importlib.util

    _ROOT_MODELS_PATH = Path(__file__).resolve().parents[1] / "models.py"
    _spec = importlib.util.spec_from_file_location("_crisis_room_root_models", str(_ROOT_MODELS_PATH))
    if _spec and _spec.loader:  # type: ignore[truthy-bool]
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)  # type: ignore[attr-defined]
        IncidentAction = _mod.IncidentAction  # type: ignore[attr-defined]
        IncidentObservation = _mod.IncidentObservation  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    pass
