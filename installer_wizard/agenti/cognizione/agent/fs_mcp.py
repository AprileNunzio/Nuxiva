from agenti.agent import paths
from agenti.mcpclient.area import Area

SERVER = "files"
AREA = "NUXIVA_MCP_AREA_FILES"
WRITE_BYTES = 64 * 1024 * 1024
DEPTH = 24


def definition() -> dict:
    roots = []
    for name, path in (("work", paths.WORK), ("models", paths.MODELS)):
        path.mkdir(parents=True, exist_ok=True)
        roots.append({"name": name, "path": str(path), "mode": "write", "max_bytes": WRITE_BYTES, "max_depth": DEPTH})
    paths.TRASH.mkdir(parents=True, exist_ok=True)
    return {"id": SERVER, "kind": "filesystem", "config": {"roots": roots, "default_root": "work", "trash": str(paths.TRASH)}}


area = Area(SERVER, AREA, definition)
active = area.active
ensure = area.ensure
needs_consent = area.needs_consent
consent = area.consent
call = area.call
