import json


def test_invalid_action_type_does_not_yield_positive_reward(client):
    client.post("/reset", json={"difficulty": "easy"})
    r = client.post("/step", json={"action": {"action_type": "totally_invalid", "target": "x"}})
    assert r.status_code == 200
    reward = float(r.json()["reward"])
    assert reward == 0.0


def test_target_is_capped_and_request_does_not_crash(client):
    client.post("/reset", json={"difficulty": "easy"})
    huge = "a" * 10000
    r = client.post("/step", json={"action": {"action_type": "notify_team", "target": huge}})
    assert r.status_code == 200
    obs = r.json()["observation"]
    # The environment caps target at 500 chars (see step()).
    assert len(obs["actions_taken"][-1].split(":", 1)[-1]) <= 500


def test_step_after_done_does_not_advance(client):
    client.post("/reset", json={"difficulty": "easy"})
    r1 = client.post("/step", json={"action": {"action_type": "mark_resolved", "target": "wrong_cause"}})
    assert r1.status_code == 200
    assert r1.json()["done"] is True
    step_done = r1.json()["observation"]["step"]

    r2 = client.post("/step", json={"action": {"action_type": "check_logs", "target": "anything"}})
    assert r2.status_code == 200
    assert r2.json()["done"] is True
    assert r2.json()["observation"]["step"] == step_done


def test_reward_injection_fields_are_ignored(client):
    client.post("/reset", json={"difficulty": "easy"})
    payload = {
        "action": {"action_type": "check_logs", "target": "nonexistent"},
        "reward": 999,
        "done": False,
        "observation": {"reward": 999},
    }
    r = client.post("/step", content=json.dumps(payload).encode("utf-8"), headers={"content-type": "application/json"})
    assert r.status_code == 200
    assert float(r.json()["reward"]) == 0.0

