"""Tests for GoapEngine orchestration harness."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from heal_my_goap.engine import GoapEngine
from heal_my_goap.models import Action, Goal, WorldState
from heal_my_goap.storage import ActionStorage
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


def test_engine_loads_actions_from_storage(tmp_path: Any) -> None:
    """Verifies engine loads persisted actions from storage at init."""
    storage_file = str(tmp_path / "preloaded.json")
    storage = ActionStorage(file_path=storage_file)
    preloaded = Action(
        name="preloaded_action",
        preconditions={"needed": True},
        effects={"done": True},
        cost=1,
    )
    storage.save_action(preloaded)

    engine = GoapEngine(initial_actions=[], storage=storage)
    assert "preloaded_action" in engine.actions_dict


def test_engine_accepts_plain_list_plan(tmp_path: Any) -> None:
    """Verifies engine handles planner returning a plain list plan."""
    action = Action(
        name="open_door",
        preconditions={},
        effects={"door_open": True},
        cost=1,
    )
    engine = GoapEngine(
        initial_actions=[action], storage_path=str(tmp_path / "list.json")
    )

    ws_kwargs: dict[str, Any] = {"door_open": False}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"door_open": True})

    with patch("heal_my_goap.engine.Planner") as mock_planner:
        mock_planner.return_value.generate_plan.return_value = ["open_door"]
        res = engine.run(initial_state, goal)

    assert res.success is True
    assert res.final_state.get("door_open") is True


def test_engine_skips_unknown_plan_action(tmp_path: Any) -> None:
    """Verifies engine ignores plan actions missing from action registry."""
    action = Action(
        name="open_door",
        preconditions={},
        effects={"door_open": True},
        cost=1,
    )
    engine = GoapEngine(
        initial_actions=[action], storage_path=str(tmp_path / "unknown.json")
    )

    ws_kwargs: dict[str, Any] = {"door_open": False}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"door_open": True})

    with patch("heal_my_goap.engine.Planner") as mock_planner:
        mock_planner.return_value.generate_plan.return_value = [
            "ghost_action",
            "open_door",
        ]
        res = engine.run(initial_state, goal)

    assert res.success is True
    assert res.final_state.get("door_open") is True


def test_engine_execution_success_but_goal_not_satisfied(tmp_path: Any) -> None:
    """Verifies engine handles successful execution that misses the goal."""
    action = Action(
        name="set_value",
        preconditions={},
        effects={"value": 1},
        cost=1,
    )
    mock_synthesizer = MagicMock(spec=LLMSynthesizer)
    mock_synthesizer.synthesize_bridge_action.return_value = Action(
        name="synth_set_other",
        preconditions={},
        effects={"other": True},
        cost=10,
    )
    engine = GoapEngine(
        initial_actions=[action],
        storage_path=str(tmp_path / "missgoal.json"),
        synthesizer=mock_synthesizer,
        max_heal_attempts=0,
    )

    ws_kwargs: dict[str, Any] = {"value": 0}
    initial_state = WorldState(**ws_kwargs)
    goal = Goal(target_state={"value": 1, "other": True})

    with patch("heal_my_goap.engine.Planner") as mock_planner:
        mock_planner.return_value.generate_plan.return_value = ["set_value"]
        res = engine.run(initial_state, goal)

    assert res.success is False
