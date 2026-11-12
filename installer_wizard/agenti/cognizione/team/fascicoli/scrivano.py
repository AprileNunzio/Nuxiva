import hashlib
import json
import logging
import os
import secrets
import stat
import threading
import time
from functools import lru_cache
from pathlib import Path

from config import STATE_DIR, env_get
from agenti.team.fascicoli import motore
from agenti.team.fascicoli.archivio import StoreError
from agenti.team.fascicoli.formato import SCHEMA

log = logging.getLogger("nuxiva.team.fascicoli")
LANGS = ("it", "en", "fr", "es")
SEALED_RISK = 2
PRUNE_EVERY_MS = 3_600_000
PRUNE_BATCH = 200
DEFAULT_DAYS = 30


@lru_cache(maxsize=4)
def texts(lang: str) -> dict:
    lang = lang if lang in LANGS else "it"
    path = Path(__file__).resolve().parents[1] / "language" / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))["fascicolo"]


def _now_ms() -> int:
    return int(time.time() * 1000)


def _key(root: Path) -> bytes:
    path = root / ".chiave"
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        key = secrets.token_bytes(32)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(key)
            os.fsync(handle.fileno())
        return key
    with os.fdopen(fd, "rb") as handle:
        if stat.S_IMODE(os.fstat(handle.fileno()).st_mode) & 0o077:
            raise PermissionError("la chiave dei fascicoli è leggibile da altri utenti")
        key = handle.read(33)
    if len(key) != 32:
        raise ValueError("chiave dei fascicoli non valida")
    return key


class Scrivano:
    def __init__(self, root: Path | None = None, native: bool = True) -> None:
        self.root = root or (STATE_DIR / "fascicoli")
        self.native = native
        self._store = None
        self._lock = threading.Lock()
        self._pruned_at = 0

    @staticmethod
    def enabled() -> bool:
        return env_get("NUXIVA_FASCICOLI", "1") != "0"

    @staticmethod
    def days() -> int:
        try:
            return max(1, min(3650, int(env_get("NUXIVA_FASCICOLI_GIORNI", str(DEFAULT_DAYS)))))
        except ValueError:
            return DEFAULT_DAYS

    def store(self):
        with self._lock:
            if self._store is None:
                self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
                os.chmod(self.root, 0o700)
                self._store = motore.store(str(self.root), _key(self.root), self.native)
            return self._store

    def _doc(self, kind: str, handle: dict, sections: dict, lang: str) -> dict:
        t = texts(lang)
        front = [["schema", SCHEMA], ["file", kind], ["operazione", handle["id"]], ["livello", handle["level"]],
                 ["autore", "ceo"], ["creato", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())], ["lingua", lang]]
        if handle.get("agents"):
            front.append(["agenti", "[" + ", ".join(handle["agents"]) + "]"])
        return {"front": front, "title": t["titles"][kind],
                "sections": [{"anchor": a, "heading": t["headings"][a], "body": b} for a, b in sections.items()]}

    def _write(self, handle: dict, name: str, kind: str, sections: dict) -> None:
        doc = self._doc(kind, handle, sections, handle["lang"])
        self.store().write(handle["rel"], name, doc, _now_ms())

    def open(self, decision, text: str, lang: str, channel: str = "chat", card=None) -> dict:
        if not self.enabled():
            return {}
        t = texts(lang)["text"]
        primary = decision.primary_agent
        helpers = list(decision.secondary_agents)
        handle = {"lang": lang if lang in LANGS else "it", "level": decision.level, "started": _now_ms(),
                  "agents": [primary.id] + [h.id for h in helpers], "sealed": bool(card and card.get("risk", 0) >= SEALED_RISK)}
        try:
            handle["rel"] = self.store().open(decision.level, handle["started"])
            handle["id"] = handle["rel"].rsplit("/", 1)[1]
            self._write(handle, "00-richiesta.md", "richiesta", {
                "request": text,
                "origin": t["origin"].format(channel=channel, lang=handle["lang"]),
            })
            if decision.level != "lampo":
                self._plan(handle, decision, card, "open")
            self._maybe_prune()
        except (OSError, ValueError, RuntimeError, StoreError, KeyError) as exc:
            log.warning("fascicolo non scritto: %s", exc)
            return {}
        return handle

    def _plan(self, handle: dict, decision, card, state: str) -> None:
        t = texts(handle["lang"])["text"]
        primary = decision.primary_agent
        scores = {aid: score for aid, score, _ in decision.ranked}
        why = ", ".join(decision.ranked[0][2][:6]) if decision.ranked else t["none"]
        lines = [t["agent_line"].format(name=primary.name, id=primary.id, score=scores.get(primary.id, 0), role=t["role_primary"])]
        lines += [t["agent_line"].format(name=h.name, id=h.id, score=scores.get(h.id, 0), role=t["role_support"])
                  for h in decision.secondary_agents]
        self._write(handle, "01-contesto.md", "contesto", {
            "agents": "\n".join(lines),
            "signals": t["signals"].format(confidence=decision.confidence, level=decision.level, why=why,
                                           node=decision.target_node, tier=decision.execution_tier),
        })
        mark = {"open": " ", "verified": "x", "done": "~", "failed": "!"}[state]
        steps = [t["step"].format(mark=mark, n=1, id=primary.id, goal=t["step_primary"])]
        steps += [t["step"].format(mark=mark, n=i, id=h.id, goal=t["step_support"]) for i, h in enumerate(decision.secondary_agents, 2)]
        risky = bool(card and card.get("risk", 0) >= SEALED_RISK)
        self._write(handle, "02-piano.md", "piano", {
            "goal": t["goal"].format(name=primary.name),
            "criteria": t["criteria"],
            "steps": "\n".join(steps),
            "risks": t["risks_high"] if risky else t["risks_low"],
        })

    def close(self, handle: dict, decision, result: dict, outcome: dict, agent_name: str) -> None:
        if not handle.get("rel"):
            return
        t = texts(handle["lang"])["text"]
        reply = str(result.get("reply") or "")
        if not reply:
            answer = t["answer_empty"]
        elif handle["sealed"]:
            digest = hashlib.sha256(reply.encode()).hexdigest()[:12]
            answer = t["answer_sealed"].format(chars=len(reply), digest=digest)
        else:
            answer = reply
        status = outcome.get("status", "unverified")
        verified = bool(outcome.get("verified"))
        try:
            if handle["level"] != "lampo":
                state = "verified" if verified else ("failed" if status in ("failed", "blocked") else "done")
                self._plan(handle, decision, None if not handle["sealed"] else {"risk": SEALED_RISK}, state)
            self._write(handle, "99-esito.md", "esito", {
                "summary": t["summary"].format(status=status, verified=t["yes"] if verified else t["no"], agent=agent_name),
                "answer": answer,
                "timing": t["timing"].format(ms=max(0, _now_ms() - handle["started"]), level=handle["level"]),
            })
        except (OSError, ValueError, RuntimeError, StoreError, KeyError) as exc:
            log.warning("esito del fascicolo non scritto: %s", exc)

    def _maybe_prune(self) -> None:
        now = _now_ms()
        if now - self._pruned_at < PRUNE_EVERY_MS:
            return
        self._pruned_at = now
        store = self.store()
        for rel in store.expired(now, self.days(), PRUNE_BATCH):
            store.prune(rel, now)


scrivano = Scrivano()
