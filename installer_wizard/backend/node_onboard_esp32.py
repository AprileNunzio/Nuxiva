from typing import Any, Dict, List

from fastapi import HTTPException, Request


def onboard_esp32(req: Any, request: Request, ports: List[Dict[str, Any]], tier: str) -> Dict[str, Any]:
    from agenti.nodes import esp32
    from agenti.secure import api as secure
    from state import store
    allowed = {p["device"] for p in ports}
    try:
        port = esp32.clean_port(req.usb_port, allowed)
        esp32.clean_credentials(req.wifi_ssid, req.wifi_key, req.name)
    except esp32.Esp32Error as exc:
        raise HTTPException(status_code=400, detail=exc.code)
    try:
        link = esp32.open_port(port)
    except (OSError, ImportError):
        raise HTTPException(status_code=409, detail="esp32.error.port_busy")
    try:
        result = esp32.provision(link, request.url.hostname, secure._active["port"], req.wifi_ssid, req.wifi_key, req.name)
    except esp32.Esp32Error as exc:
        raise HTTPException(status_code=409, detail=exc.code)
    finally:
        link.close()
    store.event("INFO", f"Nodo ESP32 {result['node_id']} configurato via USB", "nodes")
    return {"node_id": result["node_id"], "name": result["name"], "target": "esp32", "tier": tier,
            "status": "enrolled", "parent_id": req.parent_id, "message": "esp32.onboard.done",
            "fingerprint": result["fingerprint"], "pairing_code": result["pairing_code"],
            "firmware": result["firmware"], "flash_encrypted": result["flash_encrypted"]}
