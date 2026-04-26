import pytest

def test_reset_easy(env):
    obs = env.reset(difficulty="easy")
    assert obs.step == 0
    assert obs.max_steps == 8
    assert obs.difficulty == "easy"
    assert obs.done == False
    assert obs.reward == 0.0

def test_reset_medium(env):
    obs = env.reset(difficulty="medium")
    assert obs.max_steps == 10
    assert obs.difficulty == "medium"

def test_reset_hard(env):
    obs = env.reset(difficulty="hard")
    assert obs.max_steps == 12
    assert obs.difficulty == "hard"

def test_step_check_logs(env):
    from models import IncidentAction
    env.reset(difficulty="easy")
    action = IncidentAction(action_type="check_logs", target="payment-service")
    obs = env.step(action)
    assert obs.step == 1
    assert obs.reward >= 0.0
    assert obs.reward <= 1.0

def test_step_increments(env):
    from models import IncidentAction
    env.reset(difficulty="easy")
    for i in range(3):
        action = IncidentAction(action_type="check_logs", target="payment-service")
        obs = env.step(action)
    assert obs.step == 3

def test_episode_terminates_at_max_steps(env):
    from models import IncidentAction
    obs = env.reset(difficulty="easy")
    max_steps = obs.max_steps
    for i in range(max_steps + 2):
        action = IncidentAction(action_type="check_logs", target="payment-service")
        obs = env.step(action)
    assert obs.done == True

def test_reward_between_0_and_1(env):
    from models import IncidentAction
    env.reset(difficulty="easy")
    action = IncidentAction(action_type="check_logs", target="payment-service")
    obs = env.step(action)
    assert 0.0 <= obs.reward <= 1.0

