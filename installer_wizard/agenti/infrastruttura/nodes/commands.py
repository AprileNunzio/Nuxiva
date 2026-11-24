import asyncio
import json
from functools import lru_cache
from pathlib import Path

from config import read_env

from agenti.chat import context as request_context
from agenti.nodes import screenshot_bridge, screenshot_intent

LANGUAGES = ("it", "en", "fr", "es")
WAIT = 8.0
STEP = 0.2
DIRECTORY = Path(__file__).resolve().parent / "language"


@lru_cache(maxsize=len(LANGUAGES))
def _phrases(lang: str) -> dict:
    data = json.loads((DIRECTORY / f"{lang}.json").read_text(encoding="utf-8"))
    return data.get("screenshot_voice") or {}


def phrase(key: str, lang: str | None = None, **values) -> str:
    lang = lang if lang in LANGUAGES else (read_env().get("NUXIVA_UI_LANG") or "it")
    lang = lang if lang in LANGUAGES else "it"
    template = _phrases(lang).get(key) or _phrases("it").get(key) or key
    return template.format(**values)


async def _outcome(previous: int) -> dict | None:
    waited = 0.0
    while waited < WAIT:
        await asyncio.sleep(STEP)
        waited += STEP
        report = screenshot_bridge.latest()
        if report and report["id"] > previous and report["status"] != "delivered_later":
            return report
    return None


async def answer(text: str) -> tuple[str, dict]:
    if not screenshot_intent.asks(text):
        raise LookupError
    ui = {"mode": "face"}
    if request_context.device.get() != "kiosk":
        return phrase("remote"), ui
    before = screenshot_bridge.latest()
    try:
        screenshot_bridge.request()
    except screenshot_bridge.BridgeUnavailable:
        return phrase("service"), ui
    report = await _outcome(before["id"] if before else 0)
    if report is None:
        return phrase("timeout"), ui
    return phrase(report["status"], folder=report["folder"]), ui
