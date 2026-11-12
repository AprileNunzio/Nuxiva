import ipaddress
import re
import socket
import time
from typing import Any, Dict, List, Optional

MDNS_GROUP = "224.0.0.251"
MDNS_PORT = 5353
MATTER_PORT = 5540

MATTERC_QUERY = b"\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x08_matterc\x04_udp\x05local\x00\x00\x0c\x00\x01"

class MatterDiscovery:
    def __init__(self, timeout: float = 1.5):
        self.timeout = timeout

    @staticmethod
    def _local_ip() -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
        finally:
            s.close()

    def discover_commissionable(self) -> List[Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(self.timeout)
        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.sendto(MATTERC_QUERY, (MDNS_GROUP, MDNS_PORT))
        except Exception:
            pass

        start = time.time()
        while time.time() - start < self.timeout:
            try:
                data, addr = sock.recvfrom(2048)
                ip = addr[0]
                parsed = self._parse_mdns_response(data, ip)
                if parsed:
                    results[ip] = parsed
            except socket.timeout:
                break
            except Exception:
                continue
        sock.close()

        if not results:
            local_ip = self._local_ip()
            if local_ip != "127.0.0.1":
                results.update(self._probe_subnet_matter_nodes(local_ip))

        return list(results.values())

    def _probe_subnet_matter_nodes(self, local_ip: str) -> Dict[str, Dict[str, Any]]:
        found: Dict[str, Dict[str, Any]] = {}
        try:
            net = ipaddress.ip_network(f"{local_ip}/24", strict=False)
        except Exception:
            return found

        for host in list(net.hosts())[:15]:
            ip_str = str(host)
            if ip_str == local_ip:
                continue
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.04)
            try:
                s.sendto(b"\x00\x00\x00\x00", (ip_str, MATTER_PORT))
                s.close()
            except Exception:
                s.close()
        return found

    def _parse_mdns_response(self, data: bytes, ip: str) -> Optional[Dict[str, Any]]:
        try:
            text = data.decode("latin1", errors="ignore")
        except Exception:
            return None

        if "_matterc" not in text and "_matter" not in text:
            return None

        vendor_id = 0xFFF1
        product_id = 0x8001
        discriminator = 3840
        device_type = 0x0100
        device_name = f"Matter-{ip.replace('.', '')[-4:]}"

        vp_match = re.search(r"VP=([0-9a-fA-F]+)\+([0-9a-fA-F]+)", text)
        if vp_match:
            try:
                vendor_id = int(vp_match.group(1), 16)
                product_id = int(vp_match.group(2), 16)
            except Exception:
                pass

        d_match = re.search(r"D=(\d+)", text)
        if d_match:
            try:
                discriminator = int(d_match.group(1))
            except Exception:
                pass

        dt_match = re.search(r"DT=(\d+)", text)
        if dt_match:
            try:
                device_type = int(dt_match.group(1))
            except Exception:
                pass

        dn_match = re.search(r"DN=([^\x00-\x1f]+)", text)
        if dn_match:
            device_name = dn_match.group(1).strip()

        return {
            "ip": ip,
            "port": MATTER_PORT,
            "discriminator": discriminator,
            "vendor_id": vendor_id,
            "product_id": product_id,
            "device_type": device_type,
            "device_name": device_name,
            "commissionable": True,
            "discovered_at": time.time(),
        }
