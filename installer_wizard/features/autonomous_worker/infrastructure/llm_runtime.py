import asyncio
import json
import logging
from pathlib import Path
import time
from typing import Any

from config import STATE_DIR
from backend.sealed import write_private
import httpx
from features.brain import llm

log = logging.getLogger("nuxiva.autonomous_worker.runtime")
RUNTIME_CONFIG_FILE = STATE_DIR / "autonomous_missions" / "runtime_config.json"


class LLMRuntimeManager:
    def __init__(self, config_path: Path = RUNTIME_CONFIG_FILE) -> None:
        self.config_path = config_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._semaphore = asyncio.Semaphore(3)
        self._last_request_time = 0.0
        self._min_interval = 0.1
        self._config = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.config_path.exists():
            default_config = {
                "mode": "auto_fallback",
                "ollama_endpoint": "http://127.0.0.1:11434",
                "ollama_model": "qwen2.5-coder",
                "cloud_model": "default",
                "token_rate_limit_per_min": 120000,
                "max_concurrent_requests": 3,
                "request_timeout_seconds": 45,
                "offline_cache_enabled": True,
            }
            write_private(self.config_path, json.dumps(default_config, indent=2).encode("utf-8"))
            return default_config
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"mode": "auto_fallback", "ollama_endpoint": "http://127.0.0.1:11434"}

    def get_config(self) -> dict[str, Any]:
        return dict(self._config)

    def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        for k in ("mode", "ollama_endpoint", "ollama_model", "cloud_model"):
            if k in updates and isinstance(updates[k], str):
                self._config[k] = updates[k].strip()
        for k in ("token_rate_limit_per_min", "max_concurrent_requests", "request_timeout_seconds"):
            if k in updates and isinstance(updates[k], (int, float)):
                self._config[k] = max(1, int(updates[k]))
        if "offline_cache_enabled" in updates:
            self._config["offline_cache_enabled"] = bool(updates["offline_cache_enabled"])

        concurrency = self._config.get("max_concurrent_requests", 3)
        self._semaphore = asyncio.Semaphore(concurrency)
        write_private(self.config_path, json.dumps(self._config, indent=2).encode("utf-8"))
        return dict(self._config)

    async def check_health(self) -> dict[str, Any]:
        start = time.time()
        mode = self._config.get("mode", "auto_fallback")
        ollama_url = self._config.get("ollama_endpoint", "http://127.0.0.1:11434")

        ollama_ok = False
        ollama_models: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{ollama_url.rstrip('/')}/api/tags")
                if res.status_code == 200:
                    ollama_ok = True
                    data = res.json()
                    ollama_models = [m.get("name", "") for m in data.get("models", []) if isinstance(m, dict)]
        except Exception:
            ollama_ok = False

        cloud_ok = True
        latency_ms = int((time.time() - start) * 1000)

        active_ready = False
        if mode == "ollama":
            active_ready = ollama_ok
        elif mode == "cloud":
            active_ready = cloud_ok
        else:
            active_ready = ollama_ok or cloud_ok

        return {
            "healthy": active_ready,
            "mode": mode,
            "latency_ms": latency_ms,
            "ollama_available": ollama_ok,
            "ollama_models": ollama_models,
            "cloud_available": cloud_ok,
            "timestamp": time.time(),
        }

    async def generate(
        self,
        prompt: str,
        as_json: bool = True,
        max_tokens: int = 2500,
        temperature: float = 0.2,
        system: str = "",
        component: str = "autonomous_worker",
    ) -> Any:
        async with self._semaphore:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request_time = time.time()

            mode = self._config.get("mode", "auto_fallback")
            ollama_url = self._config.get("ollama_endpoint", "http://127.0.0.1:11434")
            ollama_model = self._config.get("ollama_model", "qwen2.5-coder")

            if mode in ("ollama", "auto_fallback"):
                try:
                    return await self._call_ollama(
                        endpoint=ollama_url,
                        model=ollama_model,
                        prompt=prompt,
                        system=system,
                        as_json=as_json,
                        temperature=temperature,
                    )
                except Exception as exc:
                    if mode == "ollama":
                        raise
                    log.warning("Fallback su Cloud LLM dopo errore Ollama: %s", exc)

            return await llm.generate(
                prompt,
                as_json=as_json,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                component=component,
            )

    async def _call_ollama(
        self,
        endpoint: str,
        model: str,
        prompt: str,
        system: str,
        as_json: bool,
        temperature: float,
    ) -> Any:
        timeout = float(self._config.get("request_timeout_seconds", 45))
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if as_json:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=timeout) as client:
            res = await client.post(f"{endpoint.rstrip('/')}/api/generate", json=payload)
            res.raise_for_status()
            data = res.json()
            response_text = data.get("response", "")
            if as_json:
                return json.loads(response_text)
            return response_text


runtime_manager = LLMRuntimeManager()
