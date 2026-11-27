import asyncio
import logging
import re
import time

from agenti.brain import inflight
from agenti.chat.addressee import get_name_re
from agenti.chat.dialogue import dialogue

log = logging.getLogger("nuxiva.chat.anticipate")

MAX_TEXT = 400
MIN_WORDS = 2
LEAD = re.compile(r"^[\s,.;:!?¡¿\-]+")
stats = {"thought": 0, "skipped": 0, "failed": 0}
recent: dict[str, float] = {}


def command_of(text: str) -> str:
    clean = str(text or "")[:MAX_TEXT].strip()
    named = get_name_re().match(LEAD.sub("", clean))
    if named:
        clean = clean[clean.lower().find(named.group(0).lower()) + len(named.group(0)):]
    return LEAD.sub("", clean).strip()


def worth(text: str) -> bool:
    words = inflight.key(text).split()
    if len(words) < MIN_WORDS:
        return False
    key = " ".join(words)
    now = time.monotonic()
    if now - recent.get(key, -60.0) < 60.0:
        return False
    recent[key] = now
    if len(recent) > 128:
        for old in sorted(recent, key=recent.get)[:64]:
            del recent[old]
    return True


async def _lookup(text: str) -> None:
    from agenti.agent import commands as agent_cmd
    from agenti.agent import grounding
    from agenti.chat import code
    if agent_cmd.enabled() and not code.wanted(text) and not agent_cmd.weak(text):
        await grounding.needs_lookup(text)


async def _orchestrate(text: str) -> None:
    from agenti.team import learning, reasoning, routing
    from agenti.team.ceo import ceo
    agents = ceo.scan_team()
    routed = routing.router.decide(agents, text, learning.table(), learning.version)
    if reasoning.needs_reasoning(routed["ranked"], routed["conversational"]):
        await reasoning.think(text, agents, routed["ranked"])


async def think_ahead(text: str, device: str) -> bool:
    command = command_of(text)
    if not worth(command):
        stats["skipped"] += 1
        return False
    resolved = dialogue.resolve(device, command)
    results = await asyncio.gather(_lookup(resolved), _orchestrate(resolved), return_exceptions=True)
    failures = [r for r in results if isinstance(r, Exception)]
    for failure in failures:
        log.warning("Ragionamento anticipato interrotto: %s", type(failure).__name__)
    stats["failed" if failures else "thought"] += 1
    return not failures
