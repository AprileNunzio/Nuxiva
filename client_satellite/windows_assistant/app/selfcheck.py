from connection import diagnose
from connection.client import ServerError, first_contact
from i18n.strings import t
from permissions import os_access
from settings import store


def run() -> str:
    cfg = store.load()
    lines = []
    server = cfg.get("server") or ""
    if not server:
        lines.append(t("net.no_address"))
    else:
        try:
            first_contact(server)
            lines.append(t("selfcheck.server_ok", server=server))
        except ServerError as exc:
            lines.append(str(exc))
        lines.extend(["", *diagnose.probe(server)])
    lines.extend(["", t("selfcheck.permissions"), *os_access.describe_all()])
    return "\n".join(lines)
