from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import requests
from pydantic import ValidationError


ROOT = os.path.abspath(os.path.dirname(__file__))


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""


def check(name: str, cond: bool, detail: str = "") -> TestResult:
    return TestResult(name=name, passed=bool(cond), detail=detail)


def run_models_checks() -> Tuple[List[TestResult], Dict[str, Any]]:
    from server.models import Action, Observation, State
    from pydantic import BaseModel
    from typing import get_args, get_origin, Literal

    results: List[TestResult] = []

    # ACTION MODEL
    results.append(check("Action class exists and inherits from BaseModel", issubclass(Action, BaseModel)))

    lit = Action.model_fields["action_type"].annotation
    ok_literal = get_origin(lit) is Literal and set(get_args(lit)) == {
        "triage",
        "delegate",
        "synthesise",
        "communicate",
        "command",
        "declare_resolved",
    }
    results.append(check("action_type is Literal with exact values", ok_literal, detail=str(lit)))

    results.append(check("payload field exists and is type str", Action.model_fields["payload"].annotation is str))

    try:
        Action(action_type="invalid", payload="test")  # type: ignore
        results.append(check("invalid action_type raises ValidationError", False))
    except ValidationError:
        results.append(check("invalid action_type raises ValidationError", True))

    try:
        a = Action(action_type="triage", payload="test")
        results.append(check("valid Action creation succeeds", a.action_type == "triage" and a.payload == "test"))
    except Exception as e:
        results.append(check("valid Action creation succeeds", False, detail=str(e)))

    # OBSERVATION MODEL
    results.append(check("Observation exists and inherits from BaseModel", issubclass(Observation, BaseModel)))
    required = [
        "incident_alert",
        "available_specialists",
        "stakeholder_history",
        "step_count",
        "max_steps",
        "last_response",
        "history",
        "done",
    ]
    results.append(check("Observation contains required fields", all(f in Observation.model_fields for f in required)))
    results.append(check("done defaults to False", Observation().done is False))
    results.append(check("step_count starts at 0", Observation().step_count == 0))

    # STATE MODEL
    results.append(check("State exists and inherits from BaseModel", issubclass(State, BaseModel)))
    state_required = [
        "scenario_id",
        "ground_truth_root_cause",
        "ground_truth_fix_command",
        "correct_specialist_mappings",
        "extracted_findings",
        "hypothesis",
        "stakeholder_updates",
        "step_count",
        "done",
    ]
    results.append(check("State contains required fields", all(f in State.model_fields for f in state_required)))
    results.append(
        check(
            "State contains hidden ground_truth fields not in Observation",
            "ground_truth_root_cause" not in Observation.model_fields and "ground_truth_fix_command" not in Observation.model_fields,
        )
    )

    meta = {"Action": Action, "Observation": Observation, "State": State}
    return results, meta


def run_scenarios_checks() -> Tuple[List[TestResult], int, List[str]]:
    path = os.path.join(ROOT, "scenarios", "scenarios.json")
    scenarios = json.loads(_read(path))
    missing_lines: List[str] = []

    req_fields = [
        "id",
        "difficulty",
        "incident_alert",
        "specialist_responses",
        "ground_truth_root_cause",
        "ground_truth_fix_command",
        "correct_specialist",
        "irrelevant_specialists",
        "stakeholder_update_frequency",
        "postmortem_keywords",
        "red_herrings",
    ]
    incident_req = [
        "title",
        "error_rate",
        "latency_ms",
        "traffic_drop_pct",
        "affected_services",
        "last_deployment",
    ]

    results: List[TestResult] = []
    ids = [s.get("id") for s in scenarios]
    results.append(check("id is unique string", len(ids) == len(set(ids)) and all(isinstance(x, str) for x in ids)))

    for s in scenarios:
        sid = s.get("id", "<missing-id>")
        for f in req_fields:
            if f not in s:
                missing_lines.append(f"MISSING: scenario {sid} is missing field {f}")
        if isinstance(s.get("incident_alert"), dict):
            for f in incident_req:
                if f not in s["incident_alert"]:
                    missing_lines.append(f"MISSING: scenario {sid} is missing field incident_alert.{f}")

        # specialist_responses keys
        sr = s.get("specialist_responses", {})
        if isinstance(sr, dict):
            for k in ("database", "network", "security", "oncall"):
                if k not in sr:
                    missing_lines.append(f"MISSING: scenario {sid} is missing field specialist_responses.{k}")

    # Coverage
    difficulties = {s.get("difficulty") for s in scenarios}
    results.append(check("At least 1 easy scenario", "easy" in difficulties))
    results.append(check("At least 1 medium scenario", "medium" in difficulties))
    results.append(check("At least 1 hard scenario", "hard" in difficulties))
    results.append(check("At least 1 DB incident", any(s.get("correct_specialist") == "database" for s in scenarios)))
    results.append(check("At least 1 network incident", any(s.get("correct_specialist") == "network" for s in scenarios)))
    results.append(
        check(
            "At least 1 cascading failure (multiple affected_services)",
            any(isinstance(s.get("incident_alert", {}).get("affected_services"), list) and len(s["incident_alert"]["affected_services"]) > 1 for s in scenarios),
        )
    )
    results.append(check("At least 5 scenarios total", len(scenarios) >= 5, detail=f"count={len(scenarios)}"))

    return results, len(scenarios), missing_lines


