"""Tests for heal_my_goap domain models and custom exceptions."""

from typing import Any, cast

import pytest
from pydantic import ValidationError

from heal_my_goap.models import (
    Action,
    ExecutionResult,
    Gap,
    Goal,
    NonIdempotentExecutionError,
    Planner,
    SandboxTimeoutError,
    SynthesisError,
    SynthesizedActionSchema,
    WorldState,
)


def test_reexported_models() -> None:
    """Verifies re-exported goapauto models."""
    ws_kwargs: dict[str, Any] = {"has_key": True}
    ws = WorldState(**ws_kwargs)
    assert ws.get("has_key") is True

    action = Action(
        name="open_door",
        preconditions={"has_key": True},
        effects={"door_open": True},
        cost=1,
    )
    assert action.name == "open_door"

    goal = Goal(target_state={"door_open": True})
    assert goal.target_state == {"door_open": True}

    planner = Planner(actions_list=cast(Any, [action]))
    assert planner is not None


def test_gap_model() -> None:
    """Verifies Gap model initialization and attributes."""
    gap = Gap(
        missing_predicate={"has_key": True},
        dependent_action_name="open_door",
        closest_state={"has_key": False},
    )
    assert gap.missing_predicate == {"has_key": True}
    assert gap.dependent_action_name == "open_door"
    assert isinstance(gap.id, str) and len(gap.id) > 0


def test_synthesized_action_schema_cost_constraint() -> None:
    """Verifies cost >= 10 validation constraint on SynthesizedActionSchema."""
    valid_schema = SynthesizedActionSchema(
        name="synth_find_key",
        description="Find key in drawer",
        preconditions={"in_room": True},
        effects={"has_key": True},
        cost=10.0,
        is_idempotent=True,
    )
    assert valid_schema.cost == 10.0

    with pytest.raises(ValidationError):
        SynthesizedActionSchema(
            name="synth_free_magic",
            description="Magic action",
            preconditions={},
            effects={"has_key": True},
            cost=1.0,
        )


def test_execution_result_and_exceptions() -> None:
    """Verifies ExecutionResult container and exception inheritance."""
    ws_kwargs: dict[str, Any] = {"door_open": True}
    ws = WorldState(**ws_kwargs)
    res = ExecutionResult(
        success=True,
        final_state=ws,
        executed_actions=[],
        healed_gaps=[],
    )
    assert res.success is True
    assert res.error_message is None
    assert res.is_successful() is True

    res_fail = ExecutionResult(
        success=False,
        final_state=ws,
    )
    assert res_fail.is_successful() is False

    assert issubclass(NonIdempotentExecutionError, Exception)
    assert issubclass(SandboxTimeoutError, Exception)
    assert issubclass(SynthesisError, Exception)
