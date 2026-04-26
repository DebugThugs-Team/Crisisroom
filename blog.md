# Crisis Room: We Trained an AI to Command Production Incidents

**DebugThugs — Meta × Scalar × HuggingFace OpenEnv Hackathon, April 2026**

---

It's 2:47 AM. Your payment service is down. Revenue is bleeding at $300,000 per minute. Six engineers are in a Slack channel. Alerts are firing. Logs are scrolling. And someone has to take charge.

That person is the Incident Commander. And until now, no AI in the world has been trained to do that job.

We built the environment to train one.

---

## The Problem Nobody Has Solved

Every engineering organization at scale has lived through a production crisis. The technical fix — restart the service, roll back the deployment, flush the cache — is usually straightforward once you know what broke. The hard part is the 20 minutes before you figure that out.

During those 20 minutes, someone has to:

- Read the alerts and form an initial hypothesis
- Assign the right engineers to investigate the right systems
- Synthesize conflicting information from multiple specialists
- Keep the CEO, customer support, and status page updated
- Make the call on when to escalate, when to act, when to declare resolution

This is the Incident Commander role. It requires multi-step reasoning, information synthesis under pressure, stakeholder communication, and the judgment to know which specialist to trust when their answers conflict.

No RL environment has ever been built to train this. Crisis Room is the first.

---

## What We Built

Crisis Room is an OpenEnv-compliant reinforcement learning environment where an LLM agent learns to manage cascading production system failures — investigating root causes, issuing remediation commands, and communicating to stakeholders — all within a step budget that simulates real time pressure.

The environment exposes three incident difficulty levels, eight agent action types, four independent reward components, and a full anti-reward-hacking suite. It runs as a FastAPI server, validates cleanly with `openenv validate`, and is deployed live on Hugging Face Spaces.

