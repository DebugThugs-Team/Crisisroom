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

Every engineer knows the feeling. It's 3am. PagerDuty fires. Five services are down. Revenue is bleeding. You have logs, alerts, and ten minutes to figure out what broke.

Crisis Room is an RL environment where an agent learns to be that engineer — reading alerts, checking logs, running diagnostics, and restoring service as fast as possible.

---

## What the agent does

The agent receives a live incident: active alerts, service statuses, and an environment message. It must investigate the root cause and fix it within a step budget. Eight actions are available:

`check_logs` · `run_diagnostic` · `restart_service` · `rollback_deployment` · `scale_up` · `notify_team` · `escalate` · `mark_resolved`

The faster and more accurately it resolves the incident, the higher the reward.

---

## Three difficulty levels

**Easy** (8 steps) — Single service down, root cause visible in logs. Example: DB connection pool exhausted, SSL certificate expired.

**Medium** (10 steps) — Cascading failure across multiple services. Example: Redis OOM taking down checkout, auth, and inventory simultaneously. Memory leak from a bad deployment.

**Hard** (12 steps) — Silent data corruption or intermittent DNS failure. No obvious alerts. All services reporting healthy. Agent must run diagnostics to find the pattern.

---

## Reward function

| Component | Weight | Description |
|---|---|---|
| Resolution | 40% | Service restored with correct fix |
| Investigation | 30% | Relevant logs and diagnostics checked before fixing |
| Efficiency | 20% | Fewer steps = higher score |
| Communication | 10% | Team notified, escalated when appropriate |
| Wrong restarts | penalty | -0.1 per unnecessary action |

Rewards are non-sparse — partial score is returned at every step so the agent gets a signal throughout the episode.

---

## Baseline scores (Qwen/Qwen2.5-72B-Instruct, zero fine-tuning)

| Task | Score |
|---|---|
| easy-incident | 0.500 |
| medium-incident | 0.840 |
| hard-incident | 0.467 |
| **Average** | **0.602** |

*Post fine-tuning scores (GRPO, on-site training) — to be updated at hackathon*

---

## Running locally

```bash
# Start the server
cd server
PYTHONPATH=/path/to/crisis_room uvicorn app:app --host 0.0.0.0 --port 8000

# Run inference
HF_TOKEN=your_token python3 inference.py
```

## API

```
POST /reset          {"difficulty": "easy"|"medium"|"hard"}
POST /step           {"action": {"action_type": "...", "target": "..."}}
GET  /tasks          List all 3 tasks
GET  /health         Health check
```
## Training Results

![Reward Curve](reward_curve.png)

| Metric | Value |
|---|---|
| Baseline reward | 1.7 |
| Post-training reward | 2.2 |
| Improvement | ~17% across 3 reward signals |
| Training notebook | [Crisis_room.ipynb](Crisis_room.ipynb) |

## Links
- **HF Space:** https://huggingface.co/spaces/DebugThugs/crisis-room
- **Blog:** YOUR_BLOG_URL_HERE
- **Notebook:** [Crisis_room.ipynb](Crisis_room.ipynb)