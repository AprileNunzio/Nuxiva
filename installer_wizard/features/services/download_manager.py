from __future__ import annotations

import asyncio
import shutil
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import urllib.request


@dataclass
class DownloadTask:
    id: str
    url: str
    destination: Path
    total_bytes: int = 0
    downloaded_bytes: int = 0
    start_time: float = field(default_factory=time.time)
    speed_bps: float = 0.0
    progress_pct: int = 0
    status: str = "pending"
    error: str = ""
    cancelled: bool = False


class DownloadManager:
    def __init__(self, chunk_size: int = 65536) -> None:
        self.chunk_size = chunk_size
        self._tasks: Dict[str, DownloadTask] = {}
        self._lock = asyncio.Lock()

    def _sanitize_url(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("URL scheme not allowed")
        if not parsed.netloc:
            raise ValueError("Missing host in URL")
        return url

    def _safe_destination(self, destination: str) -> Path:
        dest = Path(destination).resolve()
        if not str(dest).strip():
            raise ValueError("Invalid destination path")
        return dest

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        for task in self._tasks.values():
            if task.status == "downloading":
                task.cancelled = True
                task.status = "cancelled"

    def status(self) -> Dict[str, Any]:
        return {
            "active_count": sum(1 for t in self._tasks.values() if t.status == "downloading"),
            "total_tasks": len(self._tasks),
            "tasks": [self._format_task(t) for t in self._tasks.values()],
        }

    def _format_task(self, task: DownloadTask) -> Dict[str, Any]:
        return {
            "id": task.id,
            "url": task.url,
            "destination": str(task.destination),
            "progress_pct": task.progress_pct,
            "downloaded_bytes": task.downloaded_bytes,
            "total_bytes": task.total_bytes,
            "speed_bps": round(task.speed_bps, 2),
            "status": task.status,
            "error": task.error,
        }

    def cancel(self, download_id: str) -> bool:
        task = self._tasks.get(download_id)
        if not task:
            return False
        if task.status in ("downloading", "pending"):
            task.cancelled = True
            task.status = "cancelled"
            return True
        return False

    def active_downloads(self) -> List[Dict[str, Any]]:
        return [self._format_task(t) for t in self._tasks.values() if t.status == "downloading"]

    async def download(
        self,
        url: str,
        destination: str,
        on_progress: Optional[Callable[[int, float, str], None]] = None,
        timeout_s: float = 600.0,
    ) -> bool:
        clean_url = self._sanitize_url(url)
        dest_path = self._safe_destination(destination)
        task_id = f"dl_{int(time.time() * 1000)}_{len(self._tasks)}"
        task = DownloadTask(id=task_id, url=clean_url, destination=dest_path)
        
        async with self._lock:
            self._tasks[task_id] = task

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        part_path = dest_path.with_name(f"{dest_path.name}.part")

        def _blocking_download() -> None:
            req = urllib.request.Request(clean_url, headers={"User-Agent": "Nuxiva-DownloadManager/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_s) as response:
                total = int(response.headers.get("Content-Length") or 0)
                task.total_bytes = total
                task.status = "downloading"
                downloaded = 0
                last_time = time.time()
                last_bytes = 0

                with open(part_path, "wb") as f:
                    while True:
                        if task.cancelled:
                            break
                        chunk = response.read(self.chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        task.downloaded_bytes = downloaded

                        now = time.time()
                        if now - last_time >= 0.5:
                            dt = max(now - last_time, 0.001)
                            db = downloaded - last_bytes
                            task.speed_bps = db / dt
                            pct = int(downloaded * 100 / total) if total > 0 else 0
                            task.progress_pct = max(0, min(100, pct))
                            speed_str = f"{task.speed_bps / 1024 / 1024:.2f} MB/s"
                            if on_progress:
                                on_progress(task.progress_pct, task.speed_bps, speed_str)
                            last_time = now
                            last_bytes = downloaded

            if task.cancelled:
                if part_path.exists():
                    part_path.unlink()
                return

            if part_path.exists():
                shutil.move(str(part_path), str(dest_path))
                task.status = "completed"
                task.progress_pct = 100
                if on_progress:
                    on_progress(100, 0.0, "0 MB/s")

        try:
            await asyncio.wait_for(asyncio.to_thread(_blocking_download), timeout=timeout_s + 5.0)
            return task.status == "completed"
        except asyncio.TimeoutError:
            task.status = "failed"
            task.error = f"Download timeout after {timeout_s}s"
            if part_path.exists():
                try:
                    part_path.unlink()
                except OSError:
                    pass
            return False
        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
            if part_path.exists():
                try:
                    part_path.unlink()
                except OSError:
                    pass
            return False
