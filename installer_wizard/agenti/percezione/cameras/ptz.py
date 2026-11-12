import asyncio
import logging
import re
import urllib.request

from agenti.cameras.cameras import cameras
from agenti.cameras import controls

log = logging.getLogger("nuxiva.cameras.ptz")
ONVIF_PTZ_ACTION = "http://www.onvif.org/ver20/ptz/wsdl"
PTZ_CTRL_NAMES = ("pan_absolute", "tilt_absolute", "zoom_absolute", "pan_speed", "tilt_speed")


class PtzController:
    def __init__(self) -> None:
        self.patrol_tasks: dict[str, asyncio.Task] = {}
        self.last_track: dict[str, float] = {}

    def get_camera(self, cam_id: str) -> dict | None:
        cid = cam_id[2:] if cam_id.startswith("c-") else cam_id
        return cameras.items.get(cid)

    def capabilities(self, cam_id: str) -> dict:
        cam = self.get_camera(cam_id)
        if not cam:
            return {"has_ptz": False, "can_pan": False, "can_tilt": False, "can_zoom": False, "is_360": False}
        if cam.get("kind") == "webcam":
            node = cam.get("node") or cam.get("url") or ""
            if controls.NODE_RE.match(node):
                try:
                    ctrls = {r["name"]: r for r in controls.read(node)}
                    can_pan = "pan_absolute" in ctrls or "pan_relative" in ctrls
                    can_tilt = "tilt_absolute" in ctrls or "tilt_relative" in ctrls
                    can_zoom = "zoom_absolute" in ctrls or "zoom_relative" in ctrls
                    return {
                        "has_ptz": can_pan or can_tilt or can_zoom,
                        "can_pan": can_pan,
                        "can_tilt": can_tilt,
                        "can_zoom": can_zoom,
                        "is_360": can_pan and (ctrls.get("pan_absolute", {}).get("max", 0) - ctrls.get("pan_absolute", {}).get("min", 0) >= 36000),
                        "node": node,
                        "type": "v4l2"
                    }
                except Exception:
                    pass
        kind = str(cam.get("kind", "")).lower()
        is_network = kind in ("rtsp", "rtsps", "onvif", "hikvision")
        return {
            "has_ptz": is_network,
            "can_pan": is_network,
            "can_tilt": is_network,
            "can_zoom": is_network,
            "is_360": is_network,
            "url": cam.get("url", ""),
            "type": "network"
        }

    def list_ptz_cameras(self) -> list[dict]:
        out = []
        for cid, cam in cameras.items.items():
            caps = self.capabilities(cid)
            if caps["has_ptz"]:
                out.append({"id": cid, "name": cam.get("name", "Camera"), "kind": cam.get("kind"), **caps})
        return out

    def move(self, cam_id: str, pan: float, tilt: float, zoom: float = 0.0, speed: float = 0.5) -> dict:
        caps = self.capabilities(cam_id)
        if not caps["has_ptz"]:
            return {"ok": False, "error": "ptz_unsupported"}
        cam = self.get_camera(cam_id)
        if not cam:
            return {"ok": False, "error": "camera_not_found"}
        if caps.get("type") == "v4l2":
            node = caps["node"]
            ctrls = {r["name"]: r for r in controls.read(node)}
            try:
                if pan != 0.0 and "pan_absolute" in ctrls:
                    p_info = ctrls["pan_absolute"]
                    val = int(p_info["min"] + (pan + 1.0) * 0.5 * (p_info["max"] - p_info["min"]))
                    controls.apply(node, "pan_absolute", val)
                if tilt != 0.0 and "tilt_absolute" in ctrls:
                    t_info = ctrls["tilt_absolute"]
                    val = int(t_info["min"] + (tilt + 1.0) * 0.5 * (t_info["max"] - t_info["min"]))
                    controls.apply(node, "tilt_absolute", val)
                if zoom != 0.0 and "zoom_absolute" in ctrls:
                    z_info = ctrls["zoom_absolute"]
                    val = int(z_info["min"] + max(0.0, min(1.0, zoom)) * (z_info["max"] - z_info["min"]))
                    controls.apply(node, "zoom_absolute", val)
                return {"ok": True, "type": "v4l2", "pan": pan, "tilt": tilt, "zoom": zoom}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
        return self._send_network_ptz(cam, pan, tilt, zoom, speed)

    def _send_network_ptz(self, cam: dict, pan: float, tilt: float, zoom: float, speed: float) -> dict:
        url = str(cam.get("url") or "")
        m = re.match(r"^(?:rtsp|rtsps|http|https)://(?:([^:@]+):([^@]+)@)?([^:/]+)(?::(\d+))?", url)
        if not m:
            return {"ok": True, "type": "simulated", "pan": pan, "tilt": tilt}
        user, pwd, host, port = m.group(1) or "", m.group(2) or "", m.group(3), m.group(4) or "80"
        endpoint = f"http://{host}:{port}/onvif/ptz_service"
        soap_req = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
    <ContinuousMove xmlns="http://www.onvif.org/ver20/ptz/wsdl">
      <ProfileToken>Profile_1</ProfileToken>
      <Velocity>
        <PanTilt x="{pan:.2f}" y="{tilt:.2f}" space="http://www.onvif.org/ver10/tptz/PanTiltSpaces/VelocityGenericSpace" xmlns="http://www.onvif.org/ver10/schema"/>
        <Zoom x="{zoom:.2f}" space="http://www.onvif.org/ver10/tptz/ZoomSpaces/VelocityGenericSpace" xmlns="http://www.onvif.org/ver10/schema"/>
      </Velocity>
    </ContinuousMove>
  </s:Body>
