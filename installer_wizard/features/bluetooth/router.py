from features.bluetooth import store
from features.devices import audio


def _key(mac: str) -> str:
    return mac.replace(":", "_")


def _ranked(live: dict, data: dict, cap: str, use_key: str, order: list[str], auto: bool) -> list[str]:
    ranked = []
    for mac, dev in live.items():
        settings = store.settings(data, mac)
        use = settings[use_key]
        if cap not in dev["capabilities"] or use == "never" or (use == "auto" and not auto):
            continue
        if cap == "audio_in" and settings["profile"] == "quality" and "audio_out" in dev["capabilities"]:
            continue
        position = order.index(mac) if mac in order else len(order)
        ranked.append((0 if use == "preferred" else 1, position, mac))
    return [mac for *_, mac in sorted(ranked)]


def choose(devs: list[dict], data: dict) -> dict:
    live = {d["mac"]: d for d in devs if d["connected"]}
    auto = data["auto_switch"]
    outputs = _ranked(live, data, "audio_out", "output_use", data["output_order"], auto)
    inputs = _ranked(live, data, "audio_in", "voice_input", data["input_order"], auto)
    return {"output": outputs[0] if outputs else None, "input": inputs[0] if inputs else None,
            "audio": [m for m, d in live.items() if {"audio_out", "audio_in"} & set(d["capabilities"])]}


def _pick(profiles: dict, wanted: str) -> str | None:
    names = [n for n, p in profiles.items() if p.get("available", True) and n != "off"]
    if wanted == "headset":
        return next((n for n in names if "handsfree_head_unit" in n), None) or next(
            (n for n in names if "head_unit" in n or "headset" in n), None)
    return next((n for n in names if "a2dp" in n and "sink" in n), None) or next((n for n in names if "a2dp" in n), None)


async def _profiles(choice: dict, data: dict) -> None:
    cards = {c["name"]: c for c in await audio.pactl_json("cards") if c.get("name", "").startswith("bluez_card.")}
    for mac in choice["audio"]:
        card = cards.get(f"bluez_card.{_key(mac)}")
        settings = store.settings(data, mac)
        if not card or (settings["output_use"] == "never" and settings["voice_input"] == "never"):
            continue
        profile = settings["profile"]
        wants_mic = profile == "headset" or (profile == "auto" and mac == choice["input"])
        target = _pick(card.get("profiles") or {}, "headset" if wants_mic else "quality")
        if target and target != card.get("active_profile"):
            await audio.pactl("set-card-profile", card["name"], target)


async def _nodes(kind: str) -> list[str]:
    items = await audio.pactl_json("sinks" if kind == "sink" else "sources")
    return [i.get("name", "") for i in items if i.get("name") and not i.get("name", "").endswith(".monitor")]


class Router:
    def __init__(self) -> None:
        self.fallback = {"sink": "", "source": ""}
        self.active = {"sink": "", "source": ""}

    async def _default(self, kind: str) -> str:
        _, out = await audio.pactl(f"get-default-{kind}")
        return out.strip()

    async def _level(self, kind: str, node: str, settings: dict) -> None:
        value = settings["volume"] if kind == "sink" else settings["mic_gain"]
        await audio.pactl(f"set-{kind}-volume", node, f"{int(value)}%")

    async def _switch(self, kind: str, mac: str | None, data: dict) -> bool:
        current = await self._default(kind)
        nodes = await _nodes(kind)
        if mac:
            node = next((n for n in nodes if _key(mac) in n), None)
            if not node or node == current:
                return False
            if current and not current.startswith("bluez_"):
                self.fallback[kind] = current
            await audio.pactl(f"set-default-{kind}", node)
            await self._level(kind, node, store.settings(data, mac))
            self.active[kind] = node
            return True
        if not current.startswith("bluez_") or current != self.active[kind]:
            self.active[kind] = ""
            return False
        target = self.fallback[kind] if self.fallback[kind] in nodes else next(
            (n for n in nodes if not n.startswith("bluez_")), "")
        if not target:
            return False
        await audio.pactl(f"set-default-{kind}", target)
        self.active[kind] = ""
        return True

    async def apply(self, devs: list[dict]) -> dict:
        data = store.load()
        choice = choose(devs, data)
        await _profiles(choice, data)
        output = await self._switch("sink", choice["output"], data)
        source = await self._switch("source", choice["input"], data)
        return {"output": choice["output"], "input": choice["input"], "changed": output or source}


router = Router()