def run_environment_tests(meta: Dict[str, Any]) -> Tuple[List[TestResult], float, float, float, int]:
    from server.environment import CrisisRoomEnvironment
    from server.models import Action, Observation

    results: List[TestResult] = []

    # TEST 4I: step before reset raises RuntimeError
    env_fresh = CrisisRoomEnvironment()
    try:
        env_fresh.step(Action(action_type="triage", payload="test"))
        results.append(check("STEP BEFORE RESET raises RuntimeError", False))
    except RuntimeError:
        results.append(check("STEP BEFORE RESET raises RuntimeError", True))

    # Force-load easy scenario
    env = CrisisRoomEnvironment()
    obs = env.reset(difficulty="easy")

    # TEST 4A — RESET expectations
    results.append(check("reset returns Observation instance", isinstance(obs, Observation)))
    results.append(check("obs.done == False", obs.done is False))
    results.append(check("obs.step_count == 0", obs.step_count == 0))
    results.append(check("obs.max_steps == 20", obs.max_steps == 20))
    results.append(check("obs.incident_alert not empty", isinstance(obs.incident_alert, str) and len(obs.incident_alert) > 0))
    results.append(
        check(
            "obs.available_specialists contains at least db/network/security",
            all(x in obs.available_specialists for x in ["database", "network", "security"]),
        )
    )
    results.append(check("obs.history == []", obs.history == []))
    # hidden ground truth fields
    d = obs.model_dump()
    results.append(check("ground_truth_root_cause NOT present in obs", "ground_truth_root_cause" not in d))

    # TEST 4B — TRIAGE ACTION
    obs2, reward, done = env.step(
        Action(
            action_type="triage",
            payload="SEV1. Payment service down. 43% error rate. Recent deployment suspicious.",
        )
    )
    results.append(check("triage reward == 0.0", reward == 0.0))
    results.append(check("triage done == False", done is False))
    results.append(check("triage increments step_count to 1", obs2.step_count == 1))
    results.append(check("history has 1 entry", len(obs2.history) == 1))
    results.append(check("history[0]['action']=='triage'", obs2.history[0].get("action") == "triage"))

    # TEST 4C — DELEGATE TO CORRECT SPECIALIST
    obs3, reward3, done3 = env.step(
        Action(action_type="delegate", payload="database: check query volume and index health on payment-db")
    )
    results.append(check("delegate reward == 0.0", reward3 == 0.0))
    results.append(check("delegate done == False", done3 is False))
    results.append(check("last_response contains scripted answer", isinstance(obs3.last_response, str) and len(obs3.last_response) > 0))
    results.append(check("step_count == 2", obs3.step_count == 2))
    results.append(check("state tracks CORRECT delegation", any(d.get("correct") is True for d in env.state.delegations)))  # type: ignore

    # TEST 4D — DELEGATE TO WRONG SPECIALIST (same easy)
    env_w = CrisisRoomEnvironment()
    env_w.reset(scenario_id=env.state.scenario_id)  # type: ignore
    _o1, _r1, _d1 = env_w.step(Action(action_type="triage", payload="SEV1 initial assessment"))
    obs_wrong2, r_wrong2, done_wrong2 = env_w.step(
        Action(action_type="delegate", payload="security: check for DDoS or anomalous traffic patterns")
    )
    results.append(check("wrong delegate mid-episode reward==0.0", r_wrong2 == 0.0))
    results.append(check("state tracks WRONG delegation", any(d.get("correct") is False for d in env_w.state.delegations)))  # type: ignore
    results.append(check("wrong delegate response contains security response", isinstance(obs_wrong2.last_response, str) and len(obs_wrong2.last_response) > 0))

    # TEST 4E — COMMUNICATE ACTION
    obs_c, r_c, done_c = env.step(
        Action(action_type="communicate", payload="CEO: Payment service degraded due to suspected DB issue. ETA 15 mins.")
    )
    results.append(check("communicate reward == 0.0", r_c == 0.0))
    results.append(check("communicate done == False", done_c is False))
    results.append(check("stakeholder_updates[CEO] set to current step", env.state.stakeholder_updates.get("CEO") == obs_c.step_count))  # type: ignore
    results.append(check("last_response confirms communication logged", "logged" in (obs_c.last_response or "").lower()))

    # TEST 4F — TERMINAL CORRECT FIX (HIGH REWARD)
    env_hi = CrisisRoomEnvironment()
    env_hi.reset(difficulty="easy")
    env_hi.step(Action(action_type="triage", payload="SEV1. Payment-api down. 43% error rate."))
    env_hi.step(Action(action_type="delegate", payload="database: check query volume and index health"))
    env_hi.step(Action(action_type="synthesise", payload="Root cause: DB index dropped in recent deployment. Full table scans."))
    env_hi.step(Action(action_type="communicate", payload="CEO: investigating DB index issue from deployment"))
    env_hi.step(Action(action_type="command", payload="rollback payment-api"))
    obs_f, reward_f, done_f = env_hi.step(
        Action(
            action_type="declare_resolved",
            payload="Root cause was dropped transaction_id index from commit a4f2b1. Impact: 23 mins, 40k users. Fix: rollback. Action items: (1) add index verification to CI/CD (2) require DBA approval for schema migrations.",
        )
    )
    best = float(reward_f)
    results.append(check("done True after declare_resolved", done_f is True and obs_f.done is True))
    results.append(check("reward > 0.50", best > 0.50, detail=f"reward={best}"))
    results.append(check("reward <= 1.0", best <= 1.0))
    results.append(check("reward is float", isinstance(best, float)))
    results.append(check("env.state.done == True", env_hi.state.done is True))  # type: ignore

    # TEST 4G — TERMINAL WRONG FIX (LOW REWARD)
    env_lo = CrisisRoomEnvironment()
    env_lo.reset(scenario_id=env_hi.state.scenario_id)  # type: ignore
    env_lo.step(Action(action_type="triage", payload="SEV1 initial assessment"))
    _obs_g, reward_g, done_g = env_lo.step(Action(action_type="declare_resolved", payload="The issue was a DDoS attack. We blocked the IPs. Fixed."))
    worst = float(reward_g)
    results.append(check("wrong-fix done == True", done_g is True))
    results.append(check("wrong-fix reward < 0.20", worst < 0.20, detail=f"reward={worst}"))
    results.append(check("wrong-fix reward >= 0.0", worst >= 0.0))
    results.append(check("wrong-fix reward != high reward", worst != best))
    diff = best - worst
    # warning handled by caller

    # TEST 4H — MAX STEPS TERMINATION
    env_ms = CrisisRoomEnvironment()
    env_ms.reset(difficulty="easy")
    done_at = None
    final_reward = None
    for i in range(20):
        obs_i, r_i, d_i = env_ms.step(Action(action_type="triage", payload=f"step {i}"))
        if d_i:
            done_at = obs_i.step_count
            final_reward = float(r_i)
            break
    results.append(check("terminates at or before step 20", done_at is not None and done_at <= 20, detail=f"done_at={done_at}"))
    results.append(check("done == True when terminated", done_at is not None))
    results.append(check("reward between 0.0 and 1.0", final_reward is not None and 0.0 <= final_reward <= 1.0, detail=f"reward={final_reward}"))
    results.append(check("reward low (<0.25)", final_reward is not None and final_reward < 0.25, detail=f"reward={final_reward}"))

    return results, best, worst, diff, int(done_at or -1)


