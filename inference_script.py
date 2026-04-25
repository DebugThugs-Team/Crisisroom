from __future__ import annotations

import os
import statistics
from typing import Any, Dict

import requests


HF_TOKEN = os.environ.get("HF_TOKEN")
MODEL_ID = os.environ.get("MODEL_ID", "meta-llama/Llama-3.1-8B-Instruct")
ENVIRONMENT_URL = os.environ.get("ENVIRONMENT_URL") or "http://localhost:8000"
NUM_EPISODES = int(os.environ.get("NUM_EPISODES", "3"))


def _hf_router_chat(prompt: str) -> str:
    """
    Minimal HF Inference Router chat call.
    We keep this intentionally simple for hackathon baselines.
    """
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN is required")

    url = "https://router.huggingface.co/v1/chat/completions"
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "Return only JSON with keys action_type and payload."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 120,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return (data["choices"][0]["message"]["content"] or "").strip()


def reset_env() -> Dict[str, Any]:
    r = requests.post(f"{ENVIRONMENT_URL}/reset", json={}, timeout=30)
    r.raise_for_status()
    return r.json()


def step_env(action_type: str, payload: str) -> Dict[str, Any]:
    r = requests.post(f"{ENVIRONMENT_URL}/step", json={"action_type": action_type, "payload": payload}, timeout=30)
    r.raise_for_status()
    return r.json()


def run_episode() -> float:
    obs = reset_env()
    done = bool(obs.get("done", False))
    episode_reward = 0.0

    while not done:
        prompt = f"incident_alert={obs.get('incident_alert','')}\nstep_count={obs.get('step_count')}\nlast_response={obs.get('last_response','')}"
        # Baseline policy: trivial triage then attempt resolve (kept deterministic for testing)
        if obs.get("step_count", 0) == 0:
            action_type, payload = "triage", "SEV1 initial assessment"
        else:
            action_type, payload = "declare_resolved", "Fixed. Root cause unknown."

        result = step_env(action_type, payload)
        obs = result["observation"]
        episode_reward = float(result["reward"])
        done = bool(result["done"])

    return float(episode_reward)


def main() -> None:
    scores = []
    for i in range(NUM_EPISODES):
        r = run_episode()
        scores.append(r)
        print(f"Episode {i+1} reward: {r:.3f}", flush=True)
    avg = statistics.mean(scores) if scores else 0.0
    print(f"Average reward: {avg:.3f}", flush=True)


if __name__ == "__main__":
    main()

