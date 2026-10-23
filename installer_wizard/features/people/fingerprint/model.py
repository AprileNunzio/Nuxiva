import re

FINGERS = ("left_thumb", "left_index", "left_middle", "left_ring", "left_little",
           "right_thumb", "right_index", "right_middle", "right_ring", "right_little")
TRANSPORTS = ("usb", "bluetooth", "wifi", "builtin")
TEMPLATE_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,128}$")
READER_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,64}$")
EVENTS = ("match", "no_match", "enrolled", "enroll_failed")


def clean_label(value, limit: int = 40) -> str:
    return " ".join(str(value or "").split())[:limit]


def clean_reader(value) -> str:
    text = str(value or "").strip()
    return text if READER_RE.match(text) else ""


def clean_template(value) -> str:
    text = str(value or "").strip()
    return text if TEMPLATE_RE.match(text) else ""


def clean_transport(value) -> str:
    text = str(value or "").strip().lower()
    return text if text in TRANSPORTS else "usb"
