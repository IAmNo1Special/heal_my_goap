"""Tests for sandbox code execution and safety checks."""

import pytest

from heal_my_goap.models import SandboxTimeoutError
from heal_my_goap.sandbox import SandboxExecutor


def test_sandbox_safe_code_execution() -> None:
    """Verifies safe Python code execution in sandbox."""
    executor = SandboxExecutor()
    code = "x = 10\ny = 20\nresult = x + y\n"
    local_vars = executor.execute_code(code)
    assert local_vars.get("result") == 30


def test_sandbox_blocked_imports() -> None:
    """Verifies AST validation blocks os module import."""
    executor = SandboxExecutor()
    code = "import os"
    with pytest.raises(ValueError, match="Forbidden AST node"):
        executor.execute_code(code)


def test_sandbox_blocked_sys() -> None:
    """Verifies AST validation blocks sys module import."""
    executor = SandboxExecutor()
    code = "import sys"
    with pytest.raises(ValueError, match="Forbidden AST node"):
        executor.execute_code(code)


def test_sandbox_blocked_builtins() -> None:
    """Verifies AST validation blocks dangerous builtins like eval."""
    executor = SandboxExecutor()
    code = "eval('1 + 1')"
    with pytest.raises(ValueError, match="Forbidden function"):
        executor.execute_code(code)


def test_sandbox_timeout_enforcement() -> None:
    """Verifies hard timeout enforcement on infinite loop execution."""
    executor = SandboxExecutor()
    infinite_loop_code = "while True:\n    pass\n"
    with pytest.raises(SandboxTimeoutError):
        executor.execute_code(infinite_loop_code, timeout_seconds=0.5)
