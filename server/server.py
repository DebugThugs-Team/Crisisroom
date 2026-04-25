from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal

from .environment import CrisisRoomEnvironment
from .models import Action, Observation


app = FastAPI()

_ENV: CrisisRoomEnvironment | None = None


class ResetRequest(BaseModel):
    difficulty: str | None = None
    scenario_id: str | None = None


class StepRequest(BaseModel):
    action_type: Literal[
        "triage",
        "delegate",
        "synthesise",
        "communicate",
        "command",
        "declare_resolved",
    ]
    payload: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset(req: ResetRequest):
    global _ENV
    _ENV = CrisisRoomEnvironment()
    obs = _ENV.reset(scenario_id=req.scenario_id, difficulty=req.difficulty)
    return obs.model_dump()


@app.post("/step")
def step(req: StepRequest):
    global _ENV
    if _ENV is None or _ENV.state is None:
        raise HTTPException(status_code=400, detail="Must call /reset before /step")
    action = Action(action_type=req.action_type, payload=req.payload)
    obs, reward, done = _ENV.step(action)
    return {"observation": obs.model_dump(), "reward": float(reward), "done": bool(done)}


@app.get("/state")
def get_state():
    global _ENV
    if _ENV is None or _ENV.state is None:
        raise HTTPException(status_code=400, detail="No active episode; call /reset first")
    return _ENV.state.model_dump()

