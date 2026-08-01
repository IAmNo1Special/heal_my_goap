"""Basic GOAP example demonstrating deterministic planning."""

from heal_my_goap import Action, Goal, Planner, WorldState


def main() -> None:
    """Executes basic GOAP planning example."""
    initial_state = WorldState(in_room=True, has_key=True, door_open=False)

    open_door = Action(
        name="open_door",
        preconditions={"has_key": True, "in_room": True},
        effects={"door_open": True},
        cost=1.0,
    )

    goal = Goal(target_state={"door_open": True})

    planner = Planner(actions_list=[open_door])
    result = planner.generate_plan(initial_state, goal)

    plan_steps = result.plan if hasattr(result, "plan") else result
    print("🎯 Basic GOAP Plan Generated:")
    for step in plan_steps:
        print(f" -> {step}")


if __name__ == "__main__":
    main()
