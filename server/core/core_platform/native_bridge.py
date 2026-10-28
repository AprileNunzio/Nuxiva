from types import ModuleType
from typing import Any, Callable, Optional

from server.core.core_platform.errors import CortexFailure, fail
from server.core.core_platform.result import Err, Ok, Result

REQUIRED_SYMBOLS = (
    "RustNeuronIndex",
    "RustCorticalCortex",
    "RustEmbodiedCortex",
    "RustSigner",
    "CortexError",
    "cortex_sanitize_utterance",
    "cortex_seal",
    "cortex_open",
    "cortex_derive_key",
    "cortex_verify",
    "cortex_validate_slots",
)


def load_native() -> Result[ModuleType, CortexFailure]:
    try:
        import nuxiva_native
    except ImportError:
        return fail("platform.native.unavailable")
    missing = [name for name in REQUIRED_SYMBOLS if not hasattr(nuxiva_native, name)]
    if missing:
        return fail("platform.native.outdated", missing=missing)
    return Ok(nuxiva_native)


def call_native(action: Callable[[ModuleType], Any], lang: Optional[str] = None) -> Result[Any, CortexFailure]:
    loaded = load_native()
    if not loaded.is_ok:
        return loaded
    native = loaded.value
    try:
        return Ok(action(native))
    except native.CortexError as exc:
        return Err(CortexFailure(str(exc), lang))
