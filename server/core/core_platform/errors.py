from typing import Optional

from server.core.core_platform.result import Err, Ok, Result
from server.shared.errors.domain_errors import NuxivaBaseException
from server.shared.i18n.provider import global_translator

MODULE = "core/core_platform"
CLIENT_PREFIXES = ("cortex.input.", "cortex.vector.", "cortex.slots.", "cortex.neuron.invalid", "cortex.router.", "cortex.forge.", "cortex.plasticity.")
NOT_FOUND_CODES = frozenset({"cortex.neuron.unknown", "cortex.forge.unknown_skill"})
UNAVAILABLE_PREFIXES = ("platform.", "hippocampus.embedding.", "hippocampus.skills.", "hippocampus.distillation.", "gliner.")


class CortexFailure(NuxivaBaseException):
    def __init__(self, code: str, lang: Optional[str] = None, details: Optional[dict] = None) -> None:
        super().__init__(message=translate_code(code, lang), code=code, details=details)

    @property
    def status_code(self) -> int:
        if self.code in NOT_FOUND_CODES:
            return 404
        if self.code.startswith(CLIENT_PREFIXES):
            return 422
        if self.code.startswith(UNAVAILABLE_PREFIXES):
            return 503
        return 500


def translate_code(code: str, lang: Optional[str] = None) -> str:
    key = f"errors.{code}"
    return global_translator.translate(MODULE, key, lang)


def fail(code: str, lang: Optional[str] = None, **details: object) -> Err[CortexFailure]:
    return Err(CortexFailure(code, lang, dict(details) or None))


def require(condition: bool, code: str) -> Result[None, CortexFailure]:
    return Ok(None) if condition else fail(code)