def run_reward_tests() -> List[TestResult]:
    from server.environment import compute_reward_components
    from server.models import State

    scenario = json.loads(_read(os.path.join(ROOT, "scenarios", "scenarios.json")))[0]
    results: List[TestResult] = []

    # Component 1 — Resolution
    st_ok = State(
        scenario_id=scenario["id"],
        ground_truth_root_cause=scenario["ground_truth_root_cause"],
        ground_truth_fix_command="rollback payment-api",
        correct_specialist_mappings={},
        extracted_findings=[],
        hypothesis="",
        stakeholder_updates={},
        step_count=6,
        done=True,
        issued_commands=["rollback payment-api"],
        delegations=[],
        wrong_escalations=0,
        declared_resolved_text="root cause impact timeline action items rollback index",
    )
    c_ok = compute_reward_components(st_ok, scenario)
    results.append(check("resolution_score == 0.35 when correct command", abs(c_ok["resolution_score"] - 0.35) < 1e-9, detail=f"got={c_ok['resolution_score']}"))

    st_bad = st_ok.model_copy(deep=True)
    st_bad.issued_commands = ["restart auth-service"]
    c_bad = compute_reward_components(st_bad, scenario)
    results.append(check("resolution_score == 0.0 when wrong command", abs(c_bad["resolution_score"] - 0.0) < 1e-9, detail=f"got={c_bad['resolution_score']}"))

    # Component 2 — Time efficiency exacts
    for step, exp in [(6, 0.20), (15, 0.13), (20, 0.08)]:
        st = st_ok.model_copy(deep=True)
        st.step_count = step
        st.issued_commands = []
        st.declared_resolved_text = ""
        st.stakeholder_updates = {}
        st.delegations = []
        st.wrong_escalations = 0
        st.done = False
        got = float(compute_reward_components(st, scenario)["time_score"])
        results.append(check(f"time_score expected {exp:.2f} at step_count={step}", abs(got - exp) < 1e-9, detail=f"got={got}"))

    # Component 3 — Communication
    st_c = st_ok.model_copy(deep=True)
    st_c.done = False
    st_c.step_count = 10
    st_c.issued_commands = []
    st_c.declared_resolved_text = ""
    st_c.delegations = []
    st_c.stakeholder_updates = {"CEO": 8}
    got_c = float(compute_reward_components(st_c, scenario)["communication_score"])
    results.append(check("communication_score close to 0.20 with timely CEO updates", got_c >= 0.19, detail=f"got={got_c}"))

    st_nc = st_c.model_copy(deep=True)
    st_nc.stakeholder_updates = {}
    got_nc = float(compute_reward_components(st_nc, scenario)["communication_score"])
    results.append(check("communication_score near 0.0 when never updated", got_nc <= 0.01, detail=f"got={got_nc}"))

    # Component 4 — Delegation accuracy
    st_d = st_ok.model_copy(deep=True)
    st_d.done = False
    st_d.step_count = 10
    st_d.issued_commands = []
    st_d.declared_resolved_text = ""
    st_d.stakeholder_updates = {}
    st_d.delegations = [{"specialist": "database", "correct": True, "payload": "database: ..."}]
    got_d = float(compute_reward_components(st_d, scenario)["delegation_score"])
    results.append(check("delegation_score == 0.15 when correct delegation", abs(got_d - 0.15) < 1e-9, detail=f"got={got_d}"))

    st_dw = st_d.model_copy(deep=True)
    st_dw.delegations = [{"specialist": "security", "correct": False, "payload": "security: ..."}]
    got_dw = float(compute_reward_components(st_dw, scenario)["delegation_score"])
    results.append(check("delegation_score < 0.10 when wrong delegation", got_dw < 0.10, detail=f"got={got_dw}"))

    # Component 5 — Postmortem quality
    rich = (
        "Root cause: transaction_id index dropped in schema migration during commit a4f2b1. "
        "Impact: 23 minutes, 40,000 users affected. Timeline: 02:47 alert, 02:51 identified, "
        "03:10 rollback complete. Action items: (1) add index verification to CI/CD pipeline "
        "(2) require DBA approval for schema migrations (3) add automated index health check."
    )
    poor = "Fixed it."
    st_pm = st_ok.model_copy(deep=True)
    st_pm.done = False
    st_pm.step_count = 10
    st_pm.issued_commands = []
    st_pm.stakeholder_updates = {}
    st_pm.delegations = []
    st_pm.declared_resolved_text = rich
    got_rich = float(compute_reward_components(st_pm, scenario)["postmortem_score"])
    results.append(check("postmortem_score > 0.07 for rich postmortem", got_rich > 0.07, detail=f"got={got_rich}"))

    st_pm.declared_resolved_text = poor
    got_poor = float(compute_reward_components(st_pm, scenario)["postmortem_score"])
    results.append(check("postmortem_score < 0.03 for poor postmortem", got_poor < 0.03, detail=f"got={got_poor}"))

    # Penalty checks
    st_pen = st_ok.model_copy(deep=True)
    st_pen.done = True
    st_pen.step_count = 10
    st_pen.issued_commands = ["restart auth-service"]  # wrong
    st_pen.wrong_escalations = 2
    st_pen.declared_resolved_text = ""
    got_pen = float(compute_reward_components(st_pen, scenario)["penalty"])
    results.append(check("2 wrong escalations penalty >= 0.10", got_pen >= 0.10, detail=f"got={got_pen}"))

    # Clamp checks
    from server.environment import _clamp01 as clamp  # type: ignore

    results.append(check("clamp caps >1.0 to 1.0", clamp(1.7) == 1.0))
    results.append(check("clamp caps <0.0 to 0.0", clamp(-0.2) == 0.0))

    return results