**Live environment:** [https://huggingface.co/spaces/hemankkk/crisis_room](https://huggingface.co/spaces/hemankkk/crisis_room)

---

## The Architecture

### What the Agent Sees

On every step, the agent receives a structured observation containing:

- The incident title and severity
- Active alerts firing across the system
- Current service status for every affected service (healthy / degraded / down)
- Log or diagnostic output from the last action
- A running list of every action taken in this episode
- Signals: root cause found, services restored, steps remaining, partial score

The agent does **not** see the hidden ground truth. It must infer root cause from logs and diagnostics — exactly as a real engineer would.

### What the Agent Can Do

Eight action types, each with a specific purpose:

| Action | Purpose |
|---|---|
| `check_logs` | Read logs for a specific service |
| `run_diagnostic` | Run a named diagnostic (memory, cpu, dns_check, data_integrity, ssl_check) |
| `restart_service` | Restart a service — only effective if it's the right one |
| `rollback_deployment` | Roll back to a previous version |
| `scale_up` | Add instances — reduces pressure but doesn't fix root cause |
| `notify_team` | Communicate to the team — required once, penalized if repeated |
| `escalate` | Escalate to on-call lead — required for hard incidents |
| `mark_resolved` | Close the incident with a stated root cause |

### What Ends an Episode

An episode ends when the agent issues the correct fix action (`restart_service`, `rollback_deployment`, or `mark_resolved` with the correct root cause), or when the step budget is exhausted — whichever comes first.

---

## The Incident Library

We built six production incidents across three difficulty tiers, each based on real failure patterns from Google SRE, PagerDuty, and Datadog research.

### Easy (8 steps)

**DB Connection Pool Exhausted** — Payment service returning 500 errors. Root cause visible in logs. Single service affected. Agent must check logs, identify pool exhaustion, restart the service.

**SSL Certificate Expired** — API gateway SSL handshake failures at 95%. Certificate expiry flagged in logs 7 days prior but not acted on. Agent must run ssl_check diagnostic, then mark_resolved.

### Medium (10 steps)

**Redis Out of Memory** — Checkout, auth, and inventory all degraded simultaneously. Redis OOM taking down three services at once. Agent must identify the shared dependency, not treat each service as a separate failure.

**Memory Leak from Bad Deployment** — Order service slowly degrading after a deployment. Memory growing at 120MB/min. No obvious crash — agent must correlate deployment timing with memory trend and rollback.

### Hard (12 steps)

**Silent Data Corruption** — All services report healthy. No infrastructure alerts. Customers reporting wrong order amounts. Agent must run `data_integrity` diagnostic to find a float32 precision bug introduced in v3.1.0.

**Cascading DNS Failure** — Intermittent failures across multiple services. CoreDNS configmap missing a forwarding entry after an infrastructure change. Agent must distinguish DNS failure from application errors and restart the DNS resolver.

---

## The Reward Function

Four independent components. No single signal can be gamed without the others pulling it down.

```
reward = (0.40 × resolution_score)
       + (0.30 × investigation_score)
       + (0.20 × efficiency_score)
       + (0.10 × communication_score)
       - (0.10 × wrong_restarts)
```

**Resolution (40%)** — Did the agent fix the right service with the right action? Verified against hidden ground truth. Services restored divided by services affected.

**Investigation (30%)** — Did the agent check relevant logs and run relevant diagnostics before acting? Measured against the actual log keys and diagnostic names available in the incident. Rewards thorough investigation, not lucky guesses.

**Efficiency (20%)** — Fewer steps equals higher score. An agent that resolves in 4 steps earns full marks here. An agent that burns all 12 steps earns near zero. Trains urgency.

**Communication (10%)** — Was the team notified? Was the incident escalated on hard difficulty? Trains the communication habits that distinguish good incident commanders from great ones.

**Penalty** — `-0.1` per wrong restart, wrong rollback, redundant notification, redundant escalation, or unknown action type. Reward hacking is expensive.

---

## Reward Hacking Protection

We took reward hacking seriously. Here is every vector we closed:

**Step limit** — `max_steps` is set at reset from a locked config dict. No action type can modify it. Episodes cannot be extended.

**Resolution verification** — `services_restored` only increments when the correct fix action is applied to the correct target, verified against hidden ground truth in the incident dict. The agent cannot claim resolution without earning it.

**Redundant action penalty** — `notify_team` and `escalate` are boolean flags. Calling them a second time after they are already set triggers `wrong_restarts += 1` and a penalty. No free stakeholder spam.

**Spam detection** — Three identical consecutive actions in `actions_taken` trigger an automatic penalty. The agent cannot loop on `run_diagnostic:memory` indefinitely for free.

**Unknown action penalty** — Any unrecognized `action_type` also triggers `wrong_restarts += 1`. Garbage inputs are not free.

**Input length cap** — `action.target` is truncated to 500 characters. Oversized payloads cannot bloat state.

**Investigation score denominator** — Investigation credit is computed against `incident["logs"].keys()` and `incident["diagnostics"].keys()`, not against `affected_services`. An agent cannot earn investigation credit by checking unrelated services.

---

## Baseline Results

We ran the environment against `Qwen/Qwen2.5-72B-Instruct` with zero fine-tuning to establish a baseline. The model had never seen Crisis Room before.

| Task | Score |
|---|---|
| easy-incident | 0.500 |
| medium-incident | 0.840 |
| hard-incident | 0.467 |
| **Average** | **0.602** |

The medium score of 0.840 is particularly notable — the model correctly identified a memory leak from deployment timing in 3 steps. The hard score of 0.467 shows clear room for improvement, which is exactly what GRPO training is designed to close.

*Post fine-tuning scores (GRPO, on-site training) — to be updated at hackathon*

---

## The Training Pipeline

The training loop uses **Unsloth** for efficient fine-tuning and **TRL's GRPOTrainer** for reinforcement learning. GRPO generates multiple candidate action sequences per prompt, scores each against our reward function, and updates the model to prefer higher-scoring behavior.

Why GRPO over PPO? No value network needed. Simpler, more stable, and proven by DeepSeek-R1. The algorithm computes advantage as `(reward - mean) / std` across a group of rollouts, and pushes the model toward the higher-advantage responses.

Training connects directly to the live OpenEnv environment via HTTP — every episode is a real interaction with `POST /reset` and `POST /step`, not a static dataset. The model learns from actual environment feedback.

---

## Themes Hit

**Theme 3.1 — World Modeling: Professional Tasks** (Primary)

The agent interacts with a dynamic system — logs, diagnostics, service states — and must maintain causal reasoning about what broke and why. Every incident is a partially observable world. The agent cannot see the ground truth. It must build a world model from evidence and act on it. This is exactly what the theme describes: real hard work instead of shortcuts.

**Theme 2 — Long-Horizon Planning** (Secondary)

Medium and hard incidents require multi-step hypothesis formation with delayed resolution reward. The hard DNS incident requires the agent to form a theory across 4-5 investigative steps before acting. Early decisions constrain later options — an unnecessary restart early in the episode costs penalty points that compound through the episode.

---

## The Stack

- **OpenEnv** — environment interface, validation, deployment
- **FastAPI** — HTTP server exposing `/reset`, `/step`, `/tasks`, `/health`
- **Pydantic v2** — `IncidentAction` and `IncidentObservation` models
- **TRL + GRPO** — reinforcement learning trainer
- **Unsloth** — efficient fine-tuning on Colab T4/A100
- **Hugging Face Spaces** — live deployment

---

## Running It Yourself

**Start the server:**
```bash
cd server
PYTHONPATH=/path/to/crisis_room uvicorn app:app --host 0.0.0.0 --port 8000
```

**Run a full episode:**
```bash
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"difficulty": "hard"}'

curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"action_type": "run_diagnostic", "target": "dns_check"}}'

curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"action_type": "restart_service", "target": "dns-resolver"}}'
```

**Run inference with a real model:**
```bash
HF_TOKEN=your_token python3 inference.py
```

**Validate:**
```bash
openenv validate
# [OK] crisis_room: Ready for multi-mode deployment
```

---

## Why This Matters

The real-world value is immediate and quantifiable. AI-assisted incident response reduces MTTR by 30-50% — that translates directly to millions of dollars saved per year for any engineering organization at scale. Every company that runs production systems at scale has this problem. Nobody has trained an RL agent to solve it.

Crisis Room is the first environment purpose-built to do exactly that.

---

*Built by DebugThugs — Hemank Aggarwal, Riddhika Sachdeva, Chinmay Nayar*
*Meta × Scalar × HuggingFace OpenEnv Hackathon, April 2026*
*Environment: [https://huggingface.co/spaces/hemankkk/crisis_room](https://huggingface.co/spaces/hemankkk/crisis_room)*
