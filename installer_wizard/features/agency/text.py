import re
import secrets
import unicodedata

SLUG = re.compile(r"[^a-z0-9]+")
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f‪-‮⁦-⁩‎‏]")
SEGMENT = re.compile(r"[^\w .-]+")


def clean(value, limit: int) -> str:
    text = CONTROL.sub("", str(value or "")).replace("\r", "").strip()
    return text[:limit]


def slug(value, limit: int = 40, fallback: str = "x") -> str:
    ascii_text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    body = SLUG.sub("-", ascii_text).strip("-")[:limit].strip("-")
    return body or fallback


def unique_id(title: str) -> str:
    return f"{slug(title, 48, 'progetto')}-{secrets.token_hex(3)}"


def folder_name(title: str, fallback: str) -> str:
    name = SEGMENT.sub(" ", clean(title, 56)).strip(" .")
    name = re.sub(r"\s+", " ", name)
    return name or fallback


def strings(values, limit: int, count: int) -> list[str]:
    if not isinstance(values, list):
        return []
    out = [clean(v, limit) for v in values if isinstance(v, (str, int, float))]
    return [v for v in out if v][:count]


def estimate_tokens(*parts: str) -> int:
    return max(1, sum(len(p or "") for p in parts) // 4)
