import importlib
import importlib.util
import logging
import sys
from pathlib import Path

from i18n.strings import t

log = logging.getLogger("nuxiva.runtime")

THEMES = ("blue.json", "dark-blue.json", "green.json")
FONT_SUFFIXES = (".otf", ".ttf")
EXIT_ASSETS = 3
EXIT_TOOLKIT = 4


def toolkit_root() -> Path | None:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return base / "customtkinter"
    spec = importlib.util.find_spec("customtkinter")
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(next(iter(spec.submodule_search_locations)))


def missing_assets(root: Path | None) -> list[str]:
    if root is None or not root.is_dir():
        return ["customtkinter"]
    absent = [f"assets/themes/{name}" for name in THEMES if not (root / "assets" / "themes" / name).is_file()]
    fonts = root / "assets" / "fonts"
    if not fonts.is_dir() or not any(path.suffix.lower() in FONT_SUFFIXES for path in fonts.rglob("*") if path.is_file()):
        absent.append("assets/fonts")
    return absent


def report(message: str, interactive: bool) -> None:
    log.error("%s", message)
    print(message, file=sys.stderr)
    if interactive and sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "Nuxiva", 0x10)


def ensure(interactive: bool = True) -> int:
    absent = missing_assets(toolkit_root())
    if absent:
        report(t("startup.assets_missing", files=", ".join(absent)), interactive)
        return EXIT_ASSETS
    try:
        toolkit = importlib.import_module("customtkinter")
        toolkit.ThemeManager.theme["CTkButton"]
    except (ImportError, OSError, ValueError, KeyError) as exc:
        report(t("startup.toolkit_failed", reason=str(exc)), interactive)
        return EXIT_TOOLKIT
    return 0


def smoke() -> int:
    code = ensure(interactive=False)
    if code:
        return code
    for module in ("ui.theme", "ui.pairing_view", "ui.panel"):
        try:
            importlib.import_module(module)
        except (ImportError, OSError) as exc:
            report(t("startup.toolkit_failed", reason=f"{module}: {exc}"), False)
            return EXIT_TOOLKIT
    return 0
