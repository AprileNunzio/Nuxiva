from server.core.reasoning.engines.scanner import engine_scanner
from server.features.brain.contracts import CognitiveEngineProfile, EngineStrategy, EngineVersionStatusResponse
from server.features.llm_gateway.contracts import CognitiveEngineVersion


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


brain_engine_service = BrainEngineService()
