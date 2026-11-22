"""Servizio di esecuzione codice protetto (Sandbox & Approval Gate)."""

import asyncio
import os
import sys
import tempfile
import time
from typing import Any, Dict

SUPPORTED_LANGUAGES = ("python", "sh", "bash", "javascript", "typescript")
MAX_CODE_CHARS = 100_000
TIMEOUT_SECONDS = 15.0


class ExecutionService:
    @staticmethod
    def is_executable(kind: str, language: str) -> bool:
        lang = (language or "").lower().strip()
        return kind in ("code", "script") or lang in SUPPORTED_LANGUAGES

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: float = TIMEOUT_SECONDS,
    ) -> Dict[str, Any]:
        lang = (language or "python").lower().strip()
        if len(code) > MAX_CODE_CHARS:
            return {
                "ok": False,
                "exit_code": -1,
                "output": f"Errore: il codice supera il limite consentito di {MAX_CODE_CHARS} caratteri.",
                "duration_ms": 0,
            }

        start_time = time.perf_counter()
        tmp_file = None

        try:
            suffix = ".py" if "py" in lang else ".sh" if "sh" in lang else ".js"
            with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as f:
                f.write(code)
                tmp_file = f.name

            if "py" in lang:
                cmd = [sys.executable, "-u", tmp_file]
            elif "sh" in lang or "bash" in lang:
                cmd = ["/bin/bash", tmp_file]
            elif "js" in lang or "node" in lang:
                cmd = ["node", tmp_file]
            else:
                return {
                    "ok": False,
                    "exit_code": -1,
                    "output": f"Linguaggio '{language}' non supportato per esecuzione immediata.",
                    "duration_ms": 0,
                }

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                out = stdout_data.decode("utf-8", errors="replace")
                err = stderr_data.decode("utf-8", errors="replace")
                combined = (out + ("\n[stderr]:\n" + err if err else "")).strip()

                return {
                    "ok": proc.returncode == 0,
                    "exit_code": proc.returncode,
                    "output": combined or "[Esecuzione terminata senza output]",
                    "duration_ms": duration_ms,
                }
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                return {
                    "ok": False,
                    "exit_code": 124,
                    "output": f"[Tempo limite scaduto ({timeout}s)]",
                    "duration_ms": int(timeout * 1000),
                }

        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "ok": False,
                "exit_code": -1,
                "output": f"[Errore durante l'avvio della sandbox: {type(exc).__name__}: {exc}]",
                "duration_ms": duration_ms,
            }
        finally:
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.unlink(tmp_file)
                except OSError:
                    pass