def run_server_tests() -> List[TestResult]:
    results: List[TestResult] = []
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "server.server:app", "--port", "8765"], cwd=ROOT)
    try:
        time.sleep(3)

        # GET /health
        r = requests.get("http://localhost:8765/health", timeout=10)
        results.append(check("GET /health status 200", r.status_code == 200))
        ok = False
        try:
            ok = r.json().get("status") == "ok"
        except Exception:
            ok = False
        results.append(check("GET /health body contains status ok", ok))

        # POST /reset
        r = requests.post("http://localhost:8765/reset", json={}, timeout=10)
        results.append(check("POST /reset status 200", r.status_code == 200))
        data = r.json()
        for k in ("incident_alert", "available_specialists", "step_count", "done"):
            results.append(check(f"/reset response has key {k}", k in data))
        results.append(check("step_count == 0", data.get("step_count") == 0))
        results.append(check("done == False", data.get("done") is False))

        # POST /step valid
        r = requests.post("http://localhost:8765/step", json={"action_type": "triage", "payload": "SEV1 assessment"}, timeout=10)
        results.append(check("POST /step valid status 200", r.status_code == 200))
        data = r.json()
        results.append(check("/step has keys observation,reward,done", all(k in data for k in ("observation", "reward", "done"))))
        reward = data.get("reward")
        results.append(check("reward is float in [0,1]", isinstance(reward, float) and 0.0 <= reward <= 1.0))
        results.append(check("observation.step_count == 1", data.get("observation", {}).get("step_count") == 1))

        # POST /step invalid action_type
        r = requests.post("http://localhost:8765/step", json={"action_type": "fly_to_moon", "payload": "test"}, timeout=10)
        results.append(check("invalid action_type returns 422", r.status_code == 422))

        # POST /step before /reset on fresh server
        # Launch a second proc on 8766
        proc2 = subprocess.Popen([sys.executable, "-m", "uvicorn", "server.server:app", "--port", "8766"], cwd=ROOT)
        try:
            time.sleep(2)
            r = requests.post("http://localhost:8766/step", json={"action_type": "triage", "payload": "test"}, timeout=10)
            results.append(check("/step before /reset returns 400", r.status_code == 400))
        finally:
            proc2.terminate()

        # GET /state
        r = requests.get("http://localhost:8765/state", timeout=10)
        results.append(check("GET /state status 200", r.status_code == 200))
        data = r.json()
        results.append(check("/state contains ground_truth fields", "ground_truth_root_cause" in data and "ground_truth_fix_command" in data))

    finally:
        proc.terminate()
    return results


