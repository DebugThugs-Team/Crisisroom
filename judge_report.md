## Crisis Room — Judge Report (OpenEnv / RL Hackathon)

### Problem statement
Production incidents are time-critical, high-stakes, and involve partial observability, noisy signals, and coordination. “Knowing the fix” isn’t enough: a competent Incident Commander must investigate, communicate, mitigate, and resolve under a strict time budget.

### What the environment is
`CrisisRoomEnvironment` is a step-based incident-response environment. Each episode samples a scenario (incident), exposes alerts/status/logs/diagnostics, and scores the agent based on correct resolution plus operationally realistic behavior (investigation before action, efficient steps, communication).

### Action space
Single discrete action with `(action_type, target)`:
- `check_logs` — target: service name
- `run_diagnostic` — target: diagnostic key (e.g. `memory`, `dns_check`, `ssl_check`)
- `restart_service` — target: service name
- `rollback_deployment` — target: service name
- `scale_up` — target: service name
- `notify_team` — target: free-text message (capped)
- `escalate` — target: free-text (capped)
- `mark_resolved` — target: stated root cause string

### Observation space
Each step returns an `IncidentObservation` including:
- incident context: `active_alerts`, `service_status`
- agent trace: `actions_taken`, `step`, `max_steps`, `steps_remaining`
- investigation outputs: `log_output`
- outcome fields: `root_cause_found`, `services_restored`, `done`
- reward: `partial_score` / `reward` (bounded to \([0, 1]\))

### Episode mechanics & termination
- `reset(difficulty)` samples an incident and initializes hidden session state.
- `step(action)` updates state and returns the next observation.
- Episodes terminate when:
  - `resolved == True`, or
  - `step_count >= max_steps` (difficulty-dependent).

### Reward function (high-level)
The reward is composed of independent components (bounded, weighted, with penalties):
- **Resolution score**: proportion of affected services restored.
- **Investigation score**: credit for checking relevant logs/diagnostics.
- **Communication score**: team notification; escalation rewarded on hard.
- **Efficiency**: only applies once meaningful progress exists (prevents “free reward” from random fast actions).
- **Penalties**: wrong/irrelevant restarts, redundant comms/escalations, invalid actions, and spam patterns.

### Anti–reward-hacking defenses
Implemented defenses:
- **Step budget enforcement**: hard termination at `max_steps`; step-after-done does not advance state.
- **Bounded rewards**: clamped to \([0, 1]\).
- **No reward injection**: request fields like `"reward": 999` are ignored; reward is computed server-side.
- **Spam / redundancy penalties**: repeated identical actions and redundant notify/escalate accrue penalties.
- **Input caps**: `target` is truncated to 500 chars; large payloads are handled without crashing.
- **Unknown actions**: do not yield positive reward.

Non-goals / limitations (explicit):
- This is a lightweight simulated incident environment (not a real cluster); “ground truth” is scenario-defined.
- Specialist delegation and postmortem quality are not modeled as separate action types (but can be extended).

### Demo flow (recommended)
1. Open the Space → UI loads at `/`.
2. Click reset (easy/medium/hard) → observe alerts + services.
3. Investigate (logs/diagnostics) → see `log_output` updates.
4. Apply fix (restart/rollback/mark_resolved) → episode ends with final reward.
5. Show anti-hacking: try invalid action / spam → observe penalties / no free reward.

### Tests & validation performed
Automated tests added (pytest):
- API: `/`, `/static/*`, `/reset`, `/step`, malformed JSON returns 4xx.
- Environment: difficulty handling, step increments, max steps termination, step-after-done.
- Reward hacking: invalid actions, reward injection fields, huge payload truncation.

Stress/audit scripts added:
- `scripts/stress_test.py` runs 100 random episodes and writes `test_results.json` + `judge_summary.txt`.
- `scripts/reward_hacking_audit.py` probes common exploit vectors and writes `reward_hacking_report.json`.

### Measurable improvement (what judges can look for)
- Reward curve in UI (`reward_curve.png`) + reported baseline vs trained scores in README.
- Environment provides dense step-wise reward signals for learning (not purely sparse).

### Future work (high-value)
- Add explicit “delegate” / “postmortem” actions and richer scenario graphs (cascades, mitigations).
- Expand reward components: delayed comms penalty, incorrect escalation penalty, mitigation-vs-fix separation.
- Add deterministic seeding for exact reproducibility across runs.

