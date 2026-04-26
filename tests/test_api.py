def test_get_root_serves_ui(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    # Lightweight smoke assertion that the UI content is present.
    assert "<html" in r.text.lower()


def test_static_assets_served(client):
    r1 = client.get("/static/index.html")
    assert r1.status_code == 200
    assert "text/html" in r1.headers.get("content-type", "")

    r2 = client.get("/static/reward_curve.png")
    assert r2.status_code == 200
    assert "image/png" in r2.headers.get("content-type", "")


def test_reset_step_loop_smoke(client):
    reset = client.post("/reset", json={"difficulty": "easy"})
    assert reset.status_code == 200
    payload = reset.json()
    assert payload["done"] is False
    obs = payload["observation"]
    assert obs["episode_id"]
    assert obs["step"] == 0
    assert obs["max_steps"] in (8, 10, 12)

    step = client.post(
        "/step",
        json={"action": {"action_type": "run_diagnostic", "target": "ssl_check"}},
    )
    assert step.status_code == 200
    step_payload = step.json()
    assert "observation" in step_payload
    assert isinstance(step_payload["reward"], (int, float))
    assert 0.0 <= float(step_payload["reward"]) <= 1.0


def test_malformed_json_is_4xx_not_500(client):
    r = client.post("/reset", content=b"not-json", headers={"content-type": "application/json"})
    assert 400 <= r.status_code < 500

