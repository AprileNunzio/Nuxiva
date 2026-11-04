import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from features.locale.colocated.errors import I18nError

log = logging.getLogger("nuxiva.i18n")


async def _handle(request: Request, exc: Exception) -> JSONResponse:
    error = exc if isinstance(exc, I18nError) else I18nError(str(exc))
    level = logging.ERROR if error.status_code >= 500 else logging.WARNING
    log.log(level, "%s on %s: %s", error.code, request.url.path, error.detail)
    return JSONResponse(
        {"error": error.code, "detail": error.detail},
        status_code=error.status_code,
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


def install(app: FastAPI) -> None:
    app.add_exception_handler(I18nError, _handle)
