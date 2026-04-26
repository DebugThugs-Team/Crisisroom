import sys, random
sys.path.insert(0, '/Users/shivangnayar/Downloads/crisis_room/server')
sys.path.insert(0, '/Users/shivangnayar/Downloads/crisis_room')

from crisis_room_environment import CrisisRoomEnvironment
from models import IncidentAction

env = CrisisRoomEnvironment()
difficulties = ["easy", "medium", "hard"]
actions = ["check_logs", "run_diagnostic", "restart_service",
           "rollback_deployment", "notify_team", "escalate", "mark_resolved"]
targets = ["payment-service", "api-gateway", "redis-cluster",
           "order-service", "memory", "db_connections", "dns_check"]

all_rewards = []
resolved_count = 0
errors = []

for episode in range(30):
    try:
        difficulty = difficulties[episode % 3]
        obs = env.reset(difficulty=difficulty)
        episode_rewards = []

        for step in range(obs.max_steps):
            action = IncidentAction(
                action_type=random.choice(actions),
                target=random.choice(targets)
            )
            obs = env.step(action)
            episode_rewards.append(obs.reward)
            assert 0.0 <= obs.reward <= 1.0, f"Reward out of bounds: {obs.reward}"
            if obs.done:
                if obs.services_restored > 0:
                    resolved_count += 1
                break

        all_rewards.append(max(episode_rewards))
    except Exception as e:
        errors.append(f"Episode {episode}: {e}")

avg = sum(all_rewards) / len(all_rewards)
print(f"\n=== STRESS TEST RESULTS ===")
print(f"Episodes:     30/30 completed")
print(f"Avg reward:   {avg:.4f}")
print(f"Min reward:   {min(all_rewards):.4f}")
print(f"Max reward:   {max(all_rewards):.4f}")
print(f"Resolved:     {resolved_count}/30")
print(f"Errors:       {len(errors)}")
if errors:
    for e in errors:
        print(f"  ERROR: {e}")
else:
    print("✅ Zero errors across 30 episodes")
assert len(errors) == 0, "FAIL: Errors during stress test"
assert avg > 0.0, "FAIL: Average reward is 0"
print("✅ STRESS TEST PASSED")

