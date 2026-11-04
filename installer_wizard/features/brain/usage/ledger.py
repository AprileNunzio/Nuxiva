import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Mapping

from cryptography.fernet import InvalidToken
from config import ETC_DIR
from sealed import SealedFile

from features.cloud.catalog import BY_ID, is_cloud, parse_ref

LOCAL = "local"
KEEP_DAYS = 62
MAX_BUDGET = 10**12
MAX_MODELS_PER_DAY = 200
MAX_TOKENS_PER_CALL = 10**8
log = logging.getLogger("nuxiva.brain.usage")


class BudgetError(ValueError):
    pass


def provider_of(ref: str) -> str:
    if not is_cloud(ref):
        return LOCAL
    try:
        return parse_ref(ref)[0]
    except ValueError:
        return "unknown"


def _count(value: object) -> int:
    return max(0, min(MAX_TOKENS_PER_CALL, int(value))) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _cap(value: object) -> int | None:
    if value is None or value == "" or value == 0:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= MAX_BUDGET:
        raise BudgetError("budget_invalid")
    return value


def _clean(raw: object) -> dict:
    data = raw if isinstance(raw, dict) else {}
    days = data.get("days") if isinstance(data.get("days"), dict) else {}
    budgets = data.get("budgets") if isinstance(data.get("budgets"), dict) else {}
    providers = budgets.get("providers") if isinstance(budgets.get("providers"), dict) else {}
    clean_days = {}
    for day, rows in days.items():
        if isinstance(day, str) and len(day) == 10 and isinstance(rows, dict):
            clean_days[day] = {str(ref)[:230]: [_count(v) for v in (row + [0, 0, 0])[:3]]
                               for ref, row in list(rows.items())[:MAX_MODELS_PER_DAY] if isinstance(row, list)}
    caps = {}
    for pid, value in providers.items():
        try:
            cap = _cap(value)
        except BudgetError:
            continue
        if cap and pid in BY_ID:
            caps[pid] = cap
    try:
        total = _cap(budgets.get("global"))
    except BudgetError:
        total = None
    return {"days": clean_days, "budgets": {"global": total, "providers": caps}}


class UsageLedger:
    def __init__(self, sealed: SealedFile, clock: Callable[[], float] = time.time) -> None:
        self._sealed = sealed
        self._clock = clock
        self._lock = threading.Lock()
        self._data: dict | None = None

    def _state(self) -> dict:
        if self._data is None:
            try:
                self._data = _clean(self._sealed.load())
            except (OSError, ValueError, InvalidToken) as exc:
                log.error("Registro dei consumi illeggibile, ne inizio uno nuovo: %s", type(exc).__name__)
                self._data = _clean({})
        return self._data

    def _today(self) -> str:
        return datetime.fromtimestamp(self._clock(), timezone.utc).strftime("%Y-%m-%d")

    def _month(self) -> str:
        return self._today()[:7]

    def _persist(self, data: dict) -> None:
        cutoff = datetime.fromtimestamp(self._clock() - KEEP_DAYS * 86400, timezone.utc).strftime("%Y-%m-%d")
        data["days"] = {d: rows for d, rows in data["days"].items() if d >= cutoff}
        self._sealed.save(data)

    def record(self, ref: str, tokens_in: object, tokens_out: object) -> None:
        if not ref:
            return
        with self._lock:
            data = self._state()
            rows = data["days"].setdefault(self._today(), {})
            if ref not in rows and len(rows) >= MAX_MODELS_PER_DAY:
                return
            row = rows.setdefault(ref[:230], [0, 0, 0])
            row[0] += _count(tokens_in)
            row[1] += _count(tokens_out)
            row[2] += 1
            try:
                self._persist(data)
            except OSError as exc:
                log.error("Registro dei consumi non salvato: %s", exc)

    def _month_rows(self, data: dict) -> list[tuple[str, list[int]]]:
        month = self._month()
        return [(ref, row) for day, rows in data["days"].items() if day.startswith(month) for ref, row in rows.items()]

    def spent(self, provider: str | None = None) -> int:
        with self._lock:
            rows = self._month_rows(self._state())
        return sum(r[0] + r[1] for ref, r in rows
                   if (provider is None and provider_of(ref) != LOCAL) or provider_of(ref) == provider)

    def allows(self, ref: str) -> bool:
        provider = provider_of(ref)
        if provider == LOCAL:
            return True
        with self._lock:
            budgets = self._state()["budgets"]
        own, total = budgets["providers"].get(provider), budgets["global"]
        if own is not None and self.spent(provider) >= own:
            return False
        return total is None or self.spent() < total

    def set_budgets(self, raw: Mapping) -> dict:
        providers = raw.get("providers", {})
        providers = {} if providers is None else providers
        if not isinstance(providers, Mapping) or len(providers) > len(BY_ID):
            raise BudgetError("budget_invalid")
        caps = {}
        for pid, value in providers.items():
            if pid not in BY_ID:
                raise BudgetError("budget_unknown_provider")
            cap = _cap(value)
            if cap:
                caps[pid] = cap
        with self._lock:
            data = self._state()
            data["budgets"] = {"global": _cap(raw.get("global")), "providers": caps}
            self._persist(data)
        return self.summary()

    def summary(self) -> dict:
        with self._lock:
            data = self._state()
            rows = self._month_rows(data)
            budgets = {"global": data["budgets"]["global"], "providers": dict(data["budgets"]["providers"])}
            days = {d: sum(r[0] + r[1] for r in day_rows.values()) for d, day_rows in data["days"].items()}
            today = days.get(self._today(), 0)
        per_provider: dict[str, list[int]] = {}
        per_model: dict[str, list[int]] = {}
        for ref, row in rows:
            for bucket, key in ((per_provider, provider_of(ref)), (per_model, ref)):
                acc = bucket.setdefault(key, [0, 0, 0])
                for i in range(3):
                    acc[i] += row[i]
        cloud = sum(v[0] + v[1] for k, v in per_provider.items() if k != LOCAL)
        return {
            "month": self._month(),
            "today": today,
            "total": sum(v[0] + v[1] for v in per_provider.values()),
            "cloud": cloud,
            "budgets": budgets,
            "providers": [{"id": k, "tokens_in": v[0], "tokens_out": v[1], "calls": v[2], "budget": budgets["providers"].get(k)}
                          for k, v in sorted(per_provider.items(), key=lambda item: -(item[1][0] + item[1][1]))],
            "models": [{"ref": k, "tokens_in": v[0], "tokens_out": v[1], "calls": v[2]}
                       for k, v in sorted(per_model.items(), key=lambda item: -(item[1][0] + item[1][1]))[:20]],
            "days": [{"date": d, "tokens": t} for d, t in sorted(days.items())[-30:]],
        }

    def compact(self) -> dict:
        full = self.summary()
        cap = full["budgets"]["global"]
        return {"today": full["today"], "month": full["total"], "cloud": full["cloud"], "budget": cap,
                "used": round(min(1.0, full["cloud"] / cap), 4) if cap else None,
                "top": full["providers"][0]["id"] if full["providers"] else None}


usage_ledger = UsageLedger(SealedFile(ETC_DIR / "brain_usage.vault", ETC_DIR / "brain_usage.key"))
