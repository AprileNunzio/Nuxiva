import asyncio
import glob
import json
import logging
import os
import re
import time
from pathlib import Path

from config import STATE_DIR, WIDGETS_DIR
from features.desktop import manifest
from features.desktop.manifest import clamp_refresh
from features.desktop.novelty import AUTO_CAP, Novelty
from features.desktop.privacy import privacy
from features.desktop.screens import screens
from state import store

log = logging.getLogger("nuxiva.widgets")

SYSTEM_DIR = WIDGETS_DIR
USER_DIR = STATE_DIR / "widgets"
STATE_FILE = STATE_DIR / "widgets.json"
NOVELTY_FILE = STATE_DIR / "widget_novelty.json"
FORCED_KEY_PREFIXES = ("recall:", "test:")
FILES = {"widget.js": "application/javascript", "widget.css": "text/css"}
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,40}$")
REQUEST_HOLD = 120
SNOOZE = 600
AUTO_PREFIXES = ("briefing:", "welcome:", "sport-near:")
SNOOZE_FORGET = 6 * 3600


class Desk:
    def __init__(self) -> None:
        self.widgets: dict[str, dict] = {}
        self.errors: list[dict] = []
        self.signature = ""
        self.instances: dict[str, dict] = {}
        self.last: dict[str, dict] = {}
        self.sources: dict = {}
        self.providers: dict = {}
        self.polled: dict[str, float] = {}
        self.cost: dict[str, dict] = {}
        self.suppressed: set = set()
        self.request_at = 0.0
        self.dismissed: dict[str, tuple[str, float]] = {}
        self.idle_at = 0.0
        self.prefs = self._load()
        self.novelty = Novelty(NOVELTY_FILE)
        USER_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _load() -> dict:
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.prefs, indent=1, ensure_ascii=False), encoding="utf-8")
        tmp.replace(STATE_FILE)

    def scan(self) -> bool:
        paths = sorted(glob.glob(str(SYSTEM_DIR / "*" / "widget.json")) + glob.glob(str(USER_DIR / "*" / "widget.json")))
        sig = "|".join(f"{p}:{os.path.getmtime(p)}" for p in paths if os.path.exists(p))
        if sig == self.signature:
            return False
        self.signature = sig
        found, errors = {}, []
        for p in paths:
            folder = Path(p).parent
            try:
                m = json.loads(Path(p).read_text(encoding="utf-8"))
                m.setdefault("id", folder.name)
                if not _ID_RE.match(str(m["id"])) or not m.get("name"):
                    raise ValueError("id o nome non validi")
                if not (folder / "widget.js").exists():
                    raise ValueError("manca widget.js")
                if m["id"] in found:
                    raise ValueError("id già usato")
            except (OSError, ValueError, TypeError) as exc:
                errors.append({"path": p, "error": str(exc)[:200]})
                continue
            manifest.normalize(m, folder, SYSTEM_DIR)
            found[m["id"]] = m
        new = [w for w in found if w not in self.widgets and self.widgets]
        self.widgets, self.errors = found, errors
        for w in new:
            store.event("INFO", f"Nuovo widget disponibile: {found[w]['name']}", "widgets")
        for e in errors:
            log.warning("Widget non valido %s: %s", e["path"], e["error"])
        self.publish()
        return True

    def enabled(self, wid: str) -> bool:
        return self.prefs.get(wid, {}).get("enabled", True)

    def priority(self, wid: str) -> int:
        p = self.prefs.get(wid, {}).get("priority")
        return int(p) if p is not None else self.widgets.get(wid, {}).get("priority", 50)

    def refresh_of(self, wid: str) -> int | None:
        rec = self.prefs.get(wid, {})
        if "refresh" in rec:
            return rec["refresh"]
        return self.widgets.get(wid, {}).get("refresh")

    def set_prefs(self, wid: str, body: dict) -> None:
        if wid not in self.widgets:
            raise KeyError(wid)
        rec = self.prefs.setdefault(wid, {})
        if "enabled" in body:
            rec["enabled"] = bool(body["enabled"])
        if "priority" in body:
            rec["priority"] = None if body["priority"] in ("", None) else max(0, min(100, int(body["priority"])))
        if "refresh" in body:
            if body["refresh"] in ("", None):
                rec.pop("refresh", None)
            else:
                rec["refresh"] = clamp_refresh(body["refresh"])
        self._save()
        self.publish()

    def set_position(self, wid: str, x: float | None, y: float | None) -> None:
        if wid not in self.widgets:
            raise KeyError(wid)
        rec = self.prefs.setdefault(wid, {})
        if x is None or y is None:
            rec.pop("pos", None)
        else:
            rec["pos"] = {"x": max(0.0, min(1.0, float(x))), "y": max(0.0, min(1.0, float(y)))}
        self._save()
        self.publish()

    def set_screen(self, wid: str, screen: int | None) -> None:
        if wid not in self.widgets:
            raise KeyError(wid)
        rec = self.prefs.setdefault(wid, {})
        if screen is None:
            rec.pop("screen", None)
        else:
            rec["screen"] = int(screen)
            rec.pop("pos", None)
        self._save()
        self.publish()

    def screen_hello(self, n: int, x: int, w: int, h: int, local: bool = False, ear: str = "", perf: str = "",
                     client: str = "") -> None:
        screens.perf(client or "?", n, local, w, h, perf)
        if screens.hello(n, x, w, h, local, ear):
            self.publish()

    def position(self, wid: str):
        return self.prefs.get(wid, {}).get("pos") or self.widgets.get(wid, {}).get("pos")

    def show(self, wid: str, data: dict | None = None, key: str | None = None, ttl: float | None = None,
             priority: int | None = None, intent: bool = False, fullscreen: bool | None = None) -> None:
        m = self.widgets.get(wid)
        if not m:
            return
        key = key or wid
        if self.snoozed(key, data):
            return
        ttl = ttl if ttl is not None else m.get("ttl")
        if data and not key.startswith(("test:", "recall:")):
            self.last[wid] = data
        old = self.instances.get(key)
        self.instances[key] = {
            "key": key, "id": wid, "data": data or {}, "priority": priority, "intent": intent,
            "shown_at": old["shown_at"] if old else time.time(), "refreshed_at": time.time(),
            "opened_at": time.time() if intent or not old else old.get("opened_at", time.time()),
            "fullscreen": bool(old and old.get("fullscreen")) if fullscreen is None else fullscreen,
            "sticky": bool(m.get("sticky")),
            "expires_at": time.time() + float(ttl) if ttl else None,
        }
        self.publish()

    @staticmethod
    def _sig(data) -> str:
        return json.dumps(data or {}, sort_keys=True, default=str)

    def dismiss(self, key: str) -> bool:
        inst = self.instances.get(key)
        if not inst:
            return False
        now = time.time()
        self.dismissed = {k: v for k, v in self.dismissed.items() if now - v[1] < SNOOZE_FORGET}
        if not inst.get("intent") and not self.widgets.get(inst["id"], {}).get("urgent"):
            self.dismissed[key] = (self._sig(inst["data"]), now)
        self.hide(key=key)
        return True

    def snoozed(self, key: str, data) -> bool:
        hit = self.dismissed.get(key)
        if not hit:
            return False
        if time.time() - hit[1] < SNOOZE or hit[0] == self._sig(data):
            return True
        self.dismissed.pop(key, None)
        return False

    def hide(self, wid: str | None = None, key: str | None = None) -> None:
        keys = [key] if key else [k for k, i in self.instances.items() if i["id"] == wid]
        if any(self.instances.pop(k, None) for k in keys):
            self.publish()

    def fullscreen(self, key: str | None = None, on: bool = True) -> str | None:
        target = key if key in self.instances else None
        if target is None and key is None:
            if not on:
                target = next((k for k, i in self.instances.items() if i.get("fullscreen")), None)
            else:
                shown = self.active()
                target = shown[0]["key"] if shown else None
        if target is None:
            return None
        self.instances[target]["fullscreen"] = bool(on)
        if on:
            for other, inst in self.instances.items():
                if other != target:
                    inst["fullscreen"] = False
        self.publish()
        return target

    def in_request(self) -> bool:
        return self.request_at > self.idle_at and time.time() - self.request_at < REQUEST_HOLD

    def went_idle(self) -> None:
        self.idle_at = time.time()
        self.dismiss_intents()

    def request_started(self) -> None:
        self.request_at = time.time()

    def wake(self) -> int:
        self.request_started()
        keys = [k for k in self.instances if k.startswith(AUTO_PREFIXES)]
        for k in keys:
            self.instances.pop(k, None)
        if keys:
            self.publish()
        return len(keys)

    def on_intent(self, intent: str, ui: dict) -> None:
        self.request_started()
        wanted = {m["id"] for m in self.widgets.values()
                  if intent in m["intents"] and not m.get("standalone")}
        self.dismiss_intents(keep=wanted)
        for m in self.widgets.values():
            if m["id"] in wanted:
                panel = next((p for p in ui.get("panels", []) if p.get("type") == m.get("panel_type")), None)
                self.show(m["id"], (panel or {}).get("data") or {"title": ui.get("title", "")}, intent=True)

    def dismiss_intents(self, keep: set | None = None) -> None:
        keys = [k for k, i in self.instances.items() if i.get("intent") and not i.get("sticky") and i["id"] not in (keep or set())]
        for k in keys:
            self.instances.pop(k, None)
        if keys:
            self.publish()

    @staticmethod
    def _present() -> set[str]:
        presence = store.presence if isinstance(store.presence, dict) else {}
        return {p["slug"] for p in presence.get("people", []) if isinstance(p, dict) and p.get("known") and p.get("slug")}

    def audience_ok(self, wid: str, present: set[str]) -> bool:
        from features.team.control import control
        allowed = control.widget_people(wid)
        return not allowed or bool(present & set(allowed))

    def active(self) -> list[dict]:
        now = time.time()
        out, replaced = [], set()
        present = self._present()
        items = [i for i in self.instances.values()
                 if (not i["expires_at"] or i["expires_at"] > now) and i["id"] in self.widgets and self.enabled(i["id"])
                 and self.audience_ok(i["id"], present)]
        for i in items:
            replaced.update(self.widgets[i["id"]]["replaces"])
        for i in items:
            if i["id"] in replaced:
                continue
            m = self.widgets[i["id"]]
            prio = i["priority"] if i["priority"] is not None else self.priority(i["id"])
            out.append({**i, "priority": prio, "size": m["size"], "name": m["name"], "icon": m["icon"],
                        "rev": m["rev"], "css": m["has_css"], "chrome": m.get("chrome", True),
                        "essential": m.get("essential", False), "urgent": m.get("urgent", False), "tone": m.get("tone", "cyan"),
                        "pos": self.position(i["id"]), "overlay": m.get("overlay", False),
                        "takeover": prio >= 90 and m["size"] == "full", "fullscreen": bool(i.get("fullscreen")),
                        "sticky": bool(m.get("sticky")), "immersive": bool(m.get("immersive")),
                        "personal": m.get("personal", False), "refresh": self.refresh_of(i["id"])})
        out = self._rotate(out)
        wanted = {wid: p["screen"] for wid, p in self.prefs.items() if p.get("screen") is not None}
        return screens.assign(out, wanted)

    @staticmethod
    def _forced(item: dict) -> bool:
        return bool(item.get("intent") or item.get("urgent") or item.get("essential") or item.get("takeover")
                    or item.get("fullscreen") or item["key"].startswith(FORCED_KEY_PREFIXES))

    def _rotate(self, items: list[dict]) -> list[dict]:
        for item in items:
            item["rank"] = item["priority"] if self._forced(item) else item["priority"] - self.novelty.penalty(item["id"])
        items.sort(key=lambda x: (self._forced(x) is False, -x["rank"], -x["shown_at"]))
        forced = [i for i in items if self._forced(i)]
        optional = [i for i in items if not self._forced(i)][:AUTO_CAP]
        return forced + optional

    def sweep_private(self) -> bool:
        privacy.watch()
        store.privacy = privacy.view()
        if not privacy.away:
            self.suppressed.clear()
        if not privacy.enabled():
            return False
        now, limit, closed = time.time(), privacy.voice_seconds(), []
        for key, inst in list(self.instances.items()):
            if not self.widgets.get(inst["id"], {}).get("personal"):
                continue
            by_voice = bool(inst.get("intent")) and limit > 0 and now - inst.get("opened_at", now) >= limit
            if privacy.away or by_voice:
                self.instances.pop(key)
                closed.append(key)
                if key.startswith("bind:") and privacy.away:
                    self.suppressed.add(key)
        if closed:
            store.event("INFO", f"Widget con dati personali chiusi: {', '.join(closed)}", "privacy")
            self.publish()
        return bool(closed)

    def publish(self) -> None:
        store.desk = self.active()
        store.touch()

    def _bound_value(self, m: dict):
        bind = m.get("bind")
        attr = bind if isinstance(bind, str) else (bind or {}).get("attr")
        if not attr:
            return None
        source = self.sources.get(attr)
        try:
            return source() if source else getattr(store, attr, None)
        except Exception:
            log.exception("Sorgente del widget %s", m["id"])
            return None

    def recall(self, wid: str, target: str | int | None = None) -> str:
        m = self.widgets.get(wid)
        if not m:
            raise KeyError(wid)
        live = self._bound_value(m)
        if live:
            origin, data = "live", live if isinstance(live, dict) else {"value": live}
        elif self.last.get(wid):
            origin, data = "last", self.last[wid]
        else:
            origin, data = ("live" if m.get("standalone") else "empty"), {}
        self.dismissed.pop(f"recall:{wid}", None)
        self.show(wid, data, key=f"recall:{wid}", ttl=m.get("ttl") or 120, intent=True)
        if target and f"recall:{wid}" in self.instances:
            self.instances[f"recall:{wid}"]["target"] = str(target)
            if str(target).isdigit():
                self.instances[f"recall:{wid}"]["screen"] = int(target)
            self.publish()
        return origin

    def register_source(self, name: str, fn) -> None:
        self.sources[name] = fn

    def register_provider(self, wid: str, fn) -> None:
        self.providers[wid] = fn

    def refresh_instance(self, key: str, data: dict) -> None:
        inst = self.instances.get(key)
        if inst:
            inst.update(data=data, refreshed_at=time.time())
            self.publish()

    def _due(self, wid: str, now: float) -> bool:
        every = self.refresh_of(wid)
        if not every:
            return True
        if now - self.polled.get(wid, 0.0) < every:
            return False
        self.polled[wid] = now
        return True

    async def _providers(self) -> None:
        now = time.time()
        for key, inst in list(self.instances.items()):
            fn = self.providers.get(inst["id"])
            every = self.refresh_of(inst["id"])
            if not fn or not every or now - inst.get("refreshed_at", 0.0) < every:
                continue
            try:
                data = fn()
                data = await data if asyncio.iscoroutine(data) else data
            except Exception:
                log.exception("Aggiornamento del widget %s", inst["id"])
                inst["refreshed_at"] = now
                continue
            if isinstance(data, dict) and data:
                self.refresh_instance(key, data)
            else:
                inst["refreshed_at"] = now

    def _measured(self, wid: str, fn):
        wall, cpu = time.perf_counter(), time.thread_time()
        try:
            return fn()
        finally:
            spent_cpu = (time.thread_time() - cpu) * 1000
            spent_wall = (time.perf_counter() - wall) * 1000
            rec = self.cost.setdefault(wid, {"calls": 0, "cpu_ms": 0.0, "last_ms": 0.0, "since": time.time()})
            rec["calls"] += 1
            rec["cpu_ms"] += spent_cpu
            rec["last_ms"] = round(spent_wall, 2)

    def cost_of(self, wid: str) -> dict | None:
        rec = self.cost.get(wid)
        if not rec or not rec["calls"]:
            return None
        elapsed = max(1.0, time.time() - rec["since"])
        return {"calls": rec["calls"], "last_ms": rec["last_ms"], "avg_cpu_ms": round(rec["cpu_ms"] / rec["calls"], 3),
                "cpu_percent": round(rec["cpu_ms"] / (elapsed * 10), 3)}

    def _bindings(self) -> None:
        now = time.time()
        for m in self.widgets.values():
            bind = m.get("bind")
            if not bind or not self._due(m["id"], now):
                continue
            attr, when = (bind, None) if isinstance(bind, str) else (bind.get("attr"), bind.get("when"))
            source = self.sources.get(attr)
            try:
                value = self._measured(m["id"], source) if source else getattr(store, attr, None) if attr else None
            except Exception:
                log.exception("Sorgente del widget %s", m["id"])
                value = None
            key = f"bind:{m['id']}"
            if key in self.suppressed:
                continue
            ok = bool(value) and (not when or (isinstance(value, dict) and all(value.get(k) == v for k, v in when.items())))
            if ok:
                current = self.instances.get(key)
                if not current or current["data"] != value:
                    self.show(m["id"], value if isinstance(value, dict) else {"value": value}, key=key, ttl=m.get("ttl", 0))
                elif self.refresh_of(m["id"]):
                    self.refresh_instance(key, current["data"])
            elif key in self.instances:
                self.hide(key=key)

    def listing(self) -> dict:
        return {"widgets": [{k: v for k, v in m.items() if k != "dir"} | {"enabled": self.enabled(m["id"]),
                             "effective_priority": self.priority(m["id"]), "cost": self.cost_of(m["id"]),
                             "on_screen": sum(1 for i in self.instances.values() if i["id"] == m["id"])}
                            for m in sorted(self.widgets.values(), key=lambda x: -self.priority(x["id"]))],
                "active": self.active(), "errors": self.errors, "user_dir": str(USER_DIR)}

    def file(self, wid: str, name: str) -> Path | None:
        m = self.widgets.get(wid)
        if not m or name not in FILES:
            return None
        path = Path(m["dir"]) / name
        return path if path.exists() else None

    async def run(self) -> None:
        tick = 0
        while True:
            try:
                if tick % 20 == 0:
                    self.scan()
                self.sweep_private()
                self.novelty.tick([(i["id"], self._sig(i["data"]), bool(i.get("refresh"))) for i in store.desk
                                   if isinstance(i, dict) and i.get("id")], 1.0)
                self._bindings()
                await self._providers()
                if screens.changed():
                    self.publish()
                expired = [k for k, i in self.instances.items() if i["expires_at"] and i["expires_at"] <= time.time()]
                for k in expired:
                    self.instances.pop(k, None)
                if expired:
                    self.publish()
            except Exception:
                log.exception("Desktop dei widget")
            tick += 1
            await asyncio.sleep(1)


desk = Desk()