def run_dockerfile_checks() -> List[TestResult]:
    results: List[TestResult] = []
    path = os.path.join(ROOT, "Dockerfile")
    txt = _read(path)
    results.append(check("Starts with FROM python:3.11-slim", txt.splitlines()[0].strip() == "FROM python:3.11-slim"))
    results.append(check("Has WORKDIR /app", "WORKDIR /app" in txt))
    results.append(check("Has COPY requirements.txt . before RUN pip install", "COPY requirements.txt ." in txt and txt.index("COPY requirements.txt .") < txt.index("RUN pip install")))
    results.append(check("Has RUN pip install --no-cache-dir -r requirements.txt", "pip install --no-cache-dir -r requirements.txt" in txt))
    results.append(check("Copies scenarios/ folder", "COPY scenarios/" in txt))
    results.append(check("Copies server/ folder", "COPY server/" in txt))
    results.append(check("Has EXPOSE 8000", "EXPOSE 8000" in txt))
    results.append(check("CMD starts uvicorn host 0.0.0.0 port 8000", "uvicorn" in txt and "--host" in txt and "0.0.0.0" in txt and "--port" in txt and "8000" in txt))
    results.append(check("Dockerfile is at project root", os.path.exists(path)))
    return results


def run_inference_script_checks() -> List[TestResult]:
    results: List[TestResult] = []
    path = os.path.join(ROOT, "inference_script.py")
    txt = _read(path)

    results.append(check("Uses HF_TOKEN env var", "HF_TOKEN" in txt and "os.environ.get(\"HF_TOKEN\")" in txt))
    results.append(check("No string containing sk- anywhere", "sk-" not in txt))

    results.append(check("MODEL_ID contains '/'", "MODEL_ID" in txt and "/" in os.environ.get("MODEL_ID", "meta-llama/Llama-3.1-8B-Instruct")))
    results.append(check("ENVIRONMENT_URL configurable via env var", "ENVIRONMENT_URL" in txt and "os.environ.get(\"ENVIRONMENT_URL\")" in txt))
    results.append(check("API call uses HF inference router", "router.huggingface.co" in txt and "api.openai.com" not in txt))

    results.append(check("Calls /reset before each episode", "/reset" in txt))
    results.append(check("Calls /step in a loop until done", "while not done" in txt and "/step" in txt))
    results.append(check("Parses reward from step response", "float(result[\"reward\"])" in txt or "float(result.get(\"reward\"" in txt))
    results.append(check("Handles done == True correctly", "done = bool(result[\"done\"])" in txt and "while not done" in txt))
    results.append(check("Runs at least 3 episodes", "NUM_EPISODES" in txt and "3" in txt))

    results.append(check("Prints reward after each episode", "Episode" in txt and "reward" in txt))
    results.append(check("Prints average reward at end", "Average reward" in txt))
    results.append(check("Has a main() function", "def main()" in txt))
    return results


