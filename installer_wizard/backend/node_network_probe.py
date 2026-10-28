from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple


def _valid_ip(val: str) -> bool:
    try:
        ipaddress.ip_address(val.strip())
        return True
    except ValueError:
        return False


def _is_stub_dns(ip_str: str) -> bool:
    s = ip_str.strip()
    return s in ("127.0.0.53", "127.0.0.1", "::1", "0.0.0.0")


def parse_proc_net_route(content: str) -> Tuple[Dict[str, str], Optional[str]]:
    iface_gws: Dict[str, str] = {}
    candidates: List[Tuple[int, str, str]] = []
    for line in (content or "").splitlines()[1:]:
        parts = line.split()
        if len(parts) < 8:
            continue
        iface, dest, gw_hex, flags_hex = parts[0], parts[1], parts[2], parts[3]
        try:
            flags = int(flags_hex, 16)
            metric = int(parts[6])
        except ValueError:
            continue
        if dest != "00000000" or not (flags & 0x2) or len(gw_hex) != 8:
            continue
        try:
            gw_ip = socket.inet_ntoa(bytes.fromhex(gw_hex)[::-1])
        except (ValueError, OSError):
            continue
        if gw_ip != "0.0.0.0" and _valid_ip(gw_ip):
            iface_gws.setdefault(iface, gw_ip)
            candidates.append((metric, iface, gw_ip))
    candidates.sort(key=lambda x: x[0])
    default_gw = candidates[0][2] if candidates else None
    return iface_gws, default_gw


def parse_ip_route_output(stdout_json: str, stdout_text: str) -> Tuple[Dict[str, str], Optional[str]]:
    iface_gws: Dict[str, str] = {}
    candidates: List[Tuple[int, str]] = []
    if stdout_json.strip():
        try:
            routes = json.loads(stdout_json)
            if isinstance(routes, list):
                for r in routes:
                    if not isinstance(r, dict):
                        continue
                    gw = str(r.get("gateway") or "").strip()
                    dev = str(r.get("dev") or "").strip()
                    metric = int(r.get("metric") or 0)
                    if gw and _valid_ip(gw):
                        if dev:
                            iface_gws.setdefault(dev, gw)
                        candidates.append((metric, gw))
        except (ValueError, TypeError):
            pass
    for line in (stdout_text or "").splitlines():
        tokens = line.split()
        if "via" not in tokens:
            continue
        try:
            gw = tokens[tokens.index("via") + 1]
        except IndexError:
            continue
        if not _valid_ip(gw):
            continue
        dev = ""
        if "dev" in tokens:
            idx = tokens.index("dev")
            if idx + 1 < len(tokens):
                dev = tokens[idx + 1]
        metric = 100
        if "metric" in tokens:
            idx = tokens.index("metric")
            if idx + 1 < len(tokens) and tokens[idx + 1].isdigit():
                metric = int(tokens[idx + 1])
        if dev:
            iface_gws.setdefault(dev, gw)
        candidates.append((metric, gw))
    candidates.sort(key=lambda x: x[0])
    return iface_gws, (candidates[0][1] if candidates else None)


