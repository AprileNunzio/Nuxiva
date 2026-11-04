import json
import re
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Ok, Result
from server.core.skill_forge.ast_scanner import ALLOWED_MODULES
from server.core.skill_forge.contracts import MAX_SOURCE_CHARS

PREFIX = "auto."
MIN_CASES = 3
FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")

SYSTEM = (
    "You write tiny deterministic skills for a voice assistant. A skill is a pure Python function that turns "
    "already-extracted slot values into one sentence of speech. Reply with a single JSON object and nothing else.\n"
    "If the requests cannot be answered by a pure computation on the slots (they need live data, the web, the current "
    "time, devices, files, personal data or opinions), reply exactly {\"forgeable\": false}.\n"
    "Otherwise reply {\"forgeable\": true, \"neuron_id\": \"auto.<short_snake_name>\", \"title\": \"...\", "
    "\"slot_schema\": [{\"name\": \"...\", \"entity_label\": \"...\", \"data_type\": \"number|string|enumeration\", "
    "\"required\": true}], \"utterances\": [at least 8 varied phrasings of the request in the users' language], "
    "\"source\": \"python source\", \"cases\": [{\"slots\": {...}, \"expect_speech\": \"...\"}, at least 3]}.\n"
    "Rules for source: define run(slots) returning {\"speech\": str}; import only from: " + ", ".join(sorted(ALLOWED_MODULES)) +
    "; no classes, no str.format, no eval/exec/open/getattr/type, no I/O, no randomness, no clock; the speech is in the "
    "users' language; every expect_speech must be exactly what run returns for those slots."
)


@dataclass(frozen=True, slots=True)
class Authored:
    manifest: dict[str, Any]
    source: str


def prompt(examples: Sequence[str]) -> str:
    lines = "\n".join(f"- {item}" for item in examples)
    return f"Recurring requests the assistant could not answer without a language model:\n{lines}\nWrite the skill."


def _object(raw: str) -> Optional[dict[str, Any]]:
    text = FENCE.sub("", raw.strip())
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def parse(raw: str) -> Result[Optional[Authored], CortexFailure]:
    data = _object(raw)
    if data is None:
        return fail("cortex.forge.author_invalid")
    if data.get("forgeable") is not True:
        return Ok(None)
    source = data.get("source")
    neuron_id = data.get("neuron_id")
    if not isinstance(source, str) or not 0 < len(source) <= MAX_SOURCE_CHARS or not isinstance(neuron_id, str):
        return fail("cortex.forge.author_invalid")
    cases = data.get("cases")
    if not isinstance(cases, list) or len(cases) < MIN_CASES:
        return fail("cortex.forge.author_invalid")
    manifest = {key: data.get(key) for key in ("title", "slot_schema", "utterances", "cases")}
    manifest["neuron_id"] = neuron_id if neuron_id.startswith(PREFIX) else PREFIX + neuron_id.lstrip(".")
    return Ok(Authored(manifest, source))
