import time

from state import store

ALIVE = 30
MAIN_CAP = 2
BIG = ("l", "full")
ROLES = ("agent", "work", "visual")
WORK = frozenset({"repair_workbench", "code_view", "git_diff", "kanban_board", "document_viewer", "lavagna", "cicd_tracker",
                  "docker_matrix", "studio_3d", "viewer_3d", "thinking_tree", "text_long", "rag_sources", "system_monitor",
                  "net_topology", "firewall_logs", "os_networks", "ssh_sessions", "port_scanner", "usb_monitor", "active_tasks",
                  "project_status", "mission_tracker", "expert_work", "vram_allocator", "context_window", "api_costs"})
VISUAL = frozenset({"diorama", "chess_3d", "cam_stream", "live_cam", "tv_player", "karaoke", "audio_spectrum", "energy_chart",
                    "f1_race", "hockey_match", "sport_match", "sport_table"})


def role_of(item: dict) -> str:
    declared = item.get("screen_role")
    if declared in ROLES:
        return declared
    wid = item.get("id")
    return "work" if wid in WORK else "visual" if wid in VISUAL else "agent"


def configured_roles() -> dict[int, str]:
    disp = getattr(store, "display_settings", None)
    raw = disp.get("screen_roles") if isinstance(disp, dict) else None
    out = {}
    for k, v in (raw or {}).items() if isinstance(raw, dict) else ():
        try:
            n = int(k)
        except (TypeError, ValueError):
            continue
        if 0 <= n <= 16 and v in ROLES:
            out[n] = v
    return out


class Screens:
    def __init__(self) -> None:
        self.seen: dict[int, dict] = {}
        self.last: list[int] = []
        self.clients: dict[str, dict] = {}

    def perf(self, client: str, n: int, local: bool, w: int, h: int, text: str) -> None:
        now = time.time()
        self.clients[f"{client}#{n}"] = {"client": "questo server" if local else client, "screen": n,
                                         "size": f"{w}x{h}", "perf": text, "at": now}
        self.clients = {k: v for k, v in self.clients.items() if now - v["at"] < ALIVE * 4}
        store.displays = [{k: v for k, v in c.items() if k != "at"} for c in self.clients.values()]

    def hello(self, n: int, x: int, w: int, h: int, local: bool = False, ear: str = "") -> bool:
        known = set(s["n"] for s in self.active())
        previous = self.seen.get(n, {})
        if previous.get("local") and not local and time.time() - previous.get("at", 0) < ALIVE:
            return False
        self.seen[n] = {"n": n, "x": x, "w": w, "h": h, "local": local, "ear": ear, "at": time.time()}
        store.screens = self.active()
        return n not in known

    def active(self) -> list[dict]:
        now = time.time()
        live = [{k: v for k, v in s.items() if k != "at"} for s in self.seen.values() if now - s["at"] < ALIVE]
        return sorted(live, key=lambda s: (s["x"], s["n"]))

    def numbers(self) -> list[int]:
        return [s["n"] for s in self.active()] or [0]

    def changed(self) -> bool:
        return self.numbers() != self.last

    def roles(self, numbers: list[int] | None = None) -> dict[int, str]:
        screens = numbers or self.numbers()
        main = 0 if 0 in screens else screens[0]
        fixed = configured_roles()
        auto = iter(("work", "visual"))
        out = {}
        for n in screens:
            if n in fixed:
                out[n] = fixed[n]
            elif n == main:
                out[n] = "agent"
            else:
                out[n] = next(auto, "work")
        return out

    def screen_for_role(self, role: str, numbers: list[int] | None = None) -> int:
        screens = numbers or self.numbers()
        roles = self.roles(screens)
        main = 0 if 0 in screens else screens[0]
        fallback = {"visual": ("visual", "work"), "work": ("work", "visual")}.get(role, (role,))
        for wanted in fallback:
            for n in screens:
                if roles.get(n) == wanted and (n != main or wanted == "agent"):
                    return n
        return main

    def assign(self, items: list[dict], wanted: dict, session_mode: str = "shared") -> list[dict]:
        screens = self.last = self.numbers()
        main = 0 if 0 in screens else screens[0]
        others = [n for n in screens if n != main]
        load = {n: 0 for n in screens}
        store.screens = self.active()

        def lightest() -> int:
            return min(others, key=lambda n: (load[n], others.index(n)))

        for it in items:
            if it.get("takeover") or it.get("urgent") or (session_mode == "shared" and not others):
                it["screen"] = -1
                continue
            if it.get("overlay"):
                it["screen"] = main
                continue
            pref = wanted.get(it["id"])
            role = role_of(it)
            if pref in load:
                it["screen"] = pref
            elif not others:
                it["screen"] = main
            elif role != "agent":
                it["screen"] = self.screen_for_role(role, screens)
            elif it.get("size") in BIG or load[main] >= MAIN_CAP:
                it["screen"] = lightest()
            else:
                it["screen"] = main
            load[it["screen"]] += 1
        return items

screens = Screens()
