import logging
import socket
from pathlib import Path

log = logging.getLogger("nuxiva.tv_tuners")


def detect_real_tuners() -> list[dict]:
    """Scansiona esclusivamente dispositivi reali DVB e ricevitori tuner di rete."""
    found: list[dict] = []

    # 1. Adattatori hardware DVB Linux reali (/dev/dvb/adapter*)
    dvb_root = Path("/dev/dvb")
    if dvb_root.exists() and dvb_root.is_dir():
        for adapter_dir in sorted(dvb_root.glob("adapter*")):
            fe_path = adapter_dir / "frontend0"
            if not fe_path.exists():
                continue
            fe_name = f"DVB-T/T2 ({adapter_dir.name})"
            sys_device = Path(f"/sys/class/dvb/{adapter_dir.name}frontend0/device")
            for name_candidate in ("model", "name"):
                cand_path = sys_device / name_candidate
                if cand_path.exists():
                    try:
                        fe_name = cand_path.read_text(encoding="utf-8").strip()
                        break
                    except Exception:
                        pass
            found.append({
                "id": f"dvb_{adapter_dir.name}",
                "name": fe_name,
                "type": "dvb_t2",
                "device": str(adapter_dir),
                "status": "online",
                "signal_strength": 0,
                "signal_quality": 0,
                "channels_count": 0,
                "last_scan": 0,
                "frequency_band": "VHF/UHF (174-790 MHz)",
                "auto_detected": True,
            })

    # 2. HDHomeRun broadcast discovery UDP reale sulla rete locale (porta 65001)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.5)
        # Pacchetto discovery standard HDHomeRun
        pkt = b"\x00\x01\x00\x08\x01\x04\xff\xff\xff\xff\x02\x04\xff\xff\xff\xff"
        sock.sendto(pkt, ("255.255.255.255", 65001))
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                ip = addr[0]
                t_id = f"hdhomerun_{ip.replace('.', '_')}"
                if not any(t["id"] == t_id for t in found):
                    found.append({
                        "id": t_id,
                        "name": f"HDHomeRun ({ip})",
                        "type": "hdhomerun",
                        "device": f"http://{ip}:65001",
                        "status": "online",
                        "signal_strength": 0,
                        "signal_quality": 0,
                        "channels_count": 0,
                        "last_scan": 0,
                        "frequency_band": "DVB-T/T2 Network IP",
                        "auto_detected": True,
                    })
            except (socket.timeout, TimeoutError):
                break
        sock.close()
    except Exception as exc:
        log.debug("Discovery HDHomeRun broadcast non disponibile: %s", exc)

    return found
