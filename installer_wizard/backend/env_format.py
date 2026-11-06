import json
import os
import re
import sys
import tempfile
from pathlib import Path

import native_core

KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _py_decode_value(value: str) -> str:
    value = value.strip()
    while len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        if value[0] == '"':
            try:
                return json.loads(value.replace(r"\$", "$"))
            except json.JSONDecodeError:
                value = value[1:-1].strip()
                continue
        value = value[1:-1].strip()
    return value


def _py_format_line(key: str, value: str) -> str:
    if not KEY.fullmatch(key) or any(c in value for c in "\n\r\0"):
        raise ValueError("Chiave o valore di ambiente non valido")
    encoded = json.dumps(value, ensure_ascii=False).replace("$", r"\$")
    return f"{key}={encoded}"


def _py_entries(text: str):
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            yield None, line
        elif "=" in line:
            key, value = line.split("=", 1)
            key = key.strip().strip("\"'").strip()
            if KEY.fullmatch(key) and key not in seen:
                seen.add(key)
                yield key, _py_decode_value(value)


def _py_normalize(text: str) -> str:
    return "\n".join(value if key is None else _py_format_line(key, value) for key, value in _py_entries(text)) + "\n"


def _engine(name: str, fallback):
    native = native_core.symbol(name)
    if native is not None:
        return native
    native_core.python_fallback("env")
    return fallback


def decode_value(value: str) -> str:
    return _engine("env_decode_value", _py_decode_value)(value)


def format_line(key: str, value: str) -> str:
    return _engine("env_format_line", _py_format_line)(key, value)


def entries(text: str):
    native = native_core.symbol("env_entries")
    if native is None:
        native_core.python_fallback("env")
        yield from _py_entries(text)
        return
    yield from native(text)


def normalize(text: str) -> str:
    return _engine("env_normalize", _py_normalize)(text)


def main() -> None:
    action, name, *args = sys.argv[1:]
    path = Path(name)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if action == "export":
        for key, value in entries(text):
            if key is not None:
                sys.stdout.buffer.write(f"{key}={value}\0".encode("utf-8"))
        return
    if action == "set":
        key, value = args
        format_line(key, value)
        values = list(entries(text))
        out = [v if k is None else format_line(k, value if k == key else v) for k, v in values]
        if not any(k == key for k, _ in values):
            out.append(format_line(key, value))
        result = "\n".join(out) + "\n"
    elif action == "normalize":
        result = normalize(text)
    else:
        raise ValueError("Operazione non valida")
    if result != text:
        descriptor, temporary = tempfile.mkstemp(prefix=".nuxiva-env-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(result)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
