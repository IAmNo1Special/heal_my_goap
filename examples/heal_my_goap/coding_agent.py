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
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

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
                "has_syntax_errors": False,
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
            effects={"code_written": True},
            cost=10.0,
        ),
        Action(
            name="run_code_review",
            preconditions={
                "code_written": True,
                "code_reviewed": False,
            },
            effects={
                "code_reviewed": True,
                "lint_clean": True,
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
            effects={"build_success": True},
            cost=5.0,
        ),
        Action(
            name="run_tests",
            preconditions={"build_success": True},
            effects={"tests_passing": True},
            cost=4.0,
        ),
        Action(
            name="fix_failing_tests",
            preconditions={
                "build_success": True,
                "tests_passing": False,
            },
            effects={"tests_passing": True},
            cost=15.0,
        ),
        Action(
            name="write_documentation",
            preconditions={
                "tests_passing": True,
                "documentation_written": False,
            },
            effects={"documentation_written": True},
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
                lint_clean=False,
                documentation_written=False,
                has_syntax_errors=False,
            ),
            Goal(
                target_state={
                    "code_written": True,
                    "build_success": True,
                    "tests_passing": True,
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
                lint_clean=False,
                documentation_written=False,
                has_syntax_errors=True,
            ),
            Goal(
                target_state={
                    "tests_passing": True,
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
