from fastapi import APIRouter, HTTPException, Request

from server.features.brain.contracts import (
    EngineVersionStatusResponse,
    EngineVersionUpdateRequest,
    OllamaHibernateRequest,
    OllamaHibernateResponse,
    OllamaProbeRequest,
    OllamaProbeResponse,
)
from server.features.brain.service import brain_engine_service

brain_router = APIRouter(prefix="/brain", tags=["brain"])


def _lang(request: Request) -> str:
    return (request.headers.get("accept-language") or "it")[:2].lower()


@brain_router.get("/engine-version", response_model=EngineVersionStatusResponse)
async def get_engine_version(request: Request) -> EngineVersionStatusResponse:
    return brain_engine_service.get_status(_lang(request))


@brain_router.post("/engine-version", response_model=EngineVersionStatusResponse)
async def update_engine_version(payload: EngineVersionUpdateRequest, request: Request) -> EngineVersionStatusResponse:
    try:
        brain_engine_service.switch_engine(payload.version)
    except LookupError:
        raise HTTPException(status_code=404, detail="engine_not_found")
    return brain_engine_service.get_status(_lang(request))


@brain_router.post("/ollama/probe", response_model=OllamaProbeResponse)
async def probe_ollama_server(payload: OllamaProbeRequest) -> OllamaProbeResponse:
    return await brain_engine_service.probe_ollama(payload.host)


@brain_router.post("/ollama/hibernate", response_model=OllamaHibernateResponse)
async def hibernate_ollama(payload: OllamaHibernateRequest) -> OllamaHibernateResponse:
    return await brain_engine_service.hibernate_local_ollama_if_unused(
        payload.local_targets_count, payload.local_host
    )