def run_openenv_compliance_checks() -> List[TestResult]:
    from server.environment import CrisisRoomEnvironment
    from server.models import Action, Observation
    from typing import get_args, get_origin, Literal

    results: List[TestResult] = []
    env = CrisisRoomEnvironment()
    obs = env.reset(difficulty="easy")
    out = env.step(Action(action_type="triage", payload="x"))

    results.append(check("step() returns exactly 3 values", isinstance(out, tuple) and len(out) == 3))
    results.append(check("reset() returns exactly 1 value", isinstance(obs, Observation)))
    results.append(check("reward always float", isinstance(out[1], float)))
    results.append(check("reward between 0.0 and 1.0", 0.0 <= out[1] <= 1.0))
    results.append(check("Observation has done: bool", isinstance(obs.done, bool)))

    lit = Action.model_fields["action_type"].annotation
    results.append(check("Action model uses Literal for action_type", get_origin(lit) is Literal))

    # server endpoints existence is checked in server tests; here just check files exist
    results.append(check("requirements.txt exists at project root", os.path.exists(os.path.join(ROOT, "requirements.txt"))))
    results.append(check("Dockerfile exists at project root", os.path.exists(os.path.join(ROOT, "Dockerfile"))))
    return results


def _print_section(title: str, results: List[TestResult]) -> None:
    print(f"\n{title}")
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if r.detail:
            print(f"- {status}: {r.name} ({r.detail})")
        else:
            print(f"- {status}: {r.name}")


