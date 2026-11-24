import re
from dataclasses import dataclass
from datetime import datetime

SUFFIX = ".png"
MAX_HOST = 40
SEGMENT = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9 ._-]{0,62}[A-Za-z0-9_-]$|^[A-Za-z0-9_-]$")
HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}$")
SHARE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MANAGED = re.compile(r"^[a-z0-9-]{1,40}_\d{8}-\d{6}_\d{3}\.png$")
LANGS = ("it", "en", "fr", "es")


@dataclass(frozen=True)
class Mask:
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class Config:
    enabled: bool = False
    host: str = ""
    share: str = ""
    drive: str = ""
    subdir: str = "05 Scambio/Screenshot"
    masks: tuple = ()
    days: int = 30
    max_files: int = 500
    block_locked: bool = True
    block_guests: bool = True
    notice: bool = True
    lang: str = "it"

    @property
    def active(self) -> bool:
        return self.enabled and bool(self.host or self.drive)


def host_label(raw: str) -> str:
    out = ""
    for char in str(raw or "").lower():
        if char.isascii() and char.isalnum():
            out += char
        elif char in "-_. " and out and not out.endswith("-"):
            out += "-"
        if len(out) >= MAX_HOST:
            break
    return out.strip("-") or "nodo"


def file_name(host: str, when: datetime, seq: int) -> str:
    return f"{host_label(host)}_{when.astimezone():%Y%m%d-%H%M%S}_{seq % 1000:03d}{SUFFIX}"


def is_managed(name: str) -> bool:
    return bool(MANAGED.match(name))


def stamp(name: str) -> float | None:
    if not is_managed(name):
        return None
    try:
        return datetime.strptime(name.rsplit("_", 2)[1], "%Y%m%d-%H%M%S").timestamp()
    except ValueError:
        return None


def valid_subdir(subdir: str) -> bool:
    if not subdir:
        return True
    parts = subdir.split("/")
    return len(parts) <= 4 and all(SEGMENT.match(p) and not p.endswith((".", " ")) for p in parts)


def parse_target(raw: str) -> tuple[str, str, str]:
    raw = (raw or "").strip()
    if raw.startswith("smb://"):
        host, _, share = raw[6:].partition("/")
        share = share.rstrip("/")
        if HOST.match(host) and SHARE.match(share):
            return host, share, ""
        return "", "", ""
    if re.fullmatch(r"[A-Za-z]:\\?", raw):
        return "", "", raw[0].upper() + ":"
    return "", "", ""


def parse_masks(raw: str) -> tuple:
    out = []
    for item in (raw or "").split(";"):
        nums = [n.strip() for n in item.split(",")]
        if len(nums) != 4 or not all(n.isdigit() for n in nums):
            continue
        x, y, w, h = (int(n) for n in nums)
        if w > 0 and h > 0 and x + w <= 1000 and y + h <= 1000:
            out.append(Mask(x, y, w, h))
    return tuple(out[:16])


def flag(value, default: bool) -> bool:
    text = str(value or "").strip().lower()
    if text in ("1", "true", "yes"):
        return True
    if text in ("0", "false", "no"):
        return False
    return default


def from_settings(settings: dict) -> Config:
    get = lambda key: str(settings.get(key) or "").strip()
    host, share, drive = parse_target(get("NUXIVA_SCREENSHOT_TARGET"))
    subdir = get("NUXIVA_SCREENSHOT_SUBDIR") or Config.subdir
    if not valid_subdir(subdir):
        return Config()
    days = get("NUXIVA_SCREENSHOT_RETENTION_DAYS")
    lang = get("NUXIVA_UI_LANG")
    return Config(
        enabled=flag(get("NUXIVA_SCREENSHOT"), True), host=host, share=share, drive=drive, subdir=subdir,
        masks=parse_masks(get("NUXIVA_SCREENSHOT_MASK")), days=int(days) if days.isdigit() and int(days) <= 3650 else 30,
        block_locked=flag(get("NUXIVA_SCREENSHOT_BLOCK_LOCKED"), True),
        block_guests=flag(get("NUXIVA_SCREENSHOT_BLOCK_GUESTS"), True),
        notice=flag(get("NUXIVA_SCREENSHOT_NOTICE"), True), lang=lang if lang in LANGS else "it",
    )


def doomed(entries: list, days: int, max_files: int, now: float) -> list:
    ordered = sorted(entries, key=lambda e: (e[1], e[0]))
    out, kept = [], []
    for name, when in ordered:
        if days and now - when > days * 86400:
            out.append(name)
        else:
            kept.append(name)
    out.extend(kept[: max(0, len(kept) - max_files)])
    return out
