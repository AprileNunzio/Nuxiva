from typing import Optional

from server.core.core_platform.errors import CortexFailure
from server.core.core_platform.native_bridge import call_native
from server.core.core_platform.result import Result

MAX_UTTERANCE_CHARS = 4000


def sanitize_utterance(text: str, max_chars: int = MAX_UTTERANCE_CHARS, lang: Optional[str] = None) -> Result[str, CortexFailure]:
    return call_native(lambda native: native.cortex_sanitize_utterance(text, max_chars), lang)


def sanitize_identifier(text: str, lang: Optional[str] = None) -> Result[str, CortexFailure]:
    return call_native(lambda native: native.cortex_sanitize_identifier(text), lang)
