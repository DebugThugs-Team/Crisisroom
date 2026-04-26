import json
import os
import time

import requests


def post_json(url: str, payload, timeout=10):
    return requests.post(url, json=payload, timeout=timeout)


def main():
    base_url = os.environ.get("CRISIS_ROOM_BASE_URL", "http://127.0.0.1:7860")
    out = {"base_url": base_url, "checks": []}

    def record(name: str, ok: bool, detail: str, status_code: int | None = None):
        out["checks"].append({"name": name, "ok": ok, "detail": detail, "status_code": status_code})

    # Reset
    r = post_json(f"{base_url}/reset", {"difficulty": "easy"})
    record("reset_easy", r.status_code == 200, "reset should succeed", r.status_code)
    if r.status_code != 200:
        _write(out)
        raise SystemExit(1)

    # Invalid action should not yield positive reward
    r = post_json(f"{base_url}/step", {"action": {"action_type": "invalid_action", "target": "x"}})
    ok = r.status_code == 200 and float(r.json().get("reward", 0.0)) == 0.0
    record("invalid_action_reward", ok, f"reward={r.json().get('reward')}", r.status_code)

    # Reward injection fields should be ignored
    r = requests.post(
        f"{base_url}/step",
        data=json.dumps(
            {
                "action": {"action_type": "check_logs", "target": "nonexistent"},
                "reward": 999,
                "done": False,
                "observation": {"reward": 999},
            }
        ).encode("utf-8"),
        headers={"content-type": "application/json"},
        timeout=10,
    )
    ok = r.status_code == 200 and float(r.json().get("reward", 0.0)) == 0.0
    record("reward_injection_ignored", ok, f"reward={r.json().get('reward')}", r.status_code)

    # Malformed JSON should not 500
    r = requests.post(
        f"{base_url}/reset",
        data=b"{not-json",
        headers={"content-type": "application/json"},
        timeout=10,
    )
    record("malformed_json", 400 <= r.status_code < 500, "should return clean 4xx", r.status_code)

    # Huge payload should not crash and should be capped
    huge = "a" * 10000
    r = post_json(f"{base_url}/step", {"action": {"action_type": "notify_team", "target": huge}})
    ok = r.status_code == 200 and len(r.json()["observation"]["actions_taken"][-1].split(":", 1)[-1]) <= 500
    record("huge_payload_capped", ok, "target should be capped to 500 chars", r.status_code)

    # Step after done should not advance
    post_json(f"{base_url}/reset", {"difficulty": "easy"})
    r1 = post_json(f"{base_url}/step", {"action": {"action_type": "mark_resolved", "target": "wrong_cause"}})
    r2 = post_json(f"{base_url}/step", {"action": {"action_type": "check_logs", "target": "anything"}})
    ok = r1.status_code == 200 and r2.status_code == 200 and r2.json()["observation"]["step"] == r1.json()["observation"]["step"]
    record("step_after_done", ok, "step should not advance after done", r2.status_code)

    _write(out)


def _write(out):
    out["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open("reward_hacking_report.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    main()

