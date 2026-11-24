import asyncio
import logging
from typing import Optional, Tuple

from config import STATE_DIR, env_get
from tasks import background

from agenti.brain.llm import generate
from agenti.presentation.application.gate import MODES, worth_planning
from agenti.presentation.application.planner import PresentationPlanner
from agenti.presentation.infrastructure.commons_images import CommonsImages, http_fetchers
from agenti.presentation.infrastructure.image_store import ImageStore
from agenti.study.constants import USER_AGENT

logger = logging.getLogger("nuxiva.presentation")

ROUTE = "/api/presentation/image"
BUDGET_SECONDS = 45.0
INLINE_SECONDS = 12.0
WIDGET_SECONDS = 180
image_store = ImageStore(STATE_DIR / "presentation" / "images")


class _Models:
    def request(self, subject: str) -> None:
        from agenti.models3d.commands import _build
        background(_build(subject))


async def _complete(system: str, user: str) -> dict:
    return await generate(user, as_json=True, system=system, max_tokens=1800, temperature=0.2, kind="chat",
                          component="presentation", timeout=60)


_fetch_json, _fetch_bytes = http_fetchers(USER_AGENT)
planner = PresentationPlanner(_complete, CommonsImages(_fetch_json, _fetch_bytes, image_store, ROUTE), _Models())


def _wanted(question: str, reply: str) -> bool:
    mode = env_get("NUXIVA_PRESENTATION", "smart")
    return worth_planning(question, reply, mode if mode in MODES else "smart")


def compose_later(question: str, reply: str) -> bool:
    if not _wanted(question, reply):
        return False
    background(_brief(question, reply))
    return True


async def _brief(question: str, reply: str) -> None:
    try:
        outcome = await asyncio.wait_for(planner.compose(question, reply, widget_only=True), BUDGET_SECONDS)
    except asyncio.TimeoutError:
        logger.info("background presentation planning timed out")
        return
    if outcome is not None and outcome.widget:
        from agenti.desktop.desk import desk
        desk.show("brief", outcome.widget, ttl=WIDGET_SECONDS)


async def compose(question: str, reply: str) -> Optional[Tuple[str, dict]]:
    if not _wanted(question, reply):
        return None
    try:
        outcome = await asyncio.wait_for(planner.compose(question, reply), INLINE_SECONDS)
    except asyncio.TimeoutError:
        logger.info("presentation planning timed out")
        return None
    if outcome is None:
        return None
    if outcome.widget:
        from agenti.desktop.desk import desk
        desk.show("brief", outcome.widget, ttl=WIDGET_SECONDS)
        return outcome.speech, {"mode": "face"}
    if outcome.ui.get("mode") == "face":
        return reply, {"mode": "face"}
    return outcome.speech, outcome.ui
