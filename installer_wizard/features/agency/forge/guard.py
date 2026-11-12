import ast
import importlib
import re
from types import ModuleType

CODE_LIMIT = 40000
NAME = re.compile(r"[a-z][a-z0-9_]{2,39}")
ALLOWED_IMPORTS = frozenset({
    "math", "cmath", "statistics", "fractions", "decimal", "datetime", "calendar", "re", "json", "itertools",
    "functools", "collections", "string", "unicodedata", "operator", "bisect", "heapq", "textwrap", "difflib",
    "hashlib", "hmac", "base64", "binascii", "html", "ipaddress", "uuid", "zlib", "colorsys", "dataclasses",
    "enum", "typing", "random", "secrets",
})
FORBIDDEN = frozenset({
    "open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "input", "breakpoint", "getattr",
    "setattr", "delattr", "hasattr", "memoryview", "exit", "quit", "help", "dir", "type", "object", "super",
    "classmethod", "staticmethod", "property", "id", "print",
})

INTROSPECTION = frozenset({
    "format", "format_map", "Formatter", "vformat", "get_field", "attrgetter", "methodcaller", "mro", "gi_frame",
    "gi_code", "cr_frame", "cr_code", "ag_frame", "tb_frame", "tb_next", "f_globals", "f_locals", "f_builtins",
    "f_back", "f_code", "co_code", "func_globals", "modules", "builtins", "loader", "spec", "system", "popen",
})


def _reachable_modules() -> frozenset[str]:
    names: set[str] = set()
    seen: set[str] = set()
    queue = [importlib.import_module(m) for m in sorted(ALLOWED_IMPORTS)]
    while queue:
        module = queue.pop()
        if module.__name__ in seen:
            continue
        seen.add(module.__name__)
        for key, value in vars(module).items():
            if not isinstance(value, ModuleType):
                continue
            if value.__name__.split(".")[0] in ALLOWED_IMPORTS:
                queue.append(value)
            else:
                names.add(key)
    return frozenset(names)


BLOCKED_ATTRIBUTES = FORBIDDEN | INTROSPECTION | _reachable_modules()


class ForgeRejected(ValueError):
    pass


def _module(name: str | None) -> str:
    return (name or "").split(".")[0]


def _inspect(node: ast.AST) -> None:
    if isinstance(node, ast.Import):
        bad = [a.name for a in node.names if _module(a.name) not in ALLOWED_IMPORTS]
        if bad:
            raise ForgeRejected(f"module not allowed: {bad[0]}")
    elif isinstance(node, ast.ImportFrom):
        if node.level or _module(node.module) not in ALLOWED_IMPORTS:
            raise ForgeRejected(f"module not allowed: {node.module}")
        if any(a.name == "*" or a.name.startswith("_") for a in node.names):
            raise ForgeRejected("wildcard or private import not allowed")
    elif isinstance(node, ast.Name) and (node.id in FORBIDDEN or node.id.startswith("__")):
        raise ForgeRejected(f"name not allowed: {node.id}")
    elif isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr in BLOCKED_ATTRIBUTES):
        raise ForgeRejected(f"attribute not allowed: {node.attr}")
    elif isinstance(node, (ast.Global, ast.Nonlocal, ast.AsyncFunctionDef, ast.Await, ast.Yield, ast.YieldFrom)):
        raise ForgeRejected(f"construct not allowed: {type(node).__name__}")
    elif isinstance(node, ast.Constant) and isinstance(node.value, str) and "__" in node.value:
        raise ForgeRejected("dunder strings not allowed")


def check(code: str) -> None:
    if not isinstance(code, str) or not code.strip() or len(code) > CODE_LIMIT:
        raise ForgeRejected(f"code must be 1..{CODE_LIMIT} characters")
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ForgeRejected(f"syntax error at line {exc.lineno}") from exc
    for node in ast.walk(tree):
        _inspect(node)
    entry = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run"]
    if len(entry) != 1 or len(entry[0].args.args) != 1:
        raise ForgeRejected("define exactly one top-level def run(args)")


def name(value) -> str:
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ForgeRejected("name must be a lowercase identifier of 3..40 characters")
    return value
