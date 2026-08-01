"""Tests for GoapEngine orchestration harness."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from heal_my_goap.engine import GoapEngine
from heal_my_goap.models import Action, Goal, WorldState
from heal_my_goap.synthesizer import LLMSynthesizer


@pytest.fixture
def temp_storage_path(tmp_path: Any) -> str:
    """Fixture providing temporary action storage file path string."""
    return str(tmp_path / "test_engine_actions.json")


def test_engine_successful_direct_planning(temp_storage_path: str) -> None:
    """Verifies engine execution when baseline actions achieve goal."""
    action = Action(
        name="open_door",
        preconditions={"has_key": True},
        effects={"door_open": True},
        cost=1,
    )
    engine = GoapEngine(
        initial_actions=[action], storage_path=temp_storage_path
    )

    ws_kwargs: dict[str, Any] = {"has_key": True, "door_open": False}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"door_open": True})

    res = engine.run(initial_state, goal)
    assert res.success is True
    assert res.final_state.get("door_open") is True
    assert len(res.executed_actions) == 1
    assert res.executed_actions[0].name == "open_door"


def test_engine_self_healing_loop(temp_storage_path: str) -> None:
    """Verifies self-healing retry loop synthesizes missing bridge action."""
    initial_actions = [
        Action(
            name="open_door",
            preconditions={"has_key": True},
            effects={"door_open": True},
            cost=1,
        )
    ]

    mock_synthesizer = MagicMock(spec=LLMSynthesizer)
    synth_bridge = Action(
        name="synth_find_key",
        preconditions={},
        effects={"has_key": True},
        cost=10,
    )
    mock_synthesizer.synthesize_bridge_action.return_value = synth_bridge

    engine = GoapEngine(
        initial_actions=initial_actions,
        storage_path=temp_storage_path,
        synthesizer=mock_synthesizer,
        max_heal_attempts=3,
    )

    ws_kwargs: dict[str, Any] = {"has_key": False, "door_open": False}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"door_open": True})

    res = engine.run(initial_state, goal)
    assert res.success is True
    assert res.final_state.get("door_open") is True
    assert len(res.healed_gaps) == 1
    assert mock_synthesizer.synthesize_bridge_action.called


def test_engine_non_idempotent_action_failure(
    temp_storage_path: str,
) -> None:
    """Verifies non-idempotent action failure terminates without retries."""
    failing_action = Action(
        name="unsafe_write",
        preconditions={},
        effects={"written": True},
        cost=1,
    )

    engine = GoapEngine(
        initial_actions=[failing_action], storage_path=temp_storage_path
    )

    def failing_handler(state: WorldState) -> None:
        raise RuntimeError("External DB write failed")

    engine.register_handler(
        "unsafe_write", failing_handler, is_idempotent=False
    )

    ws_kwargs: dict[str, Any] = {"written": False}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"written": True})

    res = engine.run(initial_state, goal)
    assert res.success is False
    assert "Non-idempotent action" in (res.error_message or "")
