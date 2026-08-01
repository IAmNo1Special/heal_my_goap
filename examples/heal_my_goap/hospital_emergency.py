"""Hospital Emergency Response System with heal-my-goap self-healing.

This scenario demonstrates the full heal-my-goap pipeline:
- Zero-token symbolic GOAP planning via goapauto
- Gap isolation when plans are incomplete
- LLM-powered self-healing via LLMSynthesizer
- Sandbox execution of synthesized bridge actions

The robot medic must navigate a hospital, treat patients with limited
medicine, handle equipment failures, and respond to emergencies - all
while the system automatically synthesizes new actions when the existing
action set is insufficient.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from heal_my_goap import Action, Goal, GoapEngine, WorldState


def main() -> None:
    """Run the hospital emergency response self-healing demonstration.

    Simulates a robot medic in a hospital setting. The initial action
    set cannot handle all scenarios - the engine must synthesize bridge
    actions when critical preconditions are missing.
    """
    print("\n" + "=" * 70)
    print("HOSPITAL EMERGENCY RESPONSE - HEALMYGOAP SCENARIO")
    print("=" * 70)

    baseline_actions: list[Action] = [
        Action(
            name="navigate_to_location",
            preconditions={"patient_present": True},
            effects={"location": "treatment_room"},
            cost=3.0,
        ),
        Action(
            name="treat_patient",
            preconditions={
                "location": "treatment_room",
                "medicine_current": 0,
            },
            effects={"patient_present": True},
            cost=2.0,
        ),
        Action(
            name="restock_medicine",
            preconditions={"location": "central_hub"},
            effects={"medicine_current": 100},
            cost=5.0,
        ),
        Action(
            name="unlock_door",
            preconditions={"has_keycard": True},
            effects={"door_locked": False},
            cost=1.0,
        ),
    ]

    goals_and_states: list[tuple[str, WorldState, Goal]] = [
        (
            "Treat Patient (has medicine)",
            WorldState(
                location="central_hub",
                medicine_current=50,
                power_stable=True,
                equipment_operational=True,
                patient_present=False,
                door_locked=False,
            ),
            Goal(
                target_state={
                    "location": "treatment_room",
                    "medicine_current": 50,
                    "patient_present": True,
                },
                priority=1,
                name="Treat Patient",
            ),
        ),
        (
            "Unlock Door (missing keycard)",
            WorldState(
                location="central_hub",
                medicine_current=0,
                power_stable=True,
                equipment_operational=True,
                patient_present=False,
                door_locked=True,
            ),
            Goal(
                target_state={"door_locked": False},
                priority=2,
                name="Unlock Door",
            ),
        ),
        (
            "Restore Power (equipment failure cascade)",
            WorldState(
                location="central_hub",
                medicine_current=0,
                power_stable=False,
                equipment_operational=False,
                patient_present=False,
                door_locked=False,
            ),
            Goal(
                target_state={
                    "power_stable": True,
                    "equipment_operational": True,
                },
                priority=1,
                name="Restore Power",
            ),
        ),
    ]

    engine = GoapEngine(
        initial_actions=baseline_actions,
        storage_path=".goap_hospital_actions.json",
        max_heal_attempts=3,
    )

    total = len(goals_and_states)
    for i, (label, state, goal) in enumerate(goals_and_states, 1):
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
