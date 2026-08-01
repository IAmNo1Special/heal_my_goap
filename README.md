# heal-my-goap

A lightweight, production-ready Goal-Oriented Action Planning (GOAP) library with LLM-powered self-healing.

## Installation

```bash
uv add heal-my-goap
```

## Features

- **Deterministic A* Planning*\*: High performance, zero token runtime pathfinding via `goapauto`.
- **Frontier Gap Isolation**: Precise missing precondition diagnostics when no plan is found.
- **Structured OpenRouter LLM Synthesis**: Auto-generate bridge actions to heal missing predicate links.
- **Canonical Hash Action Storage**: Local JSON action persistence.
- **Safety Controls**: Restricted sandbox code execution timeout, state mutation rollbacks, and idempotency checks.
