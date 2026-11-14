import json
import logging
import re
from pathlib import Path

log = logging.getLogger("nuxiva.ear.merge")
CATALOG = Path(__file__).with_name("intents.json")
REF_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
MAX_SPOKEN = 4096
TAIL_WORDS = 2


def native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "RustMerge", None)


def words(text: str) -> list[str]:
    out = []
    for raw in text.split():
        w = raw.strip("".join(c for c in raw if not c.isalnum())).replace("’", "'").replace("`", "'").lower()
        if w:
            out.append(w)
    return out


class PyMerge:
    def __init__(self, catalog_json: str = ""):
        data = json.loads(catalog_json or CATALOG.read_text(encoding="utf-8"))
        self._cancel, self._resume, self._modify = (self._phrases(data[k]) for k in ("cancel", "continue", "modify"))

    @staticmethod
    def _phrases(items) -> list:
        if not items or len(items) > 128:
            raise ValueError("duplex.invalid")
        out = [words(p) for p in items]
        if any(not p for p in out):
            raise ValueError("duplex.invalid")
        return out

    def classify(self, text: str) -> str:
        s = words(text)
        if not s:
            return json.dumps("unrelated")
        for p in self._modify:
            if any(s[i:i + len(p)] == p for i in range(len(s) - len(p) + 1)):
                return json.dumps("modify")
        head = next((p for p in self._resume if s[:len(p)] == p), None)
        if head is not None:
            return json.dumps("continue" if len(s) - len(head) <= TAIL_WORDS else "unrelated")
        head = next((p for p in self._cancel if s[:len(p)] == p), None)
        if head is not None:
            return json.dumps("cancel" if len(s) - len(head) <= TAIL_WORDS else "replace")
        return json.dumps("unrelated")

    @staticmethod
    def interrupted(duplex, spoken_text: str, unspoken_ref=None) -> str:
        note = json.loads(duplex.interruption())
        if note is None:
            raise ValueError("duplex.transition")
        if unspoken_ref is not None and not REF_RE.match(unspoken_ref):
            raise ValueError("duplex.invalid")
        return json.dumps({"spoken_text": spoken_text[:MAX_SPOKEN], "unspoken_ref": unspoken_ref, "interrupted_at_ms": note["at_ms"], "spoken_chars": note["spoken_chars"]})

    def plan(self, interrupted_json: str, text: str) -> str:
        if len(interrupted_json) > 16384:
            raise ValueError("duplex.too_large")
        try:
            reply = json.loads(interrupted_json)
        except ValueError:
            raise ValueError("duplex.parse") from None
        intent = json.loads(self.classify(text))
        ref = reply.get("unspoken_ref")
        return json.dumps({"intent": intent, "drop_previous": intent in ("cancel", "replace"), "resume_ref": ref if intent == "continue" else None, "regenerate_ref": ref if intent == "modify" else None})


def build(catalog_json: str = ""):
    klass = native()
    return klass(catalog_json) if klass is not None else PyMerge(catalog_json)
