import hashlib
import json
import re
import time
from collections import OrderedDict

from agenti.places.store import store


class RoomCapture:
    def __init__(self, window=2.0, capacity=512):
        self.window = window
        self.capacity = capacity
        self.recent: OrderedDict[tuple[str, bytes], tuple[float, object]] = OrderedDict()

    def accepts(self, room: str, source: object, text: str, now: float) -> bool:
        normalized = " ".join(re.findall(r"\w+", text.casefold()))
        if not normalized:
            return True
        key = (room, hashlib.sha256(normalized.encode()).digest())
        while self.recent and now - next(iter(self.recent.values()))[0] >= self.window:
            self.recent.popitem(last=False)
        previous = self.recent.get(key)
        if previous and previous[1] is not source:
            return False
        self.recent[key] = (now, source)
        self.recent.move_to_end(key)
        if len(self.recent) > self.capacity:
            self.recent.popitem(last=False)
        return True


captures = RoomCapture()


def accepts(device: str, source: object, message: str) -> bool:
    room = store.room_of(device)
    if room is None:
        return True
    try:
        event = json.loads(message)
    except (ValueError, RecursionError):
        return True
    if not isinstance(event, dict) or event.get("type") != "transcript" or event.get("origin") is False:
        return True
    text = event.get("text")
    return not isinstance(text, str) or captures.accepts(room.id, source, text, time.monotonic())