def main() -> int:
    all_results: List[Tuple[str, List[TestResult]]] = []

    model_results, meta = run_models_checks()
    all_results.append(("MODELS", model_results))

    scenario_results, scenario_count, missing_lines = run_scenarios_checks()
    all_results.append(("SCENARIOS", scenario_results))

    env_results, best, worst, diff, done_at = run_environment_tests(meta)
    all_results.append(("ENVIRONMENT", env_results))

    reward_results = run_reward_tests()
    all_results.append(("REWARD FUNCTION", reward_results))

    server_results = run_server_tests()
    all_results.append(("FASTAPI SERVER", server_results))

    docker_results = run_dockerfile_checks()
    all_results.append(("DOCKERFILE", docker_results))

    inf_results = run_inference_script_checks()
    all_results.append(("INFERENCE SCRIPT", inf_results))

    openenv_results = run_openenv_compliance_checks()
    all_results.append(("OPENENV COMPLIANCE", openenv_results))

    # Print missing scenario fields exactly
    if missing_lines:
        print("\nSCENARIO FIELD MISSING REPORT")
        for line in missing_lines:
            print(line)

    # Print per-section details
    for title, res in all_results:
        _print_section(title, res)

    # Summary counts
    counts = {title: (sum(r.passed for r in res), len(res)) for title, res in all_results}
    passed_total = sum(p for p, t in counts.values())
    total = sum(t for p, t in counts.values())

    print("\n═══════════════════════════════════════════════")
    print("CRISIS ROOM — FULL TEST REPORT")
    print("═══════════════════════════════════════════════\n")
    print(f"MODELS:           {counts['MODELS'][0]}/{counts['MODELS'][1]} passed")
    print(f"SCENARIOS:        {counts['SCENARIOS'][0]}/{counts['SCENARIOS'][1]} passed  ({scenario_count} scenarios found)")
    print(f"ENVIRONMENT:      {counts['ENVIRONMENT'][0]}/{counts['ENVIRONMENT'][1]} passed")
    print(f"REWARD FUNCTION:  {counts['REWARD FUNCTION'][0]}/{counts['REWARD FUNCTION'][1]} passed")
    print(f"FASTAPI SERVER:   {counts['FASTAPI SERVER'][0]}/{counts['FASTAPI SERVER'][1]} passed")
    print(f"DOCKERFILE:       {counts['DOCKERFILE'][0]}/{counts['DOCKERFILE'][1]} passed")
    print(f"INFERENCE SCRIPT: {counts['INFERENCE SCRIPT'][0]}/{counts['INFERENCE SCRIPT'][1]} passed")
    print(f"OPENENV COMPLIANCE: {counts['OPENENV COMPLIANCE'][0]}/{counts['OPENENV COMPLIANCE'][1]} passed\n")
    print(f"TOTAL: {passed_total}/{total} tests passed\n")
    print("═══════════════════════════════════════════════")

    critical = []
    warnings = []
    missing_features = []

    # Reward discrimination warning
    print("\nREWARD DISCRIMINATION TEST:")
    print(f"Best episode reward:  {best:.3f}")
    print(f"Worst episode reward: {worst:.3f}")
    print(f"Difference:           {diff:.3f}")
    print(f"Status: {'PASS' if diff > 0.30 else 'FAIL'}")
    if diff <= 0.30:
        warnings.append("Reward function not discriminating enough (best-worst <= 0.30).")

    # Collect FAILs
    for title, res in all_results:
        for r in res:
            if not r.passed:
                critical.append(f"{title}: {r.name}")

    if missing_lines:
        warnings.append(f"Some scenarios missing required fields ({len(missing_lines)} missing entries).")

    print("\nCRITICAL ISSUES (fix before submitting):")
    if critical:
        for x in critical:
            print(f"- {x}")
    else:
        print("- None")

    print("\nWARNINGS (fix before hackathon):")
    if warnings:
        for x in warnings:
            print(f"- {x}")
    else:
        print("- None")

    print("\nMISSING FEATURES (nice to have):")
    if missing_features:
        for x in missing_features:
            print(f"- {x}")
    else:
        print("- None")
    print("═══════════════════════════════════════════════")

    pass_rate = passed_total / max(total, 1)
    return 0 if pass_rate >= 0.85 else 1


if __name__ == "__main__":
    raise SystemExit(main())

