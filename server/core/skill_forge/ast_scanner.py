import ast

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Ok, Result
from server.core.skill_forge.contracts import MAX_SOURCE_CHARS

ALLOWED_MODULES = frozenset({
    "math", "statistics", "decimal", "fractions", "datetime", "re", "json", "itertools",
    "functools", "collections", "unicodedata", "typing",
})
FORBIDDEN_CALLS = frozenset({
    "eval", "exec", "compile", "open", "__import__", "input", "breakpoint", "getattr", "setattr",
    "delattr", "globals", "locals", "vars", "memoryview", "exit", "quit", "help", "dir", "type",
    "super", "object", "classmethod", "staticmethod", "property",
})
FORBIDDEN_NODES = (
    ast.ClassDef, ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith, ast.Global, ast.Nonlocal,
    ast.Delete,
)
FORBIDDEN_ATTRIBUTES = frozenset({"format", "format_map", "mro", "gi_frame", "gi_code", "cr_frame", "f_globals", "f_locals", "f_builtins"})
MAX_NODES = 4_000
ENTRY = "run"


def _import_roots(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name.split(".")[0] for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        if node.level or any(alias.name == "*" for alias in node.names):
            return ["*"]
        return [(node.module or "").split(".")[0]]
    return []


def _violation(node: ast.AST) -> str:
    for root in _import_roots(node):
        if root not in ALLOWED_MODULES:
            return "cortex.forge.forbidden_import"
    if isinstance(node, FORBIDDEN_NODES):
        return "cortex.forge.forbidden_syntax"
    if isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr in FORBIDDEN_ATTRIBUTES):
        return "cortex.forge.forbidden_syntax"
    if isinstance(node, ast.Name) and node.id.startswith("__"):
        return "cortex.forge.forbidden_syntax"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
        return "cortex.forge.forbidden_call"
    if isinstance(node, ast.Name) and node.id in FORBIDDEN_CALLS and isinstance(node.ctx, ast.Load):
        return "cortex.forge.forbidden_call"
    return ""


def _has_entry(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.FunctionDef) and node.name == ENTRY and len(node.args.args) == 1
        and not node.args.vararg and not node.args.kwarg and not node.args.kwonlyargs
        for node in tree.body
    )


def scan_source(source: str) -> Result[ast.Module, CortexFailure]:
    if not isinstance(source, str) or not source.strip() or len(source) > MAX_SOURCE_CHARS:
        return fail("cortex.forge.source_too_large")
    try:
        tree = ast.parse(source, mode="exec")
    except (SyntaxError, ValueError, RecursionError):
        return fail("cortex.forge.syntax")
    count = 0
    for node in ast.walk(tree):
        count += 1
        if count > MAX_NODES:
            return fail("cortex.forge.source_too_large")
        code = _violation(node)
        if code:
            return fail(code, line=getattr(node, "lineno", 0))
    if not _has_entry(tree):
        return fail("cortex.forge.missing_entry")
    return Ok(tree)
