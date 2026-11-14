import ctypes
import hmac
import re
import sys
from pathlib import Path

from app import runtime_check  # noqa: E402

if "--smoke-test" in sys.argv:
    sys.exit(runtime_check.smoke())
STARTUP_CODE = runtime_check.ensure()
if STARTUP_CODE:
    sys.exit(STARTUP_CODE)

from app.errors import configure_logging, errors  # noqa: E402
from autonomy import profile  # noqa: E402
from connection import enroll  # noqa: E402
from connection.devicekey import DeviceKey  # noqa: E402
from connection.client import Client, first_contact  # noqa: E402
from i18n.strings import t  # noqa: E402
from settings import autostart, paths, store  # noqa: E402

MUTEX_NAME = "NUXIVA_Assistente_Windows"
ERROR_ALREADY_EXISTS = 183


def single_instance() -> bool:
    ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    return ctypes.windll.kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def verify(address: str) -> tuple[str, str]:
    return first_contact(store.normalize_server(address))


def pair(cfg: dict, address: str, code: str, name: str, start_with_windows: bool, fingerprint: str) -> None:
    server = store.normalize_server(address)
    if not server:
        raise ValueError("Scrivi l'indirizzo di NUXIVA")
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("Il codice deve avere 6 cifre")
    current, ca_pem = first_contact(server)
    if not hmac.compare_digest(current, fingerprint):
        raise ValueError("Il certificato di NUXIVA è cambiato durante l'abbinamento: premi di nuovo «Verifica»")
    name = name or cfg["name"]
    node_id = store.node_id_for(name)
    key = DeviceKey.generate()
    token = Client(server, node_id, "", ca_pem, key).pair(code, name)
    cfg.update(server=server, name=name, node_id=node_id, token=token, pin=fingerprint, ca=ca_pem, key=key.seed_hex())
    store.save(cfg)
    autostart.set_enabled(start_with_windows)


def auto_enroll(cfg: dict, source: tuple[str, Path] | None = None) -> bool:
    kind, path = source or ("file", paths.APP_DIR / enroll.ENROLL_FILE)
    try:
        data = enroll.load_trailer(path) if kind == "installer" else enroll.load(path)
        if data is None:
            return False
        enroll.redeem(cfg, data, first_contact)
    except enroll.EnrollError as exc:
        ctypes.windll.user32.MessageBoxW(None, t("enroll.failed", reason=t(exc.key)), "Nuxiva", 0x30)
        return False
    if kind == "file":
        enroll.wipe(path)
    autostart.set_enabled(True)
    return True


def main() -> None:
    configure_logging()
    errors.install()
    if not single_instance():
        ctypes.windll.user32.MessageBoxW(None, "NUXIVA è già in esecuzione: cerca la sfera luminosa nell'angolo dello schermo.",
                                         "Nuxiva", 0x40)
        return
    cfg = store.load()
    autostart.refresh()
    source = enroll.enrollment_source(sys.argv)
    local_only = profile.parse_mode(cfg.get("mode")) is profile.Mode.LOCAL
    if (not cfg["token"] or not cfg["ca"]) and not local_only and not auto_enroll(cfg, source):
        from ui.pairing_view import PairingWindow
        window = PairingWindow(cfg, verify, lambda *values: pair(cfg, *values))
        if not window.run():
            return
        if window.standalone:
            cfg["mode"] = profile.Mode.LOCAL.value
            store.save(cfg)
            autostart.set_enabled(True)
    from app.assistant import Assistant
    Assistant(cfg).start()


if __name__ == "__main__":
    sys.exit(main())
