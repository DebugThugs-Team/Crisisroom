---
title: Crisis Room
emoji: 🚨
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
license: mit
---

# Crisis Room — Production Incident Response RL Environment

> Built for the Meta × Scalar × HuggingFace OpenEnv Hackathon, April 2026
> Team: DebugThugs — Hemank Aggarwal, Riddhika Sachdeva, Chinmay Nayar

It's 2:47 AM. Payment service is down. Revenue bleeding at $300,000 per minute. Six engineers on Slack. Someone has to take charge. No AI in the world is trained to do that job. We built the environment to train one.

---

## Submission Links

- 🚀 **Live Space:** https://huggingface.co/spaces/hemankkk/crisis_room
- 📓 **Training Notebook:** https://colab.research.google.com/drive/1kVOpV5HhHOu865rXwitTBruOM76ilFNJ?usp=sharing
- 💻 **GitHub:** https://github.com/DebugThugs-Team/Crisisroom
- 📝 **Blog:** https://huggingface.co/spaces/hemankkk/crisis_room/discussions/3#69eda5409d720b0bff794510
- 📈 **Reward Curve:** See below

---

## Training Results

![Training Results](reward_curve.png)

| Difficulty | Before Training | After Training | Improvement |
|---|---|---|---|
| Easy | 0.12 | 0.23 | +92% |
| Medium | 0.13 | 0.22 | +69% |
| Hard | 0.13 | 0.18 | +38% |
| **Average** | **0.13** | **0.21** | **+65%** |

Trained using GRPO with Unsloth on live HuggingFace Space environment.
Baseline: 0.13 → Trained: 0.214 (+65.1% improvement)

---

## What the Agent Does

The agent receives a live incident — active alerts, service statuses, log outputs — and must investigate root cause and fix it within a step budget. Eight actions available:

`check_logs` · `run_diagnostic` · `restart_service` · `rollback_deployment` · `scale_up` · `notify_team` · `escalate` · `mark_resolved`

---

## Three Difficulty Levels

**Easy (8 steps)** — Single service down, root cause visible in logs. DB connection pool exhausted, SSL certificate expired.

**Medium (10 steps)** — Cascading failure across multiple services. Redis OOM cascade, memory leak from bad deployment.

**Hard (12 steps)** — Silent data corruption, cascading DNS failure, Kubernetes OOMKilled crashloop, cache split-brain, thundering herd after cache flush.

---

## Reward Function

Five independent components — no single signal can be gamed:

| Component | Weight | Description |
|---|---|---|
| Resolution | 38% | Correct fix verified against hidden ground truth |
| Investigation | 28% | Relevant logs and diagnostics checked before fixing |
| Efficiency | 19% | Fewer steps = higher score |
| Communication | 10% | Team notified, escalated when appropriate |
| Fix bonus | 5% | Correct fix action type used |
| Wrong restarts | penalty | -0.1 per unnecessary or redundant action |
 
Rewards are non-sparse — partial score is returned at every step so the agent gets a signal throughout the episode.

---

## Reward Hacking Protection

- Step limit locked at reset — no action can modify it
- Resolution verified against hidden ground truth
- Redundant notify/escalate penalised
- Spam detection — 3 identical consecutive actions trigger penalty
- Unknown action penalty
- Input length capped at 500 characters
- Investigation score computed against actual log keys

---

## Running Locally

```bash
# Recommended: use a virtualenv for local dev/testing
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run the FastAPI app (serves UI at / and API at /reset, /step, etc.)
.venv/bin/uvicorn app:app --host 0.0.0.0 --port 7860
```

**Test it:**
```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"difficulty": "hard"}'
```

**Validate:**
```bash
openenv validate
# [OK] crisis_room: Ready for multi-mode deployment
```

---

## API

```bash
# Reset environment
curl -X POST https://hemankkk-crisis-room.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"difficulty": "easy"}'

# Take a step
curl -X POST https://hemankkk-crisis-room.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"action_type": "check_logs", "target": "payment-service"}}'

# List all tasks
curl https://hemankkk-crisis-room.hf.space/tasks

# Health check
curl https://hemankkk-crisis-room.hf.space/health

# Episode stats
curl https://hemankkk-crisis-room.hf.space/stats
```

---

## Reproducibility & Tests

Run the automated test suite:

```bash
.venv/bin/pytest -q
```

Run stress testing (writes `test_results.json` and `judge_summary.txt`):

```bash
CRISIS_ROOM_BASE_URL=http://127.0.0.1:7860 CRISIS_ROOM_EPISODES=100 .venv/bin/python scripts/stress_test.py
```

Run reward-hacking audit (writes `reward_hacking_report.json`):

```bash
CRISIS_ROOM_BASE_URL=http://127.0.0.1:7860 .venv/bin/python scripts/reward_hacking_audit.py
```

---

## Innovation / Why this matters

Most “incident demos” are static UIs or prompt-only simulations. Crisis Room is a **step-based RL environment** with:
- multi-component rewards (resolution, investigation, efficiency, communication) rather than a single sparse signal
- hidden ground truth per incident to prevent “declare resolved” reward gaming
- explicit anti-spam and invalid-action penalties
- a deployable FastAPI + UI demo on Hugging Face Spaces

### Available Actions
| Action | Description |
|---|---|
| `check_logs` | Read logs for a specific service |
| `run_diagnostic` | Run a diagnostic (memory, cpu, dns_check, data_integrity, ssl_check) |
| `restart_service` | Restart a service |
| `rollback_deployment` | Roll back to previous version |
| `scale_up` | Add more instances |
| `notify_team` | Send team notification |
| `escalate` | Escalate to on-call lead |
| `mark_resolved` | Close the incident with root cause |