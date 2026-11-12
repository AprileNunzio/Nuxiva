import math
from collections import deque


def char(short: str) -> str:
    return f"0000{short}-0000-1000-8000-00805f9b34fb"


HR_CHAR = char("2a37")
TEMP_CHAR = char("2a1c")
PLX_CHARS = (char("2a5e"), char("2a5f"))
BP_CHAR = char("2a35")
WEIGHT_CHAR = char("2a9d")
BODY_CHAR = char("2a9c")
HEALTH_SERVICES = ("180d", "1809", "1822", "1810", "181d", "181b")
METRICS_OF = {HR_CHAR: ["heart_rate", "hrv"], TEMP_CHAR: ["body_temp"], PLX_CHARS[0]: ["spo2", "heart_rate"], PLX_CHARS[1]: ["spo2", "heart_rate"],
              BP_CHAR: ["bp_sys", "bp_dia", "heart_rate"], WEIGHT_CHAR: ["weight"], BODY_CHAR: ["body_fat"]}
_SFLOAT_SPECIAL = (0x07FF, 0x0800, 0x0801, 0x07FE, 0x0802)
_FLOAT_SPECIAL = (0x007FFFFF, 0x00800000, 0x00800001, 0x007FFFFE, 0x00800002)
KPA_TO_MMHG = 7.50062
LB_TO_KG = 0.45359237
RR_WINDOW = 60
RR_MIN = 20


def u16(data: bytes, at: int) -> int:
    return int.from_bytes(data[at:at + 2], "little")


def sfloat(raw: int) -> float | None:
    if raw in _SFLOAT_SPECIAL:
        return None
    mantissa, exponent = raw & 0x0FFF, raw >> 12
    mantissa -= 0x1000 if mantissa >= 0x800 else 0
    exponent -= 0x10 if exponent >= 0x8 else 0
    return mantissa * 10 ** exponent


def ieee_float(raw: int) -> float | None:
    if raw in _FLOAT_SPECIAL:
        return None
    mantissa, exponent = raw & 0xFFFFFF, raw >> 24
    mantissa -= 0x1000000 if mantissa >= 0x800000 else 0
    exponent -= 0x100 if exponent >= 0x80 else 0
    return mantissa * 10 ** exponent


def rr_intervals(data: bytes) -> list[float]:
    if not data:
        return []
    flags = data[0]
    at = 3 if flags & 1 else 2
    at += 2 if flags & 0x08 else 0
    if not flags & 0x10:
        return []
    out = []
    while at + 2 <= len(data):
        ms = u16(data, at) * 1000 / 1024
        if 250 <= ms <= 2400:
            out.append(round(ms, 1))
        at += 2
    return out


def parse_heart_rate(data: bytes) -> list[tuple[str, float]]:
    if len(data) < (3 if data and data[0] & 1 else 2):
        return []
    bpm = u16(data, 1) if data[0] & 1 else data[1]
    return [("heart_rate", bpm)] if bpm else []


def parse_temperature(data: bytes) -> list[tuple[str, float]]:
    if len(data) < 5:
        return []
    value = ieee_float(int.from_bytes(data[1:5], "little"))
    if value is None:
        return []
    return [("body_temp", round((value - 32) * 5 / 9 if data[0] & 1 else value, 1))]


def parse_oximeter(data: bytes) -> list[tuple[str, float]]:
    if len(data) < 5:
        return []
    spo2, pulse = sfloat(u16(data, 1)), sfloat(u16(data, 3))
    rows = [("spo2", round(spo2))] if spo2 is not None else []
    return rows + ([("heart_rate", round(pulse))] if pulse is not None else [])


def parse_blood_pressure(data: bytes) -> list[tuple[str, float]]:
    if len(data) < 7:
        return []
    flags = data[0]
    scale = KPA_TO_MMHG if flags & 1 else 1.0
    sys_v, dia_v = sfloat(u16(data, 1)), sfloat(u16(data, 3))
    rows = [] if sys_v is None or dia_v is None else [("bp_sys", round(sys_v * scale)), ("bp_dia", round(dia_v * scale))]
    at = 7 + (7 if flags & 0x02 else 0)
    if flags & 0x04 and len(data) >= at + 2:
        pulse = sfloat(u16(data, at))
        if pulse:
            rows.append(("heart_rate", round(pulse)))
    return rows


def parse_weight(data: bytes) -> list[tuple[str, float]]:
    if len(data) < 3:
        return []
    raw = u16(data, 1)
    if raw == 0xFFFF:
        return []
    kg = raw * 0.01 * LB_TO_KG if data[0] & 1 else raw * 0.005
    return [("weight", round(kg, 1))]


def parse_body(data: bytes) -> list[tuple[str, float]]:
    if len(data) < 4:
        return []
    raw = u16(data, 2)
    return [] if raw == 0xFFFF else [("body_fat", round(raw * 0.1, 1))]


PARSERS = {HR_CHAR: parse_heart_rate, TEMP_CHAR: parse_temperature, PLX_CHARS[0]: parse_oximeter, PLX_CHARS[1]: parse_oximeter,
           BP_CHAR: parse_blood_pressure, WEIGHT_CHAR: parse_weight, BODY_CHAR: parse_body}


class RrWindow:
    def __init__(self) -> None:
        self.rows: deque = deque(maxlen=RR_WINDOW)
        self.fresh = 0

    def add(self, intervals: list[float]) -> float | None:
        for ms in intervals:
            if self.rows and abs(ms - self.rows[-1]) > self.rows[-1] * 0.3:
                continue
            self.rows.append(ms)
            self.fresh += 1
        if len(self.rows) < RR_MIN or self.fresh < RR_MIN:
            return None
        self.fresh = 0
        rows = list(self.rows)
        diffs = [(b - a) ** 2 for a, b in zip(rows, rows[1:])]
        return round(math.sqrt(sum(diffs) / len(diffs)), 0)


def nearby_rows(found: dict) -> list[dict]:
    rows = []
    for address, (device, adv) in found.items():
        name = (adv.local_name or getattr(device, "name", "") or "")[:40]
        services = [u for u in adv.service_uuids or [] if str(u).lower()[4:8] in HEALTH_SERVICES]
        if name or services:
            rows.append({"address": address.upper(), "name": name, "rssi": adv.rssi, "services": services[:8]})
    return sorted(rows, key=lambda r: -(r["rssi"] or -127))[:40]
