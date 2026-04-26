from server.crisis_room_environment import CrisisRoomEnvironment, DIFFICULTY_CONFIG
from models import IncidentAction


def test_reset_supports_difficulty_levels():
    env = CrisisRoomEnvironment()
    for difficulty in ("easy", "medium", "hard"):
        obs = env.reset(difficulty=difficulty)
        assert obs.difficulty == difficulty
        assert obs.max_steps == DIFFICULTY_CONFIG[difficulty]["max_steps"]
        assert obs.step == 0
        assert obs.episode_id
        assert obs.done is False


def test_invalid_difficulty_does_not_crash():
    env = CrisisRoomEnvironment()
    obs = env.reset(difficulty="totally-invalid")
    assert obs.difficulty in ("easy", "medium", "hard")
    assert obs.episode_id


def test_step_count_increments_and_max_steps_enforced():
    env = CrisisRoomEnvironment()
    obs = env.reset(difficulty="easy")
    max_steps = obs.max_steps

    for i in range(max_steps):
        obs = env.step(IncidentAction(action_type="check_logs", target="nonexistent-service"))
        assert obs.step == i + 1
        if i < max_steps - 1:
            assert obs.done is False

    assert obs.done is True
    assert obs.step == max_steps

    # After done, the episode should not advance further.
    obs2 = env.step(IncidentAction(action_type="check_logs", target="nonexistent-service"))
    assert obs2.done is True
    assert obs2.step == max_steps


def test_reward_is_bounded_and_not_positive_for_useless_actions():
    env = CrisisRoomEnvironment()
    env.reset(difficulty="easy")
    obs = env.step(IncidentAction(action_type="check_logs", target="nonexistent-service"))
    assert 0.0 <= float(obs.reward) <= 1.0
    assert float(obs.reward) == 0.0

