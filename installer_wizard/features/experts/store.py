import json
import logging
import threading
import time

from config import STATE_DIR
from sealed import SealedFile, write_private

from features.experts.model import Expert, ExpertError, build

log = logging.getLogger("nuxiva.experts")
PROFILES = STATE_DIR / "experts.json"
HISTORY = STATE_DIR / "experts_history.sealed"
HISTORY_KEY = STATE_DIR / "experts_history.key"
SEEDED = STATE_DIR / "experts_seeded.json"
KEEP_TURNS = 40
MAX_EXPERTS = 400


class ExpertStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._experts: dict[str, Expert] | None = None
        self._history = SealedFile(HISTORY, HISTORY_KEY)

    def _load(self) -> dict[str, Expert]:
        if self._experts is not None:
            return self._experts
        experts: dict[str, Expert] = {}
        try:
            rows = json.loads(PROFILES.read_text(encoding="utf-8")) if PROFILES.exists() else []
        except (OSError, ValueError) as exc:
            log.error("Esperti non leggibili: %s", exc)
            raise
        from features.agent import registry
        known = set(registry.TOOLS)
        for row in rows if isinstance(rows, list) else []:
            try:
                expert = build({**row, "tools": [t for t in row.get("tools") or [] if t in known]}, known)
            except (ExpertError, AttributeError) as exc:
                log.warning("Esperto scartato: %s", exc)
                continue
            experts[expert.id] = expert
        self._experts = experts
        return experts

    def _save(self) -> None:
        data = [e.to_dict() for e in self._load().values()]
        write_private(PROFILES, json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8"))

    def all(self) -> list[Expert]:
        with self._lock:
            return sorted(self._load().values(), key=lambda e: e.created)

    def get(self, expert_id: str) -> Expert:
        with self._lock:
            found = self._load().get(expert_id)
        if found is None:
            raise KeyError(expert_id)
        return found

    def free_id(self, wanted: str) -> str:
        with self._lock:
            taken = self._load()
            candidate, n = wanted, 2
            while candidate in taken:
                candidate = f"{wanted[:36]}-{n}"
                n += 1
            return candidate

    def put(self, expert: Expert, create: bool) -> Expert:
        with self._lock:
            experts = self._load()
            if create and expert.id in experts:
                raise ExpertError("Esiste già un esperto con questo identificativo")
            if create and len(experts) >= MAX_EXPERTS:
                raise ExpertError("Numero massimo di esperti raggiunto")
            if not create and expert.id not in experts:
                raise KeyError(expert.id)
            experts[expert.id] = expert
            self._save()
            return expert

    def remove(self, expert_id: str) -> None:
        with self._lock:
            experts = self._load()
            if expert_id not in experts:
                raise KeyError(expert_id)
            del experts[expert_id]
            self._save()
            history = self._history.load()
            if history.pop(expert_id, None) is not None:
                self._history.save(history)

    def seeded(self) -> set[str]:
        try:
            rows = json.loads(SEEDED.read_text(encoding="utf-8")) if SEEDED.exists() else []
        except (OSError, ValueError) as exc:
            log.error("Elenco degli esperti predefiniti non leggibile: %s", exc)
            raise
        return {str(r) for r in rows} if isinstance(rows, list) else set()

    def mark_seeded(self, ids: set[str]) -> None:
        write_private(SEEDED, json.dumps(sorted(ids), ensure_ascii=False).encode("utf-8"))

    def history(self, expert_id: str) -> list[dict]:
        with self._lock:
            return list(self._history.load().get(expert_id) or [])

    def remember(self, expert_id: str, role: str, text: str, steps: list[dict] | None = None) -> dict:
        row = {"at": time.time(), "role": role, "text": str(text)[:4000]}
        if steps:
            row["steps"] = [{"tool": s["tool"], "ok": not str(s["result"]).startswith(("ERRORE", "NEGATO"))} for s in steps][:12]
        with self._lock:
            history = self._history.load()
            turns = history.setdefault(expert_id, [])
            turns.append(row)
            del turns[:-KEEP_TURNS]
            self._history.save(history)
        return row

    def forget(self, expert_id: str) -> None:
        with self._lock:
            history = self._history.load()
            if history.pop(expert_id, None) is not None:
                self._history.save(history)


experts = ExpertStore()
