import re

KINDS = ("speaker", "headphones", "headset", "microphone", "keyboard", "mouse", "gamepad", "joystick",
         "phone", "computer", "wearable", "other")
CAPABILITIES = ("audio_out", "audio_in", "pointer", "keyboard", "gamepad")

UUID_SINK = {"0000110b", "0000110d"}
UUID_HEADSET = {"00001108", "00001112", "0000111e", "0000111f", "00001131"}
UUID_HID = {"00001124", "00001812"}

ICON_KIND = {"audio-card": "speaker", "audio-headphones": "headphones", "audio-headset": "headset",
             "input-microphone": "microphone", "input-keyboard": "keyboard", "input-mouse": "mouse",
             "input-tablet": "mouse", "input-gaming": "gamepad", "phone": "phone", "computer": "computer"}
AV_MINOR = {1: "headset", 2: "headset", 4: "microphone", 5: "speaker", 6: "headphones", 7: "speaker", 8: "speaker",
            10: "speaker"}
HID_APPEARANCE = {1: "keyboard", 2: "mouse", 3: "joystick", 4: "gamepad", 5: "mouse"}
GAMEPAD_NAME = re.compile(r"controller|gamepad|joy-?con|dualshock|dualsense|xbox|8bitdo|joystick|wheel|stadia",
                          re.I)

KIND_CAPS = {
    "speaker": {"audio_out"},
    "headphones": {"audio_out"},
    "headset": {"audio_out", "audio_in"},
    "microphone": {"audio_in"},
    "keyboard": {"keyboard"},
    "mouse": {"pointer"},
    "gamepad": {"gamepad"},
    "joystick": {"gamepad"},
}


def _from_cod(cod: int | None) -> str | None:
    if not cod:
        return None
    major, minor = (cod >> 8) & 0x1F, (cod >> 2) & 0x3F
    if major == 1:
        return "computer"
    if major == 2:
        return "phone"
    if major == 4:
        return AV_MINOR.get(minor)
    if major == 5:
        sub = minor & 0x0F
        if sub == 1:
            return "joystick"
        if sub == 2:
            return "gamepad"
        if minor & 0x10:
            return "keyboard"
        if minor & 0x20:
            return "mouse"
    if major == 7:
        return "wearable"
    return None


def _from_appearance(appearance: int | None) -> str | None:
    if not appearance:
        return None
    if appearance >> 6 == 0x0F:
        return HID_APPEARANCE.get(appearance & 0x3F)
    if appearance >> 6 == 0x03:
        return "wearable"
    return None


def kind_of(dev: dict) -> str:
    kind = ICON_KIND.get(dev.get("icon") or "") or _from_cod(dev.get("cod")) or _from_appearance(dev.get("appearance"))
    uuids = set(dev.get("uuids") or [])
    if kind in (None, "keyboard", "mouse") and GAMEPAD_NAME.search(dev.get("name") or ""):
        return "gamepad"
    if kind:
        return kind
    if uuids & UUID_HEADSET:
        return "headset"
    if uuids & UUID_SINK:
        return "speaker"
    return "other"


def capabilities(dev: dict, kind: str) -> list[str]:
    uuids = set(dev.get("uuids") or [])
    caps = set(KIND_CAPS.get(kind, set()))
    if uuids & UUID_SINK:
        caps.add("audio_out")
    if uuids & UUID_HEADSET:
        caps.update({"audio_out", "audio_in"})
    if uuids & UUID_HID and not caps & {"pointer", "keyboard", "gamepad"} and kind not in ("phone", "computer"):
        caps.add("pointer")
    return [c for c in CAPABILITIES if c in caps]


def describe(dev: dict) -> dict:
    kind = kind_of(dev)
    caps = capabilities(dev, kind)
    return {**dev, "kind": kind, "capabilities": caps, "audio_out": "audio_out" in caps, "audio_in": "audio_in" in caps}
