import json
from typing import Any, Mapping, Optional, Sequence

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.native_bridge import call_native
from server.core.core_platform.result import Result


def validate_slots(
    schema: Sequence[Mapping[str, Any]],
    extracted: Mapping[str, str],
    lang: Optional[str] = None,
) -> Result[dict[str, Any], CortexFailure]:
    try:
        schema_json = json.dumps(list(schema), ensure_ascii=False)
        extracted_json = json.dumps(dict(extracted), ensure_ascii=False)
    except (TypeError, ValueError):
        return fail("cortex.slots.schema_invalid", lang)
    validated = call_native(lambda native: native.cortex_validate_slots(schema_json, extracted_json), lang)
    return validated.map(json.loads) if validated.is_ok else validated
