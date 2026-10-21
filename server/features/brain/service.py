import time
import httpx
from server.core.reasoning.engines.scanner import engine_scanner
from server.features.brain.contracts import (
    CognitiveEngineProfile,
    EngineStrategy,
    EngineVersionStatusResponse,
    OllamaDiscoveredModel,
    OllamaHibernateResponse,
    OllamaProbeResponse,
)
from server.features.llm_gateway.contracts import CognitiveEngineVersion


def normalize_ollama_host(raw: str) -> str:
    cleaned = raw.strip().rstrip("/")
    if not cleaned:
        return "http://127.0.0.1:11434"
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"http://{cleaned}"
    parts = cleaned.split("://", 1)
    scheme = parts[0]
    rest = parts[1]
    host_part = rest.split("/")[0]
    if ":" not in host_part:
        rest = f"{host_part}:11434"
    return f"{scheme}://{rest}"


class BrainEngineService:
    def __init__(self) -> None:
        self._scanner = engine_scanner
        self._configured_version: CognitiveEngineVersion = self._scanner.get_default_engine().version

    def get_configured_version(self) -> CognitiveEngineVersion:
        return self._configured_version

    def switch_engine(self, requested: CognitiveEngineVersion) -> EngineVersionStatusResponse:
        if self._scanner.get_engine(requested) is None:
            raise LookupError(requested)
        self._configured_version = requested
        return self.get_status()

    def get_status(self, lang: str | None = None) -> EngineVersionStatusResponse:
        profiles = [
            CognitiveEngineProfile(
                id=engine.version,
                name=engine.label(lang),
                architecture=engine.summary(lang),
                strategy=EngineStrategy(**engine.strategy.as_dict()),
                active=engine.version == self._configured_version,
            )
            for engine in self._scanner.list_engines()
        ]
        return EngineVersionStatusResponse(current_configured=self._configured_version, engines=profiles, success=True)

    async def probe_ollama(self, host: str) -> OllamaProbeResponse:
        normalized = normalize_ollama_host(host)
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                tags_res = None
                try:
                    tags_res = await client.get(f"{normalized}/api/tags")
                except Exception:
                    tags_res = None

                latency_ms = int((time.perf_counter() - start) * 1000)

                if tags_res is not None and tags_res.status_code == 200:
                    data = tags_res.json()
                    raw_models = data.get("models", [])
                    parsed = [
                        OllamaDiscoveredModel(
                            name=str(m.get("name") or m.get("model") or ""),
                            size=int(m.get("size") or 0),
                            parameter_size=str(m.get("details", {}).get("parameter_size") or ""),
                            quantization_level=str(m.get("details", {}).get("quantization_level") or ""),
                            family=str(m.get("details", {}).get("family") or ""),
                            modified_at=str(m.get("modified_at") or ""),
                        )
                        for m in raw_models
                    ]
                    return OllamaProbeResponse(
                        online=True,
                        latency_ms=latency_ms,
                        normalized_url=normalized,
                        models=parsed,
                    )

                try:
                    root_res = await client.get(f"{normalized}/")
                    if root_res.status_code == 200 and (
                        "ollama" in root_res.text.lower() or "running" in root_res.text.lower()
                    ):
                        return OllamaProbeResponse(
                            online=True,
                            latency_ms=latency_ms,
                            normalized_url=normalized,
                            models=[],
                        )
                except Exception:
                    pass

                try:
                    ver_res = await client.get(f"{normalized}/api/version")
                    if ver_res.status_code == 200:
                        return OllamaProbeResponse(
                            online=True,
                            latency_ms=latency_ms,
                            normalized_url=normalized,
                            models=[],
                        )
                except Exception:
                    pass

                return OllamaProbeResponse(
                    online=False,
                    latency_ms=latency_ms,
                    normalized_url=normalized,
                    error="host_unreachable_or_not_ollama",
                )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return OllamaProbeResponse(
                online=False,
                latency_ms=latency_ms,
                normalized_url=normalized,
                error=str(exc),
            )


    async def hibernate_local_ollama_if_unused(self, local_targets_count: int, local_host: str = "http://127.0.0.1:11434") -> OllamaHibernateResponse:
        if local_targets_count > 0:
            return OllamaHibernateResponse(
                hibernated=False,
                status="active",
                active_local_targets=local_targets_count,
                reason_code="resource.active_local_workload",
            )

        normalized = normalize_ollama_host(local_host)
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(f"{normalized}/api/ps")
                if res.status_code == 200:
                    data = res.json()
                    models = data.get("models", [])
                    for m in models:
                        name = m.get("name") or m.get("model")
                        if name:
                            await client.post(f"{normalized}/api/generate", json={"model": name, "keep_alive": 0})
        except Exception:
            pass

        return OllamaHibernateResponse(
            hibernated=True,
            status="hibernated",
            active_local_targets=0,
            reason_code="resource.hibernate_zero_local_targets",
        )


brain_engine_service = BrainEngineService()