def parse_resolv_conf(text: str) -> List[str]:
    upstream: List[str] = []
    stubs: List[str] = []
    for raw in (text or "").splitlines():
        line = raw.split("#", 1)[0].split(";", 1)[0].strip()
        if not line.lower().startswith("nameserver"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        ip_val = parts[1].strip()
        if not _valid_ip(ip_val):
            continue
        if _is_stub_dns(ip_val):
            if ip_val not in stubs:
                stubs.append(ip_val)
        elif ip_val not in upstream:
            upstream.append(ip_val)
    return upstream if upstream else stubs


def parse_resolvectl_dns(text: str) -> Tuple[Dict[str, List[str]], List[str]]:
    per_iface: Dict[str, List[str]] = {}
    global_dns: List[str] = []
    for raw in (text or "").splitlines():
        if ":" not in raw:
            continue
        head, tail = raw.split(":", 1)
        ips = [tok.strip() for tok in tail.split() if _valid_ip(tok.strip()) and not _is_stub_dns(tok.strip())]
        if not ips:
            continue
        if "(" in head and ")" in head:
            ifname = head.split("(", 1)[1].split(")", 1)[0].strip()
            if ifname:
                per_iface[ifname] = ips
        for ip_val in ips:
            if ip_val not in global_dns:
                global_dns.append(ip_val)
    return per_iface, global_dns


def parse_nmcli_devices(text: str) -> Tuple[Dict[str, str], Dict[str, List[str]], Dict[str, str]]:
    gws: Dict[str, str] = {}
    dns_map: Dict[str, List[str]] = {}
    kinds: Dict[str, str] = {}
    cur_dev = ""
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        val = val.strip()
        if key == "GENERAL.DEVICE":
            cur_dev = val
        elif cur_dev and key == "GENERAL.TYPE" and val:
            kinds[cur_dev] = val.lower()
        elif cur_dev and key == "IP4.GATEWAY" and val and val != "--" and _valid_ip(val):
            gws[cur_dev] = val
        elif cur_dev and key.startswith("IP4.DNS") and val and _valid_ip(val):
            lst = dns_map.setdefault(cur_dev, [])
            if val not in lst:
                lst.append(val)
    return gws, dns_map, kinds


def _probe_posix(run_cmd: Callable[..., Any]) -> Dict[str, Any]:
    iface_gws: Dict[str, str] = {}
    iface_dns: Dict[str, List[str]] = {}
    iface_kinds: Dict[str, str] = {}
    iface_modes: Dict[str, str] = {}
    wifi_signals: Dict[str, int] = {}
    default_gw: Optional[str] = None
    global_dns: List[str] = []

    json_route, txt_route = "", ""
    try:
        p = run_cmd(["ip", "-j", "route", "show", "default"], capture_output=True, text=True, timeout=3)
        if p.returncode == 0:
            json_route = p.stdout or ""
    except Exception:
        pass
    if not json_route:
        try:
            p = run_cmd(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=3)
            if p.returncode == 0:
                txt_route = p.stdout or ""
        except Exception:
            pass
    iface_gws, default_gw = parse_ip_route_output(json_route, txt_route)

    proc_route = Path("/proc/net/route")
    if (not default_gw or not iface_gws) and proc_route.is_file():
        try:
            pgws, pdef = parse_proc_net_route(proc_route.read_text(encoding="utf-8", errors="ignore"))
            for k, v in pgws.items():
                iface_gws.setdefault(k, v)
            if not default_gw and pdef:
                default_gw = pdef
        except OSError:
            pass

    try:
        p_nm = run_cmd(
            ["nmcli", "-t", "-f", "GENERAL.DEVICE,GENERAL.TYPE,IP4.GATEWAY,IP4.DNS", "device", "show"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if p_nm.returncode == 0 and p_nm.stdout:
            nm_gws, nm_dns, nm_kinds = parse_nmcli_devices(p_nm.stdout)
            for k, v in nm_gws.items():
                iface_gws.setdefault(k, v)
                if not default_gw:
                    default_gw = v
            for k, v in nm_dns.items():
                iface_dns.setdefault(k, v)
                for ip_val in v:
                    if ip_val not in global_dns and not _is_stub_dns(ip_val):
                        global_dns.append(ip_val)
            iface_kinds.update(nm_kinds)
    except Exception:
        pass

    try:
        p_res = run_cmd(["resolvectl", "dns"], capture_output=True, text=True, timeout=3)
        if p_res.returncode == 0 and p_res.stdout:
            r_iface, r_glob = parse_resolvectl_dns(p_res.stdout)
            for k, v in r_iface.items():
                iface_dns.setdefault(k, v)
            for ip_val in r_glob:
                if ip_val not in global_dns:
                    global_dns.append(ip_val)
    except Exception:
        pass

    for resolv_path in (Path("/run/systemd/resolve/resolv.conf"), Path("/etc/resolv.conf")):
        if resolv_path.is_file():
            try:
                parsed = parse_resolv_conf(resolv_path.read_text(encoding="utf-8", errors="ignore"))
                for ip_val in parsed:
                    if ip_val not in global_dns:
                        global_dns.append(ip_val)
                if global_dns and not all(_is_stub_dns(x) for x in global_dns):
                    global_dns = [x for x in global_dns if not _is_stub_dns(x)]
                    break
            except OSError:
                pass

    try:
        p_addr = run_cmd(["ip", "-j", "-4", "addr", "show"], capture_output=True, text=True, timeout=3)
        if p_addr.returncode == 0 and p_addr.stdout:
            for item in json.loads(p_addr.stdout):
                ifname = str(item.get("ifname") or "")
                for ainfo in item.get("addr_info") or []:
                    if ainfo.get("family") == "inet":
                        iface_modes[ifname] = "dhcp" if ainfo.get("dynamic") else "static"
                        break
    except Exception:
        pass

    wireless_proc = Path("/proc/net/wireless")
    if wireless_proc.is_file():
        try:
            for line in wireless_proc.read_text(encoding="utf-8", errors="ignore").splitlines()[2:]:
                if ":" not in line:
                    continue
                ifname, rest = line.split(":", 1)
                ifname = ifname.strip()
                iface_kinds.setdefault(ifname, "wifi")
                fields = rest.split()
                if len(fields) >= 2:
                    q = float(fields[1].rstrip("."))
                    wifi_signals[ifname] = max(1, min(100, int(round(q * 100 / 70.0)))) if q <= 70 else min(100, int(q))
        except (OSError, ValueError):
            pass

    return {
        "default_gw": default_gw,
        "global_dns": global_dns,
        "iface_gws": iface_gws,
        "iface_dns": iface_dns,
        "iface_kinds": iface_kinds,
        "iface_modes": iface_modes,
        "wifi_signals": wifi_signals,
    }


def _probe_windows(run_cmd: Callable[..., Any]) -> Dict[str, Any]:
    wifi_names = set()
    default_gw: Optional[str] = None
    global_dns: List[str] = []
    try:
        p = run_cmd(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=5)
        for line in (p.stdout or "").splitlines():
            if "Nome" in line or "Name" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    wifi_names.add(parts[1].strip().lower())
    except Exception:
        pass
    try:
        p = run_cmd(
            ["powershell", "-NoProfile", "-Command", "Get-NetIPConfiguration | Select-Object -ExpandProperty IPv4DefaultGateway | Select-Object -ExpandProperty NextHop"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        for ln in (p.stdout or "").splitlines():
            cand = ln.strip()
            if _valid_ip(cand):
                default_gw = cand
                break
        p2 = run_cmd(
            ["powershell", "-NoProfile", "-Command", "Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object -ExpandProperty ServerAddresses"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        for tok in (p2.stdout or "").split():
            if _valid_ip(tok) and tok not in global_dns:
                global_dns.append(tok)
    except Exception:
        pass
    return {
        "default_gw": default_gw,
        "global_dns": global_dns,
        "iface_gws": {},
        "iface_dns": {},
        "iface_kinds": {n: "wifi" for n in wifi_names},
        "iface_modes": {},
        "wifi_signals": {},
    }


def inspect_system_network_interfaces(
    node_ip: Optional[str] = None,
    run_cmd: Callable[..., Any] = subprocess.run,
) -> List[Dict[str, Any]]:
    import psutil

    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    counters = psutil.net_io_counters(pernic=True)
    meta = _probe_windows(run_cmd) if os.name == "nt" else _probe_posix(run_cmd)

    default_gw = meta["default_gw"]
    global_dns = meta["global_dns"]
    interfaces: List[Dict[str, Any]] = []

    for name, addr_list in addrs.items():
        lname = name.lower()
        if "loopback" in lname or name == "lo" or lname.startswith(("docker", "veth", "br-")):
            continue
        stat = stats.get(name)
        cnt = counters.get(name)
        mac, ipv4, netmask = None, None, None
        for a in addr_list:
            fam = getattr(a, "family", None)
            fam_str = str(fam)
            if fam in (-1, getattr(psutil, "AF_LINK", -1)) or "AF_LINK" in fam_str or "AF_PACKET" in fam_str:
                mac = a.address
            elif fam == 2 or "AF_INET" in fam_str:
                if not a.address.startswith("127."):
                    ipv4 = a.address
                    netmask = a.netmask

        nmkind = meta["iface_kinds"].get(name) or meta["iface_kinds"].get(lname, "")
        has_sys_wireless = os.name != "nt" and Path(f"/sys/class/net/{name}/wireless").exists()
        if "wifi" in nmkind or has_sys_wireless or any(w in lname for w in ("wi-fi", "wifi", "wireless", "wlan", "wlp", "wlx", "802.11")):
            kind = "wifi"
        elif "gsm" in nmkind or any(w in lname for w in ("cellular", "wwan", "lte", "gsm", "mobile")):
            kind = "cellular_gsm"
        elif "wireguard" in nmkind or any(w in lname for w in ("wg", "wireguard", "tun", "tap", "vpn")):
            kind = "vpn"
        else:
            kind = "ethernet"

        is_up = bool(stat.isup) if stat else False
        iface_gw = meta["iface_gws"].get(name) or (default_gw if is_up and (ipv4 or node_ip) else None)
        dns_list = meta["iface_dns"].get(name) or global_dns
        dns1 = dns_list[0] if (is_up and len(dns_list) >= 1) else None
        dns2 = dns_list[1] if (is_up and len(dns_list) >= 2) else None

        interfaces.append({
            "name": name,
            "kind": kind,
            "mac_address": mac or "00:00:00:00:00:00",
            "ipv4": ipv4 or (node_ip if is_up else None),
            "netmask": netmask or ("255.255.255.0" if ipv4 else None),
            "gateway": iface_gw if is_up else None,
            "dns_primary": dns1,
            "dns_secondary": dns2,
            "ip_mode": meta["iface_modes"].get(name, "dhcp"),
            "is_up": is_up,
            "speed_mbps": stat.speed if stat else 0,
            "mtu": stat.mtu if stat else 1500,
            "rx_bytes": cnt.bytes_recv if cnt else 0,
            "tx_bytes": cnt.bytes_sent if cnt else 0,
            "signal_percent": meta["wifi_signals"].get(name, 88) if kind == "wifi" and is_up else None,
        })
    return interfaces


def compute_active_route(interfaces: List[Dict[str, Any]], policy: str) -> Dict[str, Any]:
    eth = next((i["name"] for i in interfaces if i["kind"] == "ethernet" and i["is_up"]), None)
    wifi = next((i["name"] for i in interfaces if i["kind"] == "wifi" and i["is_up"]), None)
    cell = next((i["name"] for i in interfaces if i["kind"] == "cellular_gsm" and i["is_up"]), None)
    if policy == "ethernet_only":
        return {"primary_interface": eth or "none", "secondary_interface": None,
                "status": "ethernet_primary_optimal" if eth else "no_interfaces_up",
                "failover_triggered": False, "internet_reachable": bool(eth)}
    if policy == "wifi_only":
        return {"primary_interface": wifi or "none", "secondary_interface": None,
                "status": "wifi_optimal" if wifi else "wifi_disconnected",
                "failover_triggered": False, "internet_reachable": bool(wifi)}
    if policy == "dual_aggregation":
        st = "dual_aggregation_active" if (eth and wifi) else ("ethernet_primary_optimal" if eth else ("wifi_optimal" if wifi else "no_interfaces_up"))
        return {"primary_interface": eth or (wifi or "none"), "secondary_interface": wifi if (eth and wifi) else None,
                "status": st, "failover_triggered": False, "internet_reachable": bool(eth or wifi)}
    if eth:
        return {"primary_interface": eth, "secondary_interface": None, "status": "ethernet_primary_optimal",
                "failover_triggered": False, "internet_reachable": True}
    if wifi:
        return {"primary_interface": wifi, "secondary_interface": None, "status": "failover_to_wifi",
                "failover_triggered": True, "internet_reachable": True}
    if cell:
        return {"primary_interface": cell, "secondary_interface": None, "status": "failover_to_cellular_emergency",
                "failover_triggered": True, "internet_reachable": True}
    return {"primary_interface": "none", "secondary_interface": None, "status": "no_interfaces_up",
            "failover_triggered": True, "internet_reachable": False}


def build_initial_network_profile(node_id: str, real_interfaces: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "node_id": node_id,
        "policy": "fallback",
        "interfaces": real_interfaces,
        "gsm_modem": {
            "modem_id": "wwan_modem_0",
            "operator": "Nuxiva Mesh Cellular LTE-A",
            "technology": "5G SA / LTE-A",
            "signal_bars": 4,
            "signal_dbm": -78,
            "apn": "nuxiva.mesh.iot",
            "roaming_enabled": True,
            "emergency_fallback_only": True,
            "is_connected": any(i["kind"] == "cellular_gsm" and i["is_up"] for i in real_interfaces),
        },
        "vpn": {
            "enabled": True,
            "tunnel_name": "wg-nuxiva0",
            "virtual_ip": "10.42.0.10",
            "endpoint": "mesh-hub.nuxiva.local:51820",
            "handshake_age_secs": 14,
            "bytes_transferred": 8912896,
        },
    }


def merge_refreshed_interfaces(existing: List[Dict[str, Any]], fresh: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    fresh_map = {i["name"]: i for i in fresh}
    merged: List[Dict[str, Any]] = []
    for prev in existing:
        live = fresh_map.pop(prev["name"], None)
        if not live:
            merged.append(prev)
            continue
        if prev.get("ip_mode") == "static":
            merged.append({
                **live,
                "ip_mode": "static",
                "ipv4": prev.get("ipv4") or live.get("ipv4"),
                "netmask": prev.get("netmask") or live.get("netmask"),
                "gateway": prev.get("gateway") or live.get("gateway"),
                "dns_primary": prev.get("dns_primary") or live.get("dns_primary"),
                "dns_secondary": prev.get("dns_secondary") or live.get("dns_secondary"),
            })
        else:
            merged.append(live)
    merged.extend(fresh_map.values())
    return merged
