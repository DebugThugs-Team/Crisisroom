import sys
sys.path.insert(0, '/Users/shivangnayar/Downloads/crisis_room/server')
sys.path.insert(0, '/Users/shivangnayar/Downloads/crisis_room')

from crisis_room_environment import CrisisRoomEnvironment, _compute_reward, _SESSION
from models import IncidentAction

env = CrisisRoomEnvironment()

print("=== REWARD COMPONENT AUDIT ===\n")

# Scenario 1: Perfect episode — should get high reward
print("Scenario 1: Perfect investigation + correct fix")
obs = env.reset(difficulty="easy")
incident = _SESSION["incident"]
print(f"  Incident: {incident['title']}")
print(f"  Fix needed: {incident['fix_action']}:{incident['fix_target']}")

env.step(IncidentAction(action_type="check_logs", target=list(incident['logs'].keys())[0]))
env.step(IncidentAction(action_type="run_diagnostic", target=list(incident['diagnostics'].keys())[0]))
env.step(IncidentAction(action_type="notify_team", target="investigating now"))
obs = env.step(IncidentAction(action_type=incident['fix_action'], target=incident['fix_target']))
print(f"  Final reward: {obs.reward:.4f} (expected > 0.5)")
print(f"  Done: {obs.done}")
print(f"  Root cause found: {obs.root_cause_found}")
print(f"  Services restored: {obs.services_restored}")

# Scenario 2: Wrong fix — should get penalized
print("\nScenario 2: Wrong fix without investigation")
env.reset(difficulty="easy")
obs = env.step(IncidentAction(action_type="restart_service", target="wrong-service-xyz"))
print(f"  Reward after wrong fix: {obs.reward:.4f} (expected < 0.3)")

# Scenario 3: Communication only — partial reward
print("\nScenario 3: Investigation + communication only")
env.reset(difficulty="medium")
incident = _SESSION["incident"]
env.step(IncidentAction(action_type="check_logs", target=list(incident['logs'].keys())[0]))
env.step(IncidentAction(action_type="notify_team", target="team updated"))
obs = env.step(IncidentAction(action_type="escalate", target="need help"))
print(f"  Partial reward: {obs.reward:.4f} (expected 0.1-0.5)")

print("\n✅ REWARD COMPONENT AUDIT COMPLETE")

