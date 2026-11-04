import json
import sys

try:
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (512 * 2**20, 512 * 2**20))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
except (ImportError, ValueError, OSError):
    pass

SAFE = ("abs", "all", "any", "ascii", "bin", "bool", "bytes", "bytearray", "callable", "chr", "complex", "dict",
        "divmod", "enumerate", "filter", "float", "format", "frozenset", "hash", "hex", "int", "isinstance",
        "issubclass", "iter", "len", "list", "map", "max", "min", "next", "oct", "ord", "pow", "range", "repr",
        "reversed", "round", "set", "slice", "sorted", "str", "sum", "tuple", "zip", "Exception", "ValueError",
        "TypeError", "KeyError", "IndexError", "ZeroDivisionError", "ArithmeticError", "OverflowError",
        "StopIteration", "LookupError", "RuntimeError", "NotImplementedError", "True", "False", "None")
ALLOWED = frozenset(sys.argv[1].split(",")) if len(sys.argv) > 1 else frozenset()


def _import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name.split(".")[0] not in ALLOWED:
        raise ImportError(name)
    return __import__(name, globals, locals, fromlist, level)


def main() -> None:
    raw = json.loads(sys.stdin.read())
    import builtins
    table = {key: getattr(builtins, key) for key in SAFE if hasattr(builtins, key)}
    table["__import__"] = _import
    namespace = {"__builtins__": table, "__name__": "forged"}
    try:
        exec(compile(raw["code"], "<forged>", "exec"), namespace)
        result = namespace["run"](raw["args"])
        payload = {"ok": True, "result": json.loads(json.dumps(result, ensure_ascii=False, default=str))}
    except Exception as exc:
        payload = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:400]}
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
