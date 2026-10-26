import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Ok, Result

NEURON_ID = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
MAX_TITLE = 80
MAX_UTTERANCES = 64
MAX_UTTERANCE_CHARS = 200
MAX_SLOTS = 16
MAX_CASES = 16
MAX_SOURCE_CHARS = 20_000
MAX_SPEECH_CHARS = 2_000


@dataclass(frozen=True, slots=True)
class SkillCase:
    slots: Mapping[str, Any]
    expect_speech: str


@dataclass(frozen=True, slots=True)
class SkillManifest:
    neuron_id: str
    title: str
    slot_schema: tuple[Mapping[str, Any], ...]
    utterances: tuple[str, ...]
    cases: tuple[SkillCase, ...]

    @staticmethod
    def parse(data: Any) -> Result["SkillManifest", CortexFailure]:
        if not isinstance(data, Mapping):
            return fail("cortex.forge.manifest_invalid")
        neuron_id, title = data.get("neuron_id"), data.get("title")
        schema, utterances, cases = data.get("slot_schema", []), data.get("utterances"), data.get("cases")
        if not isinstance(neuron_id, str) or not NEURON_ID.match(neuron_id):
            return fail("cortex.forge.manifest_invalid")
        if not isinstance(title, str) or not 0 < len(title.strip()) <= MAX_TITLE:
            return fail("cortex.forge.manifest_invalid")
        if not isinstance(schema, list) or len(schema) > MAX_SLOTS or not all(
            isinstance(item, Mapping) and isinstance(item.get("name"), str) for item in schema
        ):
            return fail("cortex.forge.manifest_invalid")
        if not isinstance(utterances, list) or not 0 < len(utterances) <= MAX_UTTERANCES or not all(
            isinstance(item, str) and 0 < len(item.strip()) <= MAX_UTTERANCE_CHARS for item in utterances
        ):
            return fail("cortex.forge.manifest_invalid")
        parsed = SkillManifest._cases(cases)
        if parsed is None:
            return fail("cortex.forge.manifest_invalid")
        return Ok(SkillManifest(neuron_id, title.strip(), tuple(dict(item) for item in schema),
                                tuple(item.strip() for item in utterances), parsed))

    @staticmethod
    def _cases(cases: Any) -> Optional[tuple[SkillCase, ...]]:
        if not isinstance(cases, list) or not 0 < len(cases) <= MAX_CASES:
            return None
        out = []
        for case in cases:
            if not isinstance(case, Mapping) or not isinstance(case.get("slots"), Mapping) \
                    or not isinstance(case.get("expect_speech"), str):
                return None
            out.append(SkillCase(dict(case["slots"]), case["expect_speech"]))
        return tuple(out)
