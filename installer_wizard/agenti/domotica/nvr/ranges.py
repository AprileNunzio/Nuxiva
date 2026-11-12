import native_module

MAX_HEADER = 200


def _number(text: str) -> int | None:
    if not text or len(text) > 19 or not text.isascii() or not text.isdigit():
        return None
    return int(text)


def py_parse_range(header: str, total: int) -> tuple[str, int, int]:
    header = (header or "").strip()
    if not header:
        return "whole", 0, max(0, total - 1)
    if len(header) > MAX_HEADER or total <= 0 or not header.startswith("bytes="):
        return "invalid", 0, 0
    spec = header[6:].strip()
    if "," in spec or "-" not in spec:
        return "invalid", 0, 0
    left, right = (part.strip() for part in spec.split("-", 1))
    last = total - 1
    if not left:
        n = _number(right)
        return ("part", max(0, total - n), last) if n else ("invalid", 0, 0)
    start = _number(left)
    if not right:
        return ("part", start, last) if start is not None and start <= last else ("invalid", 0, 0)
    end = _number(right)
    if start is None or end is None or start > end or start > last:
        return "invalid", 0, 0
    return "part", start, min(end, last)


def parse_range(header: str, total: int) -> tuple[str, int, int]:
    fn = native_module.feature("nvr_parse_range")
    if fn is None:
        native_module.python_fallback("nvr.range")
        return py_parse_range(header, total)
    kind, start, end = fn(str(header or "")[:MAX_HEADER + 1], max(0, int(total)))
    return str(kind), int(start), int(end)
