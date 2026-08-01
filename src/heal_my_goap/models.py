"""Domain models and exceptions for heal-my-goap."""

import uuid
from typing import Any

from goapauto.models.actions import Action
from goapauto.models.goal import Goal
from goapauto.models.goap_planner import Planner
from goapauto.models.worldstate import WorldState
from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "Action",
    "ExecutionResult",
    "Gap",
    "Goal",
    "HealMyGoapError",
    "NonIdempotentExecutionError",
    "Planner",
    "SandboxTimeoutError",
    "SynthesisError",
    "SynthesizedActionSchema",
    "WorldState",
]


class Gap(BaseModel):
    """Encapsulates an unsatisfied precondition gap in GOAP planning."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    missing_predicate: dict[str, Any]
    dependent_action_name: str | None = None
    closest_state: dict[str, Any] = Field(default_factory=dict)

    def is_satisfied_by_effects(self, effects: dict[str, Any]) -> bool:
        """Checks if missing predicates are satisfied by an effects dict.

        Args:
            effects: A dictionary mapping predicate names to target values.

        Returns:
            True if all missing predicates match values in effects, False
            otherwise.
        """
        for key, val in self.missing_predicate.items():
            if effects.get(key) != val:
                return False
        return True


class SynthesizedActionSchema(BaseModel):
    """Pydantic domain schema for structured LLM action synthesis validation."""

    name: str
    description: str
    preconditions: dict[str, Any]
    effects: dict[str, Any]
    cost: float = Field(default=10.0, ge=10.0)
    is_idempotent: bool = True
    code_payload: str | None = None


class ExecutionResult(BaseModel):
    """Domain container for GoapEngine execution results."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool
    final_state: WorldState
    executed_actions: list[Action] = Field(default_factory=list)
    healed_gaps: list[Gap] = Field(default_factory=list)
    error_message: str | None = None

    def is_successful(self) -> bool:
        """Determines if the GOAP execution achieved its goal.

        Returns:
            True if execution was successful, False otherwise.
        """
        return self.success


class HealMyGoapError(Exception):
    """Base exception for heal-my-goap object hierarchy."""


class NonIdempotentExecutionError(HealMyGoapError):
    """Raised when execution of a non-idempotent action fails."""


class SandboxTimeoutError(HealMyGoapError):
    """Raised when dynamic action sandbox execution times out."""


class SynthesisError(HealMyGoapError):
    """Raised when LLM action synthesis fails."""
