import re

MASK = "[oscurato]"
KEEP_PREFIX = (
    r"(?i)(bearer[ \t]+)[A-Za-z0-9._~+/=-]{8,}",
    r"""(?i)((?:password|passwd|pwd|passphrase|parola[ _-]?d'ordine|chiave|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret|authorization|pin|otp)["']?[ \t]*[:=][ \t]*["']?)[^ \t\r\n"',;]+""",
)
WHOLE = (
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    r"sk-[A-Za-z0-9_-]{16,}",
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"xox[abposr]-[A-Za-z0-9-]{10,}",
    r"AIza[0-9A-Za-z_-]{35}",
    r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}",
    r"[A-Z]{2}[0-9]{2}(?:[ ]?[A-Z0-9]{4}){3,7}(?:[ ]?[A-Z0-9]{1,4})?",
    r"(?i)[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]",
)
CARD = r"[0-9](?:[ -]?[0-9]){12,18}"
_PREFIXED = [re.compile(p) for p in KEEP_PREFIX]
_WHOLES = [re.compile(p) for p in WHOLE]
_CARDS = re.compile(CARD)


def luhn(digits: str) -> bool:
    total, count = 0, 0
    for i, c in enumerate(ch for ch in reversed(digits) if "0" <= ch <= "9"):
        d = int(c)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        count += 1
    return 13 <= count <= 19 and total % 10 == 0


def redact(text: str) -> str:
    out = text
    for pattern in _WHOLES:
        out = pattern.sub(MASK, out)
    for pattern in _PREFIXED:
        out = pattern.sub(lambda m: (m.group(1) or "") + MASK, out)
    return _CARDS.sub(lambda m: MASK if luhn(m.group(0)) else m.group(0), out)
