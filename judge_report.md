# Crisis Room — Judge Report

## Environment Summary
- **Type:** OpenEnv-compliant RL environment
- **Task:** AI Incident Commander managing production outages
- **Difficulties:** Easy (8 steps), Medium (10 steps), Hard (12 steps)
- **Incidents:** 9 across 3 difficulty levels
- **Actions:** 8 types (check_logs, run_diagnostic, restart_service, rollback_deployment, scale_up, notify_team, escalate, mark_resolved)

## Reward Function
5 independent components — no single signal can be gamed:
- Resolution (38%): verified against hidden ground truth
- Investigation (28%): computed against actual log keys
- Efficiency (19%): only awarded when real progress exists
- Communication (10%): boolean flags, redundant calls penalised
- Fix bonus (5%): correct fix action type used

## Anti-Reward-Hacking Measures
- Step limit locked at reset — no action can modify it
- Resolution verified against hidden ground truth
- Redundant notify/escalate penalised with wrong_restarts += 1
- Spam detection — 3 identical consecutive actions trigger penalty
- Unknown action penalty — wrong_restarts += 1
- Input length capped at 500 characters
- Efficiency only rewarded when investigation/resolution/comms > 0
- Wrong mark_resolved adds penalty

## Test Results
- 12/12 tests passing
- Reward hacking audit: all vectors closed
- Stress test (20 episodes): avg reward 0.1722, max 0.64
- Invalid actions: no positive reward
- Malformed JSON: clean 400 response
- Step after done: does not advance

## Training Evidence
- Algorithm: GRPO with Unsloth
- Model: Qwen2.5-1.5B with QLoRA (r=16)
- Baseline: 0.129 normalized reward
- Trained: 0.214 normalized reward
- Improvement: +65.1%
- Connected to live HuggingFace Space during training

## Links
- Space: https://huggingface.co/spaces/hemankkk/crisis_room
- Notebook: Crisis_room_FINAL.ipynb
- Blog: blog.md

