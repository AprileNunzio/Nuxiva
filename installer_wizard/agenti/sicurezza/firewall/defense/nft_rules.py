import math

from agenti.firewall.defense.honeypot import PORT

SETS = (("tarpit", "tarpit"), ("rate_limit", "limited"), ("honeypot", "decoy"), ("quarantine", "quarantine"),
        ("sinkhole", "sinkhole"))
TYPES = {"4": "ipv4_addr", "6": "ipv6_addr", "mac": "ether_addr"}
FAMILY = {"ip4": "4", "ip6": "6", "mac": "mac"}


def _timeout(expires: float, now: float) -> int:
    return max(1, math.ceil(expires - now)) if expires else 0


def _set(name: str, kind: str, values: list[str], timeout: bool) -> list[str]:
    flags = ("flags interval, timeout" if timeout else "flags interval") if kind != "ether_addr" else "flags timeout"
    lines = [f"    set {name} {{", f"        type {kind}", f"        {flags}"]
    if kind != "ether_addr":
        lines.append("        auto-merge")
    if values:
        lines.append("        elements = { " + ", ".join(values) + " }")
    lines.append("    }")
    return lines


def _range(first: str, last: str) -> str:
    return first if first == last else f"{first}-{last}"


def sets(responses: list, ranges: dict[str, list[tuple[str, str]]], now: float) -> list[str]:
    grouped: dict[str, list[str]] = {}
    for response in responses:
        if response.kind == "country_block" or (response.expires and response.expires <= now):
            continue
        name = dict(SETS)[response.kind]
        suffix = FAMILY[response.family]
        left = _timeout(response.expires, now)
        grouped.setdefault(f"{name}_{suffix}", []).append(f"{response.target} timeout {left}s" if left else response.target)
    lines = []
    for _, name in SETS:
        for suffix, kind in TYPES.items():
            if suffix == "mac" and name != "quarantine":
                continue
            lines += _set(f"{name}_{suffix}", kind, grouped.get(f"{name}_{suffix}", []), True)
    v4, v6 = [], []
    for code in sorted(ranges):
        for first, last in ranges[code]:
            (v6 if ":" in first else v4).append(_range(first, last))
    lines += _set("geo_4", "ipv4_addr", v4, False) + _set("geo_6", "ipv6_addr", v6, False)
    return lines


def input_guard() -> list[str]:
    return [
        f"        meta nfproto ipv4 tcp dport {PORT} ip saddr != @decoy_4 counter drop",
        f"        meta nfproto ipv6 tcp dport {PORT} ip6 saddr != @decoy_6 counter drop",
        "        ip saddr @quarantine_4 counter drop",
        "        ip6 saddr @quarantine_6 counter drop",
        "        ether saddr @quarantine_mac counter drop",
        "        ip saddr @geo_4 counter drop",
        "        ip6 saddr @geo_6 counter drop",
    ]


def input_throttle() -> list[str]:
    return [
        "        ip saddr @tarpit_4 ct state new limit rate over 3/minute burst 3 packets counter drop",
        "        ip6 saddr @tarpit_6 ct state new limit rate over 3/minute burst 3 packets counter drop",
        "        ip saddr @limited_4 limit rate over 50/second burst 100 packets counter drop",
        "        ip6 saddr @limited_6 limit rate over 50/second burst 100 packets counter drop",
    ]


def forward() -> list[str]:
    return [
        "        ip saddr @quarantine_4 counter drop",
        "        ip daddr @quarantine_4 counter drop",
        "        ip6 saddr @quarantine_6 counter drop",
        "        ip6 daddr @quarantine_6 counter drop",
        "        ether saddr @quarantine_mac counter drop",
        "        ip daddr @sinkhole_4 counter drop",
        "        ip6 daddr @sinkhole_6 counter drop",
        "        ip saddr @geo_4 counter drop",
        "        ip6 saddr @geo_6 counter drop",
    ]


def output() -> list[str]:
    return ["        ip daddr @sinkhole_4 counter drop", "        ip6 daddr @sinkhole_6 counter drop"]


def nat() -> list[str]:
    return [
        "    chain decoy {",
        "        type nat hook prerouting priority dstnat; policy accept;",
        f"        ip saddr @decoy_4 meta l4proto tcp tcp dport != {PORT} redirect to :{PORT}",
        f"        ip6 saddr @decoy_6 meta l4proto tcp tcp dport != {PORT} redirect to :{PORT}",
        "    }",
    ]
