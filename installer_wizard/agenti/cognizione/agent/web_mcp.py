from agenti.mcpclient.area import Area

SERVER = "web"
AREA = "NUXIVA_MCP_AREA_WEB"


def definition() -> dict:
    return {"id": SERVER, "kind": "fetch", "config": {}}


area = Area(SERVER, AREA, definition)
active = area.active
needs_consent = area.needs_consent
consent = area.consent
call = area.call
