import ipaddress
import re

MAC = re.compile(r"^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$")
LAN = tuple(ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16", "100.64.0.0/10", "127.0.0.0/8", "0.0.0.0/8",
    "::1/128", "fc00::/7", "fe80::/10", "::/128"))
MAX_TEXT = 64


def ip(raw: str):
    text = str(raw).strip()
    if "%" in text or not text:
        return None
    try:
        value = ipaddress.ip_address(text)
    except ValueError:
        return None
    if value.version == 6 and value.ipv4_mapped is not None:
        return value.ipv4_mapped
    return value


def mac(raw: str) -> str | None:
    text = "".join(c.lower() if "A" <= c <= "Z" else c for c in str(raw).strip()).replace("-", ":")
    return text if MAC.match(text) else None


def canonical(raw: str) -> str:
    value = ip(raw)
    if value is not None:
        return str(value)
    found = mac(raw)
    if found:
        return found
    return "".join(c.lower() if "A" <= c <= "Z" else c for c in str(raw).strip())


def clean(raw) -> str | None:
    text = str(raw or "").strip()
    if not text or not all(33 <= ord(c) <= 126 for c in text):
        return None
    return canonical(text)[:MAX_TEXT]


def network(raw: str):
    found = mac(raw)
    if found:
        return ("mac", found)
    text = str(raw).strip()
    addr, slash, bits = text.partition("/")
    value = ip(addr)
    if value is None:
        return None
    if slash:
        if not bits.isdigit() or not bits.isascii():
            return None
        prefix = int(bits)
    else:
        prefix = value.max_prefixlen
    if prefix > value.max_prefixlen or prefix > 255:
        return None
    return ("ip", ipaddress.ip_network(f"{value}/{prefix}", strict=False))


def address(raw: str):
    value = ip(raw)
    if value is not None:
        return ("ip", value)
    found = mac(raw)
    return ("mac", found) if found else None


def contains(net, addr) -> bool:
    if net[0] != addr[0]:
        return False
    if net[0] == "mac":
        return net[1] == addr[1]
    return net[1].version == addr[1].version and addr[1] in net[1]


def is_lan(addr) -> bool:
    if addr[0] == "mac":
        return True
    return any(addr[1].version == n.version and addr[1] in n for n in LAN)
