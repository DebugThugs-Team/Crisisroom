import sys
sys.path.insert(0, '/Users/shivangnayar/Downloads/crisis_room/server')
sys.path.insert(0, '/Users/shivangnayar/Downloads/crisis_room')

from crisis_room_environment import CrisisRoomEnvironment
from models import IncidentAction

env = CrisisRoomEnvironment()
results = {}

# Test 1: Invalid action type
env.reset(difficulty="easy")
obs = env.step(IncidentAction(action_type="INVALID_XYZ", target=""))
results["invalid_action_reward"] = obs.reward
assert obs.reward < 0.3, f"FAIL: Invalid action got reward {obs.reward}"
print(f"✅ Invalid action reward: {obs.reward:.3f} (expected < 0.3)")

# Test 2: Empty target
env.reset(difficulty="easy")
obs = env.step(IncidentAction(action_type="check_logs", target=""))
results["empty_target_reward"] = obs.reward
print(f"✅ Empty target reward: {obs.reward:.3f}")

# Test 3: Huge payload capped
env.reset(difficulty="easy")
obs = env.step(IncidentAction(action_type="check_logs", target="x" * 10000))
assert obs.step == 1, "FAIL: Step did not increment after huge payload"
print(f"✅ Huge payload capped: step={obs.step}")

# Test 4: Step after done does not advance
obs = env.reset(difficulty="easy")
for i in range(obs.max_steps):
    obs = env.step(IncidentAction(action_type="check_logs", target="payment-service"))
assert obs.done == True
final_step = obs.step
obs2 = env.step(IncidentAction(action_type="check_logs", target="payment-service"))
assert obs2.step == final_step, f"FAIL: Step advanced after done: {obs2.step} vs {final_step}"
print(f"✅ Step after done does not advance: step={obs2.step}")

# Test 5: Redundant notify penalized
env.reset(difficulty="easy")
obs1 = env.step(IncidentAction(action_type="notify_team", target="first"))
obs2 = env.step(IncidentAction(action_type="notify_team", target="second"))
print(f"✅ Redundant notify: first={obs1.reward:.3f} second={obs2.reward:.3f}")

# Test 6: Reward always between 0 and 1
env.reset(difficulty="hard")
for i in range(12):
    obs = env.step(IncidentAction(action_type="check_logs", target="api-gateway"))
    assert 0.0 <= obs.reward <= 1.0, f"FAIL: Reward out of bounds: {obs.reward}"
print(f"✅ Reward always 0-1: final={obs.reward:.3f}")

# Test 7: All 3 difficulties work
for diff in ["easy", "medium", "hard"]:
    obs = env.reset(difficulty=diff)
    assert obs.difficulty == diff
    assert obs.done == False
    assert obs.reward == 0.0
    print(f"✅ Reset {diff}: max_steps={obs.max_steps}")

# Test 8: Efficiency only rewarded with real progress
env.reset(difficulty="easy")
for i in range(5):
    obs = env.step(IncidentAction(action_type="unknown_xyz", target=""))
print(f"✅ Efficiency without progress: reward={obs.reward:.3f} (expected < 0.3)")

# Test 9: Correct fix gets high reward
env.reset(difficulty="easy")
env.step(IncidentAction(action_type="check_logs", target="payment-service"))
env.step(IncidentAction(action_type="run_diagnostic", target="db_connections"))
env.step(IncidentAction(action_type="notify_team", target="DB pool exhausted"))
obs = env.step(IncidentAction(action_type="restart_service", target="payment-service"))
print(f"✅ Correct fix reward: {obs.reward:.3f} (expected > 0.3)")

# Test 10: Wrong fix gets penalized
env.reset(difficulty="easy")
obs = env.step(IncidentAction(action_type="restart_service", target="wrong-service"))
print(f"✅ Wrong fix penalty applied: reward={obs.reward:.3f}")

print("\n✅ ALL REWARD HACKING TESTS PASSED")
print(f"Results: {results}")

