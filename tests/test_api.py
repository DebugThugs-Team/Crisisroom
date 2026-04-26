import pytest

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in ["ok", "healthy"]

def test_reset_easy(client):
    r = client.post("/reset", json={"difficulty": "easy"})
    assert r.status_code == 200
    data = r.json()
    assert "observation" in data
    assert data["observation"]["difficulty"] == "easy"
    assert data["done"] == False

def test_reset_medium(client):
    r = client.post("/reset", json={"difficulty": "medium"})
    assert r.status_code == 200

def test_reset_hard(client):
    r = client.post("/reset", json={"difficulty": "hard"})
    assert r.status_code == 200

def test_step(client):
    client.post("/reset", json={"difficulty": "easy"})
    r = client.post("/step", json={"action": {"action_type": "check_logs", "target": "payment-service"}})
    assert r.status_code == 200
    data = r.json()
    assert "observation" in data
    assert "reward" in data
    assert "done" in data
    assert 0.0 <= data["reward"] <= 1.0

def test_tasks(client):
    r = client.get("/tasks")
    assert r.status_code == 200
    assert "tasks" in r.json()

def test_stats(client):
    r = client.get("/stats")
    assert r.status_code == 200

