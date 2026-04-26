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
-- 💻 **GitHub:** https://github.com/DebugThugs-Team/Crisisroom
- 📝 **Blog:** [blog.md](blog.md)
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
Baseline: 0.129 → Trained: 0.214 (+65.1% improvement)

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
cd server
PYTHONPATH=/path/to/crisis_room uvicorn app:app --host 0.0.0.0 --port 8000
```

**Test it:**
```bash
curl -X POST http://localhost:8000/reset \
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