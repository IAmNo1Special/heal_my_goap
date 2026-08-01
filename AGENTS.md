---
kind: agents
---

# AGENTS.md — `heal-my-goap` Project Guidelines

## Overview

`heal-my-goap` is a production-grade Python library combining zero-token
symbolic Goal-Oriented Action Planning (GOAP) with LLM-powered self-healing
via OpenRouter.

- **Zero-Token Runtime Planning**: Local A\* search via `goapauto` pathfinding
  based on deterministic state preconditions and effects.
- **Diagnostic Gap Isolation**: Frontier node analysis and backward goal graph
  traversal to pinpoint exact missing state predicates (`Gap`).
- **OpenRouter Self-Healing**: Dynamic structured LLM synthesis
  (`LLMSynthesizer`) generating namespaced bridge actions with failure retry
  memory.
- **Process Sandboxing**: Hard-timeout subprocess code execution
  (`SandboxExecutor`) with AST safety checking.

## Architecture & Module Map

- `src/heal_my_goap/models.py`: Domain schemas (`Gap`, `ExecutionResult`,
  `SynthesizedActionSchema`) & re-exports (`WorldState`, `Action`, `Goal`,
  `Planner`).
- `src/heal_my_goap/gap_analyzer.py`: Abstract interface (`BaseGapAnalyzer`)
  & diagnostic isolation engine (`GapAnalyzer`).
- `src/heal_my_goap/synthesizer.py`: Abstract interface (`BaseSynthesizer`) &
  OpenRouter structured LLM synthesizer (`LLMSynthesizer`).
- `src/heal_my_goap/storage.py`: Abstract interface (`BaseActionStorage`) &
  SHA-256 canonical hash persistence (`ActionStorage`).
- `src/heal_my_goap/sandbox.py`: Abstract interface (`BaseSandboxExecutor`) &
  `multiprocessing.Process` execution sandbox (`SandboxExecutor`).
- `src/heal_my_goap/engine.py`: Orchestrator (`GoapEngine`) managing A\*
  planning, `WorldState` checkpointing, state rollback, and self-healing.
- `src/heal_my_goap/__init__.py`: Package public API re-exports.

## Tests & Examples

- `tests/`: Unit and integration suite. `test_coverage_edge_cases.py` holds
  failure-recovery and 100%-coverage edge cases.
- `examples/heal_my_goap/`: Full-stack demonstrations (`hospital_emergency.py`,
  `coding_agent.py`) exercising the complete engine pipeline.
- `examples/goapauto_foundations/`: Raw `goapauto` reference planners.
- `demo_actions.json`: Sample action definitions for self-healing demos.

## Environment & Tooling

- **Package Manager**: Use `uv`. Install dev dependencies via `uv add --dev`;
  run dev tools via `uv run --dev`.
- **Python Version**: `>=3.13,<3.14` (see `.python-version`).
- **Formatting & Style**: Strict 80-char line length (`line-length = 80`).
  Google Python Style Guide docstrings (`pydocstyle` convention `google`,
  Ruff rules `select = ["E", "F", "I", "UP", "D"]`).
- **Zero-Dependency CLI Execution**: Use `uvx` for standalone CLI utilities
  (e.g., `uvx ruff check . --fix`, `uvx ruff format .`).
- **Command Format**: Always use `uv run <command>` (e.g.,
  `uv run --dev pytest`), omitting `python` unless explicitly required.

## Quality Assurance & Verification

Before declaring work complete, agents MUST run and pass 100%:

1. **Static Type Checking**: `uv run --dev mypy src tests` (0 errors, strict).
1. **Linting & Formatting**: `uvx ruff check . --fix` &
   `uvx ruff format .` (0 violations; Google docstrings, 80-char limit).
1. **Pytest & Coverage**:
   `uv run --dev pytest -v -s --cov=heal_my_goap --cov-report=term-missing --cov-fail-under=100 -W error`
   (100% pass, 100% coverage, 0 warnings).

### Integration Tests & API Key

- Integration tests in `tests/test_integration.py` call the live OpenRouter
  API and are skipped when `OPENROUTER_API_KEY` is absent.
- On CI the key is injected via the `OPENROUTER_API_KEY` repository secret and
  passed to the test step as an environment variable.
- Local runs load the key from `.env` (see `.env.example`); `DEFAULT_LLM_MODEL`
  configures the target OpenRouter model.

## Operational Constraints & Safety

- **Google Docstrings Required**: All modules, classes, methods, and functions
  MUST include Google-style docstrings (`Args:`, `Returns:`, `Yields:`,
  `Raises:`).
- **Module-Only Imports (Section 2.2)**: Import packages and modules only
  (e.g., `import os.path`, `import heal_my_goap.models`). Never import
  individual classes or functions directly, except primitives from `typing`
  or `collections.abc`.
- **Exception Hierarchy (Section 2.4)**: All custom exception classes MUST
  inherit from `Exception` (never `BaseException`) and MUST end with the
  `Error` suffix (e.g., `SynthesisError`).
- **Executable Entry Points (Section 3.14)**: All executable scripts and
  examples MUST wrap main logic in `def main() -> None:` and invoke it under
  `if __name__ == "__main__": main()`.
- **Idiomatic Python Features**: Use implicit boolean evaluations
  (`if not seq:`) instead of explicit length checks. Never use mutable
  default arguments.
- **No Swallowing Exceptions**: Never mask errors or substitute dummy
  fallback states.
- **Process Isolation**: Never use `ThreadPoolExecutor` for dynamic code
  execution; always use `multiprocessing.Process` with `process.terminate()`
  on timeouts to avoid GIL deadlocks.
- **OOP Adherence**: Maintain abstract base classes (`ABC`) and dependency
  injection across all engine components.

## Dependency Notes

- `goapauto==0.2.5` (pinned): The upstream planner library. On Windows it
  reassigns `sys.stdout` at import, which breaks pytest capture; run tests
  with `-s` / `-p no:capture` and read coverage via
  `coverage report --show-missing`. See goapauto issue #43.

## Git Workflow Rules

### Atomic Commit Strategy

**NEVER** stage all changes at once. Always use manual staging for atomic
commits:

```bash
git add <specific-files>
git commit -m "type(scope): descriptive message"
```

### Commit Grouping Order

1. **chore(root)**: Project config (`pyproject.toml`, `uv.lock`,
   `.gitignore`, `.python-version`, `.env.example`, `src/heal_my_goap/py.typed`)
1. **docs(root)**: Documentation (`README.md`, `AGENTS.md`)
1. **feat(models)**: Core domain models first (dependency foundation)
1. **feat(<module>)**: Each module independently (`gap_analyzer`,
   `synthesizer`, `storage`, `sandbox`, `engine`)
1. **feat(agent)**: Package exports (`__init__.py`)
1. **test**: Test suite (all test files together)
1. **feat(examples)**: Example files
1. **feat(data)**: Data files (`demo_actions.json`)

### Conventional Commit Format

```
<type>(<scope>): <message>
```

Types: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `ci`,
`chore`, `revert`

Scopes: `root`, `models`, `gap_analyzer`, `synthesizer`, `storage`, `sandbox`,
`engine`, `agent`, `examples`, `data`

### Verification

```bash
git log --oneline  # Should show 11+ atomic commits, not 1 monolithic commit
```
