import re

from features.bluetooth import adapter, store
from features.bluetooth.service import service

KIND_WORDS = {"cuffie": ("headphones", "headset"), "auricolari": ("headset", "headphones"), "cassa": ("speaker",),
              "casse": ("speaker",), "speaker": ("speaker",), "microfono": ("microphone", "headset"),
              "mouse": ("mouse",), "tastiera": ("keyboard",), "joystick": ("joystick", "gamepad"),
              "controller": ("gamepad", "joystick"), "gamepad": ("gamepad", "joystick")}
_OFF = re.compile(r"\b(scollega|disconnetti|stacca|spegni)\w*\b", re.I)


def _pick(devs: list[dict], text: str) -> dict | None:
    low = text.lower()
    named = [d for d in devs if d["name"].lower() in low or any(w in low for w in d["name"].lower().split() if len(w) > 3)]
    if named:
        return named[0]
    kinds = next((k for word, k in KIND_WORDS.items() if word in low), None)
    paired = [d for d in devs if d["paired"]]
    audio = [d for d in paired if d["audio_out"] or d["audio_in"]]
    if kinds:
        audio = [d for d in paired if d["kind"] in kinds] or audio
    order = store.load()["output_order"]
    audio.sort(key=lambda d: order.index(d["mac"]) if d["mac"] in order else 99)
    return audio[0] if audio else None


async def bluetooth_action(text: str) -> tuple[str, dict]:
    state = await service.refresh()
    if not state["controller"].get("present"):
        return ("Questo server non ha un adattatore Bluetooth: collega una chiavetta USB e lo configuro da solo.",
                {"mode": "face"})
    off = bool(_OFF.search(text))
    dev = _pick([d for d in state["devices"] if d["connected"] == off], text)
    if not dev:
        what = "collegato" if off else "abbinato e spento"
        return f"Non trovo nessun dispositivo Bluetooth {what} che corrisponda. Puoi abbinarlo dal pannello Bluetooth.", {
            "mode": "face"}
    try:
        await (adapter.disconnect if off else adapter.connect)(dev["mac"])
    except adapter.BluetoothError as exc:
        return f"{dev['name']} non risponde: assicurati che sia acceso e vicino. ({exc})", {"mode": "face"}
    await service.refresh()
    if off:
        return f"Ho scollegato {dev['name']}.", {"mode": "face"}
    return f"{dev['name']} è collegato. Da ora la ascolto e le rispondo da lì, se è il preferito.", {"mode": "face"}
