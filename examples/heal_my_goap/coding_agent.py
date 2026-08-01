"""Coding Agent Build Pipeline with heal-my-goap self-healing.

This scenario demonstrates the full heal-my-goap pipeline in a software
development context:
- Symbolic GOAP planning for build pipeline stages
- Gap isolation when preconditions are missing
- LLM-powered synthesis of novel development actions
- Sandbox execution of generated code transformations

The coding agent must navigate a complex workflow: fix syntax errors,
write implementation, run code review, build, test, optimize, and
document - synthesizing new actions when the standard workflow breaks.

Demonstrates goapauto 0.2.3+ features:
- Positional args for Set/Increment/Decrement effects
- WorldState.update_state properly applies effects
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from goapauto.models.actions import Increment, Set

from heal_my_goap import Action, Goal, GoapEngine, WorldState


def main() -> None:
    """Run the coding agent build pipeline self-healing demonstration.

    Simulates an AI coding agent implementing a feature through a
    development lifecycle. The baseline action set handles the happy
    path, but scenarios with unusual error combinations trigger the
    self-healing pipeline.
    """
    print("\n" + "=" * 70)
    print("CODING AGENT BUILD PIPELINE - HEALMYGOAP SCENARIO")
    print("=" * 70)

    baseline_actions: list[Action] = [
        Action(
            name="fix_syntax_errors",
            preconditions={"has_syntax_errors": True},
            effects={
                "has_syntax_errors": Set(False),
                "code_written": True,
            },
            cost=8.0,
        ),
        Action(
            name="write_implementation",
            preconditions={
                "requirements_read": True,
                "code_written": False,
            },
            effects={"code_written": Set(True)},
            cost=10.0,
        ),
        Action(
            name="run_code_review",
            preconditions={
                "code_written": True,
                "code_reviewed": False,
            },
            effects={
                "code_reviewed": Set(True),
                "lint_clean": Set(True),
            },
            cost=3.0,
        ),
        Action(
            name="build_project",
            preconditions={
                "code_written": True,
                "code_reviewed": True,
                "build_success": False,
            },
            effects={"build_success": Set(True)},
            cost=5.0,
        ),
        Action(
            name="run_tests",
            preconditions={"build_success": True},
            effects={
                "tests_passing": Set(True),
                "coverage_pct": Increment(30),
            },
            cost=4.0,
        ),
        Action(
            name="fix_failing_tests",
            preconditions={
                "build_success": True,
                "tests_passing": False,
            },
            effects={"tests_passing": Set(True)},
            cost=15.0,
        ),
        Action(
            name="add_more_tests",
            preconditions={
                "tests_passing": True,
                "coverage_pct": lambda v: v < 80,
            },
            effects={
                "coverage_pct": Increment(20),
            },
            cost=7.0,
        ),
        Action(
            name="optimize_performance",
            preconditions={
                "tests_passing": True,
                "complexity_score": lambda v: v > 5,
            },
            effects={
                "complexity_score": Increment(-3),
            },
            cost=12.0,
        ),
        Action(
            name="write_documentation",
            preconditions={
                "tests_passing": True,
                "documentation_written": False,
            },
            effects={"documentation_written": Set(True)},
            cost=6.0,
        ),
    ]

    scenarios: list[tuple[str, WorldState, Goal]] = [
        (
            "Full Pipeline (Happy Path)",
            WorldState(
                requirements_read=True,
                code_written=False,
                code_reviewed=False,
                build_success=False,
                tests_passing=False,
                coverage_pct=0,
                complexity_score=10,
                lint_clean=False,
                documentation_written=False,
                has_syntax_errors=False,
            ),
            Goal(
                target_state={
                    "code_written": True,
                    "build_success": True,
                    "tests_passing": True,
                    "coverage_pct": 80,
                    "complexity_score": 5,
                    "documentation_written": True,
                },
                priority=1,
                name="Ship Feature",
            ),
        ),
        (
            "Broken Build (missing fix_tests action)",
            WorldState(
                requirements_read=True,
                code_written=True,
                code_reviewed=True,
                build_success=False,
                tests_passing=False,
                coverage_pct=0,
                complexity_score=10,
                lint_clean=True,
                documentation_written=False,
                has_syntax_errors=False,
            ),
            Goal(
                target_state={
                    "build_success": True,
                    "tests_passing": True,
                },
                priority=1,
                name="Fix and Ship",
            ),
        ),
        (
            "Lint Failure (no lint fix action available)",
            WorldState(
                requirements_read=True,
                code_written=True,
                code_reviewed=False,
                build_success=True,
                tests_passing=False,
                coverage_pct=0,
                complexity_score=10,
                lint_clean=False,
                documentation_written=False,
                has_syntax_errors=False,
            ),
            Goal(
                target_state={"lint_clean": True},
                priority=2,
                name="Clean Lint",
            ),
        ),
        (
            "Deep Cascade (multiple gaps)",
            WorldState(
                requirements_read=False,
                code_written=False,
                code_reviewed=False,
                build_success=False,
                tests_passing=False,
                coverage_pct=0,
                complexity_score=10,
                lint_clean=False,
                documentation_written=False,
                has_syntax_errors=True,
            ),
            Goal(
                target_state={
                    "tests_passing": True,
                    "coverage_pct": 80,
                    "lint_clean": True,
                    "documentation_written": True,
                },
                priority=1,
                name="Complete Cleanup",
            ),
        ),
    ]

    engine = GoapEngine(
        initial_actions=baseline_actions,
        storage_path=".goap_coding_actions.json",
        max_heal_attempts=3,
    )

    total = len(scenarios)
    for i, (label, state, goal) in enumerate(scenarios, 1):
        print(f"\n--- [{i}/{total}] {label} ---")
        print(f"Initial: {state.to_dict()}")
        print(f"Goal:    {goal.target_state}")

        result = engine.run(state, goal)

        print(f"\nResult: {'SUCCESS' if result.success else 'FAILURE'}")
        if result.executed_actions:
            print("Executed Actions:")
            for act in result.executed_actions:
                print(f"  - {act.name} (cost: {act.cost})")

        if result.healed_gaps:
            print("Healed Gaps (synthesized bridge actions):")
            for gap in result.healed_gaps:
                print(
                    f"  - Missing: {gap.missing_predicate}"
                    f" (needed by: {gap.dependent_action_name})"
                )

        print(f"Final State: {result.final_state.to_dict()}")

    print("\n" + "=" * 70)
    print("SCENARIO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
