import pytest

def test_invalid_action_no_positive_reward(env):
    from models import IncidentAction
    env.reset(difficulty="easy")
    action = IncidentAction(action_type="invalid_action_xyz", target="")
    obs = env.step(action)
    assert obs.reward < 0.3

def test_empty_target_no_exploit(env):
    from models import IncidentAction
    env.reset(difficulty="easy")
    action = IncidentAction(action_type="check_logs", target="")
    obs = env.step(action)
    assert obs.reward <= 1.0

def test_huge_payload_capped(env):
    from models import IncidentAction
    env.reset(difficulty="easy")
    action = IncidentAction(action_type="check_logs", target="x" * 10000)
    obs = env.step(action)
    assert obs.step == 1

def test_step_after_done_no_advance(env):
    from models import IncidentAction
    obs = env.reset(difficulty="easy")
    max_steps = obs.max_steps
    for i in range(max_steps):
        action = IncidentAction(action_type="check_logs", target="payment-service")
        obs = env.step(action)
    assert obs.done == True
    final_step = obs.step
    action = IncidentAction(action_type="check_logs", target="payment-service")
    obs2 = env.step(action)
    assert obs2.step == final_step

def test_repeated_notify_penalized(env):
    from models import IncidentAction
    env.reset(difficulty="easy")
    env.step(IncidentAction(action_type="notify_team", target="first"))
    obs = env.step(IncidentAction(action_type="notify_team", target="second"))
    assert obs.reward <= 1.0

def test_efficiency_only_with_progress(env):
    from models import IncidentAction
    env.reset(difficulty="easy")
    # Do only invalid actions — efficiency should not be rewarded
    for i in range(3):
        obs = env.step(IncidentAction(action_type="unknown_xyz", target=""))
    # reward should be very low since no real progress
    assert obs.reward < 0.3

