import asyncio
import json
import os
import textwrap
from typing import List, Optional

import requests
from openai import OpenAI

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "dummy")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")
BENCHMARK = "crisis_room"
SUCCESS_SCORE_THRESHOLD = 0.3

SYSTEM_PROMPT = textwrap.dedent("""
    You are an AI Site Reliability Engineer responding to a live production incident.
    You will receive alerts, service statuses, and log outputs.
    Your job is to investigate, identify the root cause, fix it, and notify the team.

    Available actions:
    - check_logs: Read logs for a specific service. target = service name.
    - run_diagnostic: Run a diagnostic check. target = diagnostic name (e.g. memory, cpu, db_connections, dns_check, data_integrity, ssl_check).
    - restart_service: Restart a specific service. Only do this after you understand the cause.
    - rollback_deployment: Roll back a service to previous version. target = service name.
    - scale_up: Add more instances. target = service name.
    - notify_team: Send a message to the team. target = your message.
    - escalate: Escalate to on-call lead. target = reason.
    - mark_resolved: Close the incident. target = root cause description.

    Respond with ONLY a JSON object like:
    {"action_type": "check_logs", "target": "payment-service"}

    No explanation. No preamble. Valid JSON only.
    Think step by step: investigate first, then fix, then notify.
""").strip()

TASKS = [
    {"name": "easy-incident",   "difficulty": "easy"},
    {"name": "medium-incident", "difficulty": "medium"},
    {"name": "hard-incident",   "difficulty": "hard"},
]


def env_reset(difficulty: str):
    r = requests.post(
        f"{ENV_BASE_URL}/reset",
        json={"difficulty": difficulty},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def env_step(action_type: str, target: str):
    r = requests.post(
        f"{ENV_BASE_URL}/step",
        json={"action": {"action_type": action_type, "target": target}},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_action(client: OpenAI, obs: dict, history: List[str]) -> dict:
    alerts = obs.get("active_alerts", [])
    status = obs.get("service_status", {})
    log_out = obs.get("log_output", "")
    message = obs.get("message", "")
    history_block = "\n".join(history[-6:]) if history else "None"

    user_prompt = textwrap.dedent(f"""
        INCIDENT MESSAGE: {message}

        ACTIVE ALERTS:
        {chr(10).join(alerts)}

        SERVICE STATUS:
        {json.dumps(status, indent=2)}

        LAST LOG/DIAGNOSTIC OUTPUT:
        {log_out or "None yet"}

        PREVIOUS ACTIONS:
        {history_block}

        What is your next action? Respond with JSON only.
    """).strip()

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=100,
        )
        text = (completion.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as exc:
        print(f"[DEBUG] Model error: {exc}", flush=True)
        return {"action_type": "check_logs", "target": ""}


def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    err = error if error else "null"
    print(f"[STEP] step={step} action={action[:100]} reward={reward:.2f} done={str(done).lower()} error={err}", flush=True)

def log_end(success, steps, score, rewards):
    r = ",".join(f"{x:.2f}" for x in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={r}", flush=True)


async def run_episode(client: OpenAI, task: dict) -> float:
    difficulty = task["difficulty"]
    task_name = task["name"]
    max_steps = {"easy": 8, "medium": 10, "hard": 12}[difficulty]

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = env_reset(difficulty)
        obs = result["observation"]
        done = result.get("done", False)

        for step in range(1, max_steps + 1):
            if done:
                break

            action_dict = get_action(client, obs, history)
            action_type = action_dict.get("action_type", "check_logs")
            target = action_dict.get("target", "")

            try:
                result = env_step(action_type, target)
                obs = result["observation"]
                reward = float(result.get("reward", 0.0))
                done = result.get("done", False)
                error = None
            except Exception as e:
                reward = 0.0
                done = True
                error = str(e)

            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=f"{action_type}:{target}", reward=reward, done=done, error=error)
            history.append(f"Step {step}: {action_type}({target}) -> reward {reward:+.2f}")

            if done:
                break

        score = max(rewards) if rewards else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    all_scores = []

    for task in TASKS:
        score = await run_episode(client, task)
        all_scores.append(score)

    print(f"\n=== FINAL RESULTS ===", flush=True)
    for task, score in zip(TASKS, all_scores):
        print(f"{task['name']}: {score:.3f}", flush=True)
    print(f"Average: {sum(all_scores)/len(all_scores):.3f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())