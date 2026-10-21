import re
from typing import Annotated, Any

from pydantic import BeforeValidator, StringConstraints

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_MARKUP = re.compile(r"[<>`]")


def _sanitizer(limit: int) -> BeforeValidator:
    def convert(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return _MARKUP.sub("", _CONTROL.sub("", value)).strip()[:limit]

    return BeforeValidator(convert)


ShortText = Annotated[str, _sanitizer(80)]
MediumText = Annotated[str, _sanitizer(240)]
LongText = Annotated[str, _sanitizer(1200)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_\-][A-Za-z0-9_.\-]{0,63}$")]
Reference = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_\-]{0,15}$")]
PinNumber = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_+\-./]{1,16}$")]
