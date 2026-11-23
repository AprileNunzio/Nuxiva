from datetime import datetime

BOOSTS = (
    (range(6, 11), {"weather": 18, "news": 12}),
    (range(11, 15), {"news": 10, "weather": 6}),
    (range(17, 21), {"weather": 10, "sun": 12, "network": 6}),
    (range(21, 24), {"firewall": 8, "network": 8, "resources": 4}),
    (range(0, 6), {"firewall": 10, "resources": 6}),
)


def boost(name: str, when: datetime | None = None) -> int:
    hour = (when or datetime.now()).hour
    return next((table.get(name, 0) for hours, table in BOOSTS if hour in hours), 0)
