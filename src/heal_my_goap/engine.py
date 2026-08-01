"""GOAP execution engine with state rollback and LLM self-healing."""

import copy
from collections.abc import Callable
from typing import Any, cast

from heal_my_goap.gap_analyzer import BaseGapAnalyzer, GapAnalyzer
from heal_my_goap.models import (
    Action,
    ExecutionResult,
    Gap,
    Goal,
    Planner,
    WorldState,
)
from heal_my_goap.sandbox import BaseSandboxExecutor, SandboxExecutor
from heal_my_goap.storage import ActionStorage, BaseActionStorage
from heal_my_goap.synthesizer import BaseSynthesizer, LLMSynthesizer


class GoapEngine:
    """Orchestration harness for GOAP execution, rollback, and self-healing.

    Attributes:
        actions_dict: Dictionary mapping action names to Action instances.
        storage: Persistence handler for synthesized actions.
        synthesizer: LLM synthesis engine for bridging unsatisfied gaps.
        gap_analyzer: Diagnostic engine for identifying missing state gaps.
        sandbox: Isolated subprocess code executor.
        max_heal_attempts: Maximum self-healing retry iterations allowed.
        handlers: Runtime action execution handlers.
        idempotency_map: Idempotency flags per action name.
        failed_attempts: List of failed actions encountered during execution.
    """

    def __init__(
        self,
        initial_actions: list[Action],
        storage: BaseActionStorage | str | None = None,
        synthesizer: BaseSynthesizer | None = None,
        gap_analyzer: BaseGapAnalyzer | None = None,
        sandbox: BaseSandboxExecutor | None = None,
        max_heal_attempts: int = 3,
        storage_path: str | None = None,
    ) -> None:
        """Initializes GoapEngine.

        Args:
            initial_actions: Baseline deterministic GOAP actions.
            storage: Storage instance or path for synthesized actions.
            synthesizer: Optional custom synthesizer instance.
            gap_analyzer: Optional custom gap analyzer instance.
            sandbox: Optional custom sandbox executor instance.
            max_heal_attempts: Maximum allowed self-healing retries.
            storage_path: Optional storage path override string.
        """
        self.actions_dict: dict[str, Action] = {
            a.name: a for a in initial_actions
        }

        storage_val = storage_path or storage or ".goap_actions.json"
        self.storage: BaseActionStorage = (
            ActionStorage(file_path=storage_val)
            if isinstance(storage_val, str)
            else storage_val
        )
        self.synthesizer: BaseSynthesizer = synthesizer or LLMSynthesizer()
        self.gap_analyzer: BaseGapAnalyzer = gap_analyzer or GapAnalyzer()
        self.sandbox: BaseSandboxExecutor = sandbox or SandboxExecutor()
        self.max_heal_attempts = max_heal_attempts

        self.handlers: dict[str, Callable[[WorldState], None]] = {}
        self.idempotency_map: dict[str, bool] = {}
        self.failed_attempts: list[Action] = []

        for action in self.storage.load_actions():
            self.actions_dict[action.name] = action

    def register_handler(
        self,
        action_name: str,
        handler_func: Callable[[WorldState], None],
        is_idempotent: bool = True,
    ) -> None:
        """Registers a runtime handler function for an action.

        Args:
            action_name: Name of target action.
            handler_func: Execution callback function taking WorldState.
            is_idempotent: Whether the action can be retried safely.
        """
        self.handlers[action_name] = handler_func
        self.idempotency_map[action_name] = is_idempotent

    def run(self, initial_state: WorldState, goal: Goal) -> ExecutionResult:
        """Executes GOAP planning loop with self-healing retry logic.

        Args:
            initial_state: Starting world state.
            goal: Target GOAP goal state.

        Returns:
            An ExecutionResult indicating success status and final state.
        """
        current_state = copy.deepcopy(initial_state)
        executed_actions: list[Action] = []
        healed_gaps: list[Gap] = []

        heal_attempts = 0

        while heal_attempts <= self.max_heal_attempts:
            available_actions = list(self.actions_dict.values())
            planner = Planner(actions_list=cast(Any, available_actions))
            plan_result = planner.generate_plan(current_state, goal)

            plan_actions: list[Any] = []
            if plan_result and hasattr(plan_result, "plan"):
                raw_plan = getattr(plan_result, "plan", None)
                if raw_plan is not None:
                    plan_actions = list(raw_plan)
            elif isinstance(plan_result, list):
                plan_actions = list(plan_result)

            if plan_actions:
                execution_successful = True
                for item in plan_actions:
                    action_obj = (
                        self.actions_dict.get(item)
                        if isinstance(item, str)
                        else item
                    )
                    if not action_obj:
                        continue

                    is_idempotent = self.idempotency_map.get(
                        action_obj.name, True
                    )
                    state_checkpoint = copy.deepcopy(current_state)

                    try:
                        if action_obj.name in self.handlers:
                            self.handlers[action_obj.name](current_state)

                        if hasattr(current_state, "update_state"):
                            current_state.update_state(action_obj.effects)
                        for k, v in action_obj.effects.items():
                            setattr(current_state, k, v)

                        executed_actions.append(action_obj)
                    except Exception as exc:
                        execution_successful = False
                        if not is_idempotent:
                            err_msg = (
                                f"Non-idempotent action '{action_obj.name}' "
                                f"failed: {exc!s}"
                            )
                            return ExecutionResult(
                                success=False,
                                final_state=state_checkpoint,
                                executed_actions=executed_actions,
                                healed_gaps=healed_gaps,
                                error_message=err_msg,
                            )
                        current_state = state_checkpoint
                        self.failed_attempts.append(action_obj)
                        break

                if execution_successful:
                    curr_dict = (
                        current_state.to_dict()
                        if hasattr(current_state, "to_dict")
                        else dict(current_state)
                    )
                    goal_satisfied = True
                    for gk, gv in goal.target_state.items():
                        if curr_dict.get(gk) != gv:
                            goal_satisfied = False
                            break

                    if goal_satisfied:
                        return ExecutionResult(
                            success=True,
                            final_state=current_state,
                            executed_actions=executed_actions,
                            healed_gaps=healed_gaps,
                        )

            gap = self.gap_analyzer.analyze(
                current_state, goal, available_actions
            )
            healed_gaps.append(gap)

            bridge_action = self.synthesizer.synthesize_bridge_action(
                gap, available_actions, self.failed_attempts
            )

            self.storage.save_action(bridge_action)
            self.actions_dict[bridge_action.name] = bridge_action

            heal_attempts += 1

        err_msg = (
            f"Reached maximum heal attempts ({self.max_heal_attempts}) "
            "without reaching goal."
        )
        return ExecutionResult(
            success=False,
            final_state=current_state,
            executed_actions=executed_actions,
            healed_gaps=healed_gaps,
            error_message=err_msg,
        )
