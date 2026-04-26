try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError("openenv is required. Install with: pip install openenv-core") from e

from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from uuid import uuid4
import json
from pathlib import Path

from models import IncidentAction, IncidentObservation
from server.crisis_room_environment import (
    CrisisRoomEnvironment,
    DIFFICULTY_CONFIG,
    _SESSION,
    pick_incident,
)

app = create_app(
    CrisisRoomEnvironment,
    IncidentAction,
    IncidentObservation,
    env_name="crisis_room",
    max_concurrent_envs=1,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_STATIC_DIR = _REPO_ROOT / "static"

if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def serve_ui():
        return FileResponse(str(_STATIC_DIR / "index.html"))


@app.post("/reset", include_in_schema=False)
async def reset_with_difficulty(request: Request):
    try:
        body = await request.json()
        difficulty = body.get("difficulty", None)
    except Exception:
        difficulty = None

    if difficulty not in ("easy", "medium", "hard"):
        difficulty = __import__("random").choice(["easy", "medium", "hard"])

    incident = pick_incident(difficulty)
    cfg = DIFFICULTY_CONFIG[difficulty]

    _SESSION.update({
        "episode_id": str(uuid4()),
        "step_count": 0,
        "max_steps": cfg["max_steps"],
        "incident": incident,
        "difficulty": difficulty,
        "actions_taken": [],
        "logs_checked": set(),
        "diagnostics_run": set(),
        "root_cause_confirmed": False,
        "services_restored": 0,
        "team_notified": False,
        "escalated": False,
        "resolved": False,
        "wrong_restarts": 0,
    })

    context = None
    if cfg["visible_logs"]:
        context = "Available logs: " + ", ".join(incident["logs"].keys())

    obs = IncidentObservation(
        step=0,
        max_steps=cfg["max_steps"],
        message=f"[{difficulty.upper()}] INCIDENT: {incident['title']}\n{context or 'Run check_logs or run_diagnostic to investigate.'}",
        difficulty=difficulty,
        episode_id=_SESSION["episode_id"],
        active_alerts=incident["initial_alerts"],
        service_status=incident["initial_status"],
        log_output=None,
        actions_taken=[],
        root_cause_found=False,
        services_restored=0,
        total_services_affected=len(incident["affected_services"]),
        partial_score=0.0,
        steps_remaining=cfg["max_steps"],
        done=False,
        reward=0.0,
    )
    return JSONResponse(content={"observation": obs.model_dump(), "reward": 0.0, "done": False})


@app.get("/tasks", include_in_schema=False)
async def list_tasks():
    return JSONResponse(content={
        "tasks": [
            {"name": "easy-incident", "difficulty": "easy", "max_steps": 8, "description": "Single service down, root cause visible in logs"},
            {"name": "medium-incident", "difficulty": "medium", "max_steps": 10, "description": "Cascading failure across multiple services"},
            {"name": "hard-incident", "difficulty": "hard", "max_steps": 12, "description": "Silent corruption or intermittent failure — no obvious alerts"},
        ]
    })


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()