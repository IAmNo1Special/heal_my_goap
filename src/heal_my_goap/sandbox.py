"""AST safety visitor and process isolation sandbox executor."""

import ast
import multiprocessing
from abc import ABC, abstractmethod
from typing import Any, cast

from heal_my_goap.models import SandboxTimeoutError

FORBIDDEN_NAMES = {
    "os",
    "sys",
    "subprocess",
    "eval",
    "exec",
    "open",
    "__import__",
    "builtins",
}


class BaseSandboxExecutor(ABC):
    """Abstract interface for code execution sandboxes."""

    @abstractmethod
    def execute_code(
        self,
        code_str: str,
        context_globals: dict[str, Any] | None = None,
        timeout_seconds: float = 5.0,
    ) -> dict[str, Any]:
        """Safely executes Python code within sandbox isolation.

        Args:
            code_str: Python code string to execute.
            context_globals: Optional dict of global execution variables.
            timeout_seconds: Hard timeout in seconds.

        Returns:
            Dict containing local variables resulting from execution.

        Raises:
            SandboxTimeoutError: If execution exceeds timeout_seconds.
            ValueError: If code violates safety AST constraints or errors.
        """


class ASTSafetyVisitor(ast.NodeVisitor):
    """AST visitor to verify safe syntax before execution."""

    def visit_Import(self, node: ast.Import) -> None:
        """Validates import statements against forbidden names.

        Args:
            node: AST import node.

        Raises:
            ValueError: If an import statement targets a forbidden module.
        """
        for alias in node.names:
            if alias.name.split(".")[0] in FORBIDDEN_NAMES:
                raise ValueError(f"Forbidden AST node: import {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Validates from-import statements against forbidden names.

        Args:
            node: AST import-from node.

        Raises:
            ValueError: If a from-import statement targets a forbidden module.
        """
        if node.module and node.module.split(".")[0] in FORBIDDEN_NAMES:
            raise ValueError(
                f"Forbidden AST node: from {node.module} import ..."
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Validates function call nodes against forbidden functions.

        Args:
            node: AST call node.

        Raises:
            ValueError: If a call targets a forbidden function.
        """
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAMES:
            raise ValueError(f"Forbidden function: {node.func.id}")
        self.generic_visit(node)


def _sandbox_process_target(
    code_str: str,
    context_globals: dict[str, Any] | None,
    queue: Any,
) -> None:
    """Target function executed inside isolated subprocess.

    Args:
        code_str: Code payload string.
        context_globals: Optional execution context globals.
        queue: Multiprocessing inter-process communication queue.
    """
    try:
        executor = SandboxExecutor()
        local_vars = executor._execute_sync(code_str, context_globals)
        queue.put(("success", local_vars))
    except Exception as exc:
        queue.put(("error", str(exc)))


class SandboxExecutor(BaseSandboxExecutor):
    """Sandbox executor with AST validation and hard timeout termination."""

    def validate_ast(self, code_str: str) -> ast.AST:
        """Parses and validates AST safety for code string.

        Args:
            code_str: Python code string.

        Returns:
            Parsed AST module.

        Raises:
            ValueError: If AST contains unsafe nodes or calls.
        """
        parsed = ast.parse(code_str)
        visitor = ASTSafetyVisitor()
        visitor.visit(parsed)
        return parsed

    def _execute_sync(
        self, code_str: str, context_globals: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Synchronously executes code within safe builtins dict.

        Args:
            code_str: Python code string.
            context_globals: Global variable definitions.

        Returns:
            Resulting local variables dictionary.
        """
        self.validate_ast(code_str)
        safe_builtins = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "range": range,
            "set": set,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "True": True,
            "False": False,
            "None": None,
        }
        exec_globals = {"__builtins__": safe_builtins}
        if context_globals:
            exec_globals.update(context_globals)
        local_vars: dict[str, Any] = {}
        exec(code_str, exec_globals, local_vars)
        return local_vars

    def execute_code(
        self,
        code_str: str,
        context_globals: dict[str, Any] | None = None,
        timeout_seconds: float = 5.0,
    ) -> dict[str, Any]:
        """Executes code in isolated subprocess with timeout enforcement.

        Args:
            code_str: Code string to execute.
            context_globals: Optional globals dictionary.
            timeout_seconds: Timeout limit in seconds.

        Returns:
            Dictionary of resulting local variables.

        Raises:
            SandboxTimeoutError: If execution exceeds timeout threshold.
            ValueError: If code execution fails or violates AST rules.
        """
        self.validate_ast(code_str)
        ctx = multiprocessing.get_context("spawn")
        queue = ctx.Queue()
        process = ctx.Process(
            target=_sandbox_process_target,
            args=(code_str, context_globals, queue),
        )
        process.start()
        process.join(timeout=timeout_seconds)

        if process.is_alive():
            process.terminate()
            process.join()
            raise SandboxTimeoutError(
                f"Code execution timed out after {timeout_seconds} seconds."
            )

        if not queue.empty():
            status, payload = queue.get()
            if status == "success":
                return cast(dict[str, Any], payload)
            if status == "error":
                raise ValueError(payload)

        return {}
