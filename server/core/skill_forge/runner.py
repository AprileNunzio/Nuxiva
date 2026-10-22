import builtins
import json
import resource
import sys

ALLOWED = frozenset({
    "math", "statistics", "decimal", "fractions", "datetime", "re", "json", "itertools",
    "functools", "collections", "unicodedata", "typing",
})
SAFE_NAMES = (
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "frozenset", "int", "isinstance",
    "len", "list", "map", "max", "min", "pow", "range", "repr", "reversed", "round", "set", "slice", "sorted", "str",
    "sum", "tuple", "zip", "ord", "chr", "bin", "hex", "oct", "iter", "next", "callable", "hash", "ValueError",
    "TypeError", "KeyError", "IndexError", "ArithmeticError", "ZeroDivisionError", "Exception", "True", "False", "None",
)
MEMORY_BYTES = 256 * 2 ** 20
CPU_SECONDS = 2


def limit() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (8, 8))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name.split(".")[0] not in ALLOWED:
        raise ImportError(name)
    return builtins.__import__(name, globals, locals, fromlist, level)


def environment() -> dict:
    safe = {name: getattr(builtins, name) for name in SAFE_NAMES if hasattr(builtins, name)}
    safe["__import__"] = guarded_import
    return {"__builtins__": safe, "__name__": "skill"}


def main() -> int:
    request = json.loads(sys.stdin.buffer.read())
    scope = environment()
    code = compile(request["source"], "skill", "exec")
    limit()
    exec(code, scope)
    result = scope["run"](request["slots"])
    sys.stdout.write(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        status = main()
    except Exception as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": type(exc).__name__}))
        status = 3
    sys.stdout.flush()
    sys.exit(status)
