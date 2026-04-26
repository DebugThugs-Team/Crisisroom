import json
import os
import random
import time
from collections import Counter
from dataclasses import asdict, dataclass

import requests


@dataclass
class EpisodeResult:
    difficulty: str
    steps: int
    done: bool
    reward: float
    resolved: bool


DEFAULT_ACTIONS = [
    ("check_logs", ["payment-service", "api-gateway", "auth-service", "inventory-service", "redis-cluster", "dns-resolver"]),
    ("run_diagnostic", ["memory", "cpu", "db_connections", "dns_check", "data_integrity", "ssl_check"]),
    ("restart_service", ["payment-service", "redis-cluster", "dns-resolver", "api-gateway", "order-service"]),
    ("rollback_deployment", ["order-service", "pricing-service"]),
    ("scale_up", ["redis-cluster", "checkout-service"]),
    ("notify_team", ["payments down", "investigating", "mitigating", "suspect infra"]),
    ("escalate", ["oncall-lead", "infra-oncall", "sre-lead"]),
    ("mark_resolved", ["ssl_certificate_expired", "redis_out_of_memory", "dns_resolver_misconfiguration_after_infra_change", "wrong_cause"]),
]


def _pick_action():
    a, targets = random.choice(DEFAULT_ACTIONS)
    return {"action_type": a, "target": random.choice(targets)}


def run_episode(base_url: str, difficulty: str, max_steps_guard: int = 50) -> EpisodeResult:
    r = requests.post(f"{base_url}/reset", json={"difficulty": difficulty}, timeout=10)
    r.raise_for_status()
    obs = r.json()["observation"]
    max_steps = int(obs["max_steps"])

    steps = 0
    done = False
    reward = 0.0
    resolved = False

    while not done and steps < min(max_steps_guard, max_steps + 5):
        steps += 1
        action = _pick_action()
        step = requests.post(f"{base_url}/step", json={"action": action}, timeout=10)
        step.raise_for_status()
        payload = step.json()
        done = bool(payload["done"])
        reward = float(payload["reward"])
        resolved = bool(payload["observation"].get("root_cause_found")) and bool(payload["observation"].get("services_restored", 0))

    return EpisodeResult(difficulty=difficulty, steps=steps, done=done, reward=reward, resolved=resolved)


def main():
    base_url = os.environ.get("CRISIS_ROOM_BASE_URL", "http://127.0.0.1:7860")
    episodes = int(os.environ.get("CRISIS_ROOM_EPISODES", "100"))
    seed = int(os.environ.get("CRISIS_ROOM_SEED", str(int(time.time()))))
    random.seed(seed)

    results: list[EpisodeResult] = []
    for _ in range(episodes):
        difficulty = random.choice(["easy", "medium", "hard"])
        results.append(run_episode(base_url, difficulty))

    rewards = [r.reward for r in results]
    done_count = sum(1 for r in results if r.done)
    resolved_count = sum(1 for r in results if r.resolved)
    by_diff = Counter(r.difficulty for r in results)

    out = {
        "base_url": base_url,
        "episodes": episodes,
        "seed": seed,
        "done_count": done_count,
        "resolved_count": resolved_count,
        "avg_reward": sum(rewards) / max(len(rewards), 1),
        "min_reward": min(rewards) if rewards else None,
        "max_reward": max(rewards) if rewards else None,
        "difficulty_counts": dict(by_diff),
        "results": [asdict(r) for r in results],
    }

    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    with open("judge_summary.txt", "w", encoding="utf-8") as f:
        f.write(f"Base URL: {base_url}\n")
        f.write(f"Episodes: {episodes}\n")
        f.write(f"Seed: {seed}\n")
        f.write(f"Done: {done_count}/{episodes}\n")
        f.write(f"Resolved (heuristic): {resolved_count}/{episodes}\n")
        f.write(f"Reward avg/min/max: {out['avg_reward']:.4f} / {out['min_reward']:.4f} / {out['max_reward']:.4f}\n")
        f.write(f"Difficulty counts: {dict(by_diff)}\n")


if __name__ == "__main__":
    main()

