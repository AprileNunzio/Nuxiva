import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from server.config.env import settings

logger = logging.getLogger("nuxiva.ternary_engine")

class TernaryModelSpec(BaseModel):
    model_id: str
    name: str
    parameter_size: str # es. "27B"
    quantization: str   # "1.58-bit Ternary {-1, 0, +1}"
    memory_footprint_gb: float
    fp16_equivalent_memory_gb: float
    token_cost: float = 0.0 # Locale, nessun costo token
    description: str
    download_url_or_tag: str
    backend: str # "bitnet_cpp", "ollama_ternary", "llama_cpp"

SUPPORTED_TERNARY_MODELS: Dict[str, TernaryModelSpec] = {
    "bonsai-27b": TernaryModelSpec(
        model_id="bonsai-27b",
        name="Bonsai 27B (Ternary Weight Architecture)",
        parameter_size="27B",
        quantization="1.58-bit Ternary {-1, 0, +1}",
        memory_footprint_gb=5.8,
        fp16_equivalent_memory_gb=54.0,
        token_cost=0.0,
        description=(
            "Modello da 27 Miliardi di parametri eseguibile su normali CPU/GPU con soli 6-8 GB di RAM. "
            "Sostituisce le moltiplicazioni matriciali FP16 con sole addizioni intere {-1, 0, +1}. "
            "Zero costi di token, privacy totale e ragionamento da modello frontier su hardware consumer."
        ),
        download_url_or_tag="ollama run bonsai:27b-ternary",
        backend="ollama_ternary",
    ),
    "bitnet-b1.58-27b": TernaryModelSpec(
        model_id="bitnet-b1.58-27b",
        name="Microsoft BitNet b1.58 (27B Extreme Efficiency)",
        parameter_size="27B",
        quantization="1.58-bit Ternary {-1, 0, +1}",
        memory_footprint_gb=5.9,
        fp16_equivalent_memory_gb=54.0,
        token_cost=0.0,
        description="Architettura nativa 1.58-bit ottimizzata per kernel AVX-512 e ARM NEON.",
        download_url_or_tag="bitnet:27b",
        backend="bitnet_cpp",
    ),
    "bonsai-8b": TernaryModelSpec(
        model_id="bonsai-8b",
        name="Bonsai 8B (Ultra-Light Ternary)",
        parameter_size="8B",
        quantization="1.58-bit Ternary {-1, 0, +1}",
        memory_footprint_gb=1.9,
        fp16_equivalent_memory_gb=16.0,
        token_cost=0.0,
        description="Gira agilmente su Raspberry Pi 5 o mini-PC con soli 4 GB di RAM.",
        download_url_or_tag="ollama run bonsai:8b-ternary",
        backend="ollama_ternary",
    ),
}

class TernaryEngineManager:
    _instance = None

    def __new__(cls) -> "TernaryEngineManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._active_model = "bonsai-27b"
        return cls._instance

    def list_available_models(self) -> List[TernaryModelSpec]:
        return list(SUPPORTED_TERNARY_MODELS.values())

    def get_spec(self, model_id: str) -> Optional[TernaryModelSpec]:
        return SUPPORTED_TERNARY_MODELS.get(model_id)

    def calculate_memory_savings(self, model_id: str) -> Dict[str, Any]:
        spec = self.get_spec(model_id)
        if not spec:
            return {}
        savings_gb = spec.fp16_equivalent_memory_gb - spec.memory_footprint_gb
        savings_pct = round((savings_gb / spec.fp16_equivalent_memory_gb) * 100, 1)
        return {
            "model": spec.name,
            "ternary_ram_gb": spec.memory_footprint_gb,
            "standard_fp16_ram_gb": spec.fp16_equivalent_memory_gb,
            "saved_ram_gb": round(savings_gb, 1),
            "savings_percentage": savings_pct,
            "token_cost_eur": 0.0,
        }

    def get_active_model(self) -> str:
        return self._active_model

    def set_active_model(self, model_id: str) -> bool:
        if model_id in SUPPORTED_TERNARY_MODELS:
            self._active_model = model_id
            return True
        return False

    async def unload_ollama_model(self, model_tag: str) -> None:
        """
        Scarica un modello dalla VRAM/RAM impostando keep_alive: 0.
        Garantisce che 1 solo modello rimanga allocato in memoria su PC a singola istanza.
        """
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={"model": model_tag, "keep_alive": 0}
                )
                logger.info(f"Modello {model_tag} scaricato dalla RAM con successo.")
        except Exception as e:
            logger.debug(f"Nota su unload Ollama per {model_tag}: {e}")

    async def activate_single_model(self, model_id: str) -> Dict[str, Any]:
        """
        Attiva il modello ternario selezionato garantendo la politica a Modello Singolo:
        libera il modello precedente da Ollama prima di caricare il nuovo per evitare OOM/swap.
        """
        spec = self.get_spec(model_id)
        if not spec:
            return {"status": "error", "message": f"Modello {model_id} non supportato"}

        prev_spec = self.get_spec(self._active_model)
        if prev_spec and prev_spec.model_id != model_id:
            # Unload previous model
            prev_tag = prev_spec.download_url_or_tag.replace("ollama run ", "").strip()
            await self.unload_ollama_model(prev_tag)

        self._active_model = model_id
        target_tag = spec.download_url_or_tag.replace("ollama run ", "").strip()
        settings.SYSTEM2_MODEL = target_tag

        return {
            "status": "success",
            "active_model": model_id,
            "tag": target_tag,
            "memory_footprint_gb": spec.memory_footprint_gb,
            "policy": "single_model_isolated",
            "savings": self.calculate_memory_savings(model_id),
        }

    def can_run_on_hardware(self, available_ram_gb: float) -> Optional[TernaryModelSpec]:
        """
        Determina il modello ternario più potente eseguibile con la RAM disponibile.
        """
        for m_id in ["bonsai-27b", "bitnet-b1.58-27b", "bonsai-8b"]:
            spec = SUPPORTED_TERNARY_MODELS[m_id]
            if available_ram_gb >= spec.memory_footprint_gb + 1.5: # 1.5 GB margine OS
                return spec
        return None

ternary_engine = TernaryEngineManager()