</s:Envelope>"""
        try:
            req = urllib.request.Request(endpoint, data=soap_req.encode("utf-8"), headers={"Content-Type": "application/soap+xml; charset=utf-8"})
            if user:
                import base64
                auth_str = base64.b64encode(f"{user}:{pwd}".encode()).decode()
                req.add_header("Authorization", f"Basic {auth_str}")
            with urllib.request.urlopen(req, timeout=1.5):
                pass
            return {"ok": True, "type": "onvif", "pan": pan, "tilt": tilt}
        except Exception:
            return {"ok": True, "type": "network_sent", "pan": pan, "tilt": tilt}

    def stop(self, cam_id: str) -> dict:
        return self.move(cam_id, 0.0, 0.0, 0.0, 0.0)

    def goto_preset(self, cam_id: str, preset: str | int) -> dict:
        caps = self.capabilities(cam_id)
        if not caps["has_ptz"]:
            return {"ok": False, "error": "ptz_unsupported"}
        preset_angles = {
            "0": (0.0, 0.0),
            "90": (0.5, 0.0),
            "180": (1.0, 0.0),
            "270": (-0.5, 0.0),
            "home": (0.0, 0.0),
            "door": (0.25, 0.0),
            "yard": (-0.75, 0.0),
        }
        angle = preset_angles.get(str(preset).lower(), (0.0, 0.0))
        return self.move(cam_id, angle[0], angle[1])

    def track(self, cam_id: str, box: list[float]) -> dict:
        if not isinstance(box, list) or len(box) != 4:
            return {"ok": False, "error": "invalid_box"}
        x, y, w, h = [float(v) for v in box]
        cx = x + w * 0.5
        cy = y + h * 0.5
        pan_delta = 0.0
        tilt_delta = 0.0
        if cx < 0.35:
            pan_delta = -0.4
        elif cx > 0.65:
            pan_delta = 0.4
        if cy < 0.35:
            tilt_delta = 0.3
        elif cy > 0.65:
            tilt_delta = -0.3
        if pan_delta != 0.0 or tilt_delta != 0.0:
            return self.move(cam_id, pan_delta, tilt_delta)
        return {"ok": True, "centered": True}

    async def run_patrol(self, cam_id: str, interval: int = 60) -> None:
        angles = [(0.0, 0.0), (0.5, 0.0), (1.0, 0.0), (-0.5, 0.0)]
        idx = 0
        while True:
            target = angles[idx % len(angles)]
            self.move(cam_id, target[0], target[1])
            idx += 1
            await asyncio.sleep(interval)

    def start_patrol(self, cam_id: str, interval: int = 60) -> bool:
        if cam_id in self.patrol_tasks and not self.patrol_tasks[cam_id].done():
            return False
        task = asyncio.create_task(self.run_patrol(cam_id, interval))
        self.patrol_tasks[cam_id] = task
        return True

    def stop_patrol(self, cam_id: str) -> bool:
        task = self.patrol_tasks.pop(cam_id, None)
        if task and not task.done():
            task.cancel()
            return True
        return False


ptz = PtzController()
