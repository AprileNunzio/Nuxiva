from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

try:
    from nuxiva_native import RustAdminOsNotification  # type: ignore
except ImportError:
    RustAdminOsNotification = None  # type: ignore


@dataclass
class OSNotification:
    id: str
    level: str
    code: str
    label_key: str
    message: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)
    action: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NotificationManager:
    def __init__(self, max_history: int = 100, cooldown_s: float = 60.0) -> None:
        self.max_history = max_history
        self.cooldown_s = cooldown_s
        self._items: List[OSNotification] = []
        self._last_alert_time: Dict[str, float] = {}
        if RustAdminOsNotification is not None:
            self._rust_engine = RustAdminOsNotification(max_history, int(cooldown_s))
        else:
            self._rust_engine = None

    def notify(
        self,
        level: str,
        code: str,
        label_key: str,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        action: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> Optional[OSNotification]:
        now = time.time()
        if self._rust_engine is not None:
            res = self._rust_engine.notify(level, code, code, int(now), force)
            if res is None:
                return None
        else:
            last = self._last_alert_time.get(code, 0.0)
            if not force and (now - last < self.cooldown_s):
                return None
            self._last_alert_time[code] = now

        notification = OSNotification(
            id=f"notif_{uuid.uuid4().hex[:12]}",
            level=level.upper(),
            code=code,
            label_key=label_key,
            message=message,
            timestamp=now,
            details=details or {},
            action=action,
        )

        self._items.insert(0, notification)
        if len(self._items) > self.max_history:
            self._items.pop()

        self._broadcast(notification)
        return notification

    def _broadcast(self, notification: OSNotification) -> None:
        try:
            from nuxiva_bus import nuxiva_bus
            payload = {
                "labelKey": notification.label_key,
                "code": notification.code,
                "level": notification.level,
                "message": notification.message,
                "details": notification.details,
                "action": notification.action,
            }
            nuxiva_bus.publish("ui.notification.notice", payload, origin="os")
        except Exception:
            pass

    def get_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [item.to_dict() for item in self._items[:limit]]

    def clear(self) -> None:
        self._items.clear()
        self._last_alert_time.clear()
        if self._rust_engine is not None:
            self._rust_engine.clear()

    def count(self) -> int:
        if self._rust_engine is not None:
            return self._rust_engine.count()
        return len(self._items)


notification_manager = NotificationManager()
