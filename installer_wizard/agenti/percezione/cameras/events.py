import time

RING = 200
items: list[dict] = []


def add(kind: str, source: str, name: str, text: str) -> dict:
    entry = {"at": time.time(), "kind": kind, "source": source, "name": name, "text": text}
    items.append(entry)
    del items[:-RING]
    try:
        from nuxiva_bus import BusError, nuxiva_bus
        nuxiva_bus.publish(f"camera.event.{kind if kind.isalnum() else 'other'}", entry, origin="cameras")
    except (ImportError, BusError):
        pass
    return entry


def recent(limit: int = 100, source: str = "") -> list[dict]:
    rows = [e for e in items if not source or e["source"] == source]
    return list(reversed(rows[-limit:]))


def clear() -> None:
    items.clear()
