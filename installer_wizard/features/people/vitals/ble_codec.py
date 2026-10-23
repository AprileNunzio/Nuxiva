HR_CHAR = "00002a37-0000-1000-8000-00805f9b34fb"
TEMP_CHAR = "00002a1c-0000-1000-8000-00805f9b34fb"
PLX_CHARS = ("00002a5e-0000-1000-8000-00805f9b34fb", "00002a5f-0000-1000-8000-00805f9b34fb")
HEALTH_SERVICES = ("180d", "1809", "1822")
METRICS_OF = {HR_CHAR: ["heart_rate"], TEMP_CHAR: ["body_temp"], PLX_CHARS[0]: ["spo2", "heart_rate"], PLX_CHARS[1]: ["spo2", "heart_rate"]}
_SFLOAT_SPECIAL = (0x07FF, 0x0800, 0x0801, 0x07FE, 0x0802)
_FLOAT_SPECIAL = (0x007FFFFF, 0x00800000, 0x00800001, 0x007FFFFE, 0x00800002)


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


def parse_heart_rate(data: bytes) -> list[tuple[str, float]]:
    if len(data) < (3 if data and data[0] & 1 else 2):
        return []
    return [("heart_rate", int.from_bytes(data[1:3], "little") if data[0] & 1 else data[1])]


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
    spo2, pulse = sfloat(int.from_bytes(data[1:3], "little")), sfloat(int.from_bytes(data[3:5], "little"))
    rows = [("spo2", round(spo2))] if spo2 is not None else []
    return rows + ([("heart_rate", round(pulse))] if pulse is not None else [])


PARSERS = {HR_CHAR: parse_heart_rate, TEMP_CHAR: parse_temperature, PLX_CHARS[0]: parse_oximeter, PLX_CHARS[1]: parse_oximeter}


def nearby_rows(found: dict) -> list[dict]:
    rows = []
    for address, (device, adv) in found.items():
        name = (adv.local_name or getattr(device, "name", "") or "")[:40]
        services = [u for u in adv.service_uuids or [] if str(u).lower()[4:8] in HEALTH_SERVICES]
        if name or services:
            rows.append({"address": address.upper(), "name": name, "rssi": adv.rssi, "services": services[:8]})
    return sorted(rows, key=lambda r: -(r["rssi"] or -127))[:40]
