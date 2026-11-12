import time
from typing import Optional

import httpx

from .types import BenchmarkResult


async def run_benchmark(ollama_url: str, model: str = "") -> BenchmarkResult:
    target_model = model
    if not target_model:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            resp.raise_for_status()
            models = resp.json().get("models", [])
            if not models:
                raise ValueError("No models installed in Ollama to benchmark")
            target_model = models[0]["name"]

    prompt = "Scrivi un ragionamento passo-passo sulla convergenza numerica delle serie armoniche."
    payload = {
        "model": target_model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.2,
            "num_predict": 128,
            "num_ctx": 2048,
        },
    }

    start_time = time.perf_counter()
    first_token_time: Optional[float] = None
    generated_tokens = 0
    prompt_tokens = 0

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", f"{ollama_url}/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                import json
                chunk = json.loads(line)
                if first_token_time is None and chunk.get("response"):
                    first_token_time = time.perf_counter()
                if chunk.get("response"):
                    generated_tokens += 1
                if chunk.get("done"):
                    prompt_tokens = chunk.get("prompt_eval_count", 0)
                    eval_count = chunk.get("eval_count", 0)
                    if eval_count > 0:
                        generated_tokens = eval_count
                    break

    end_time = time.perf_counter()
    total_duration_ms = (end_time - start_time) * 1000.0
    ttft_ms = ((first_token_time or end_time) - start_time) * 1000.0
    eval_duration_ms = max(1.0, (end_time - (first_token_time or start_time)) * 1000.0)
    tok_per_sec = (generated_tokens / (eval_duration_ms / 1000.0)) if generated_tokens > 0 else 0.0

    return BenchmarkResult(
        model=target_model,
        prompt_tokens=prompt_tokens,
        generated_tokens=generated_tokens,
        total_duration_ms=round(total_duration_ms, 2),
        eval_duration_ms=round(eval_duration_ms, 2),
        tokens_per_second=round(tok_per_sec, 2),
        time_to_first_token_ms=round(ttft_ms, 2),
    )
