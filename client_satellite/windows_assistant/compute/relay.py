import base64
import binascii
import http.client
import logging
import threading
import time

from connection.client import Client, ServerError, Unauthorized
from i18n.strings import t
from permissions.catalog import Level
from permissions.gate import Denied, Gate, Request
from permissions.policy import Policy
from compute.probe import HOST, PORT

log = logging.getLogger("nuxiva.compute")
CAPABILITY = "compute.ollama"
ALLOWED = {
    ("POST", "/api/chat"), ("POST", "/api/generate"), ("POST", "/api/embed"), ("POST", "/api/embeddings"),
    ("POST", "/api/show"), ("GET", "/api/tags"), ("GET", "/api/ps"), ("GET", "/api/version"),
}
BODY_LIMIT = 1 << 20
READ_SIZE = 1 << 16
FLUSH_BYTES = 1 << 14
FLUSH_SECONDS = 0.05
POLL_TIMEOUT = 40.0
RETRY_AFTER = 10.0
UPSTREAM_TIMEOUT = 600.0
MAX_WORKERS = 2


class JobRejected(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def decode(job: dict) -> tuple[str, str, bytes]:
    method, path = str(job.get("method") or ""), str(job.get("path") or "")
    if (method, path) not in ALLOWED:
        raise JobRejected("compute_path_not_allowed")
    try:
        body = base64.b64decode(str(job.get("body") or ""), validate=True)
    except (binascii.Error, ValueError):
        raise JobRejected("compute_invalid_body")
    if len(body) > BODY_LIMIT:
        raise JobRejected("compute_body_too_large")
    return method, path, body


class ComputeRelay(threading.Thread):
    def __init__(self, client: Client, gate: Gate, policy: Policy, available) -> None:
        super().__init__(daemon=True, name="compute-relay")
        self.client, self.gate, self.policy, self.available = client, gate, policy, available
        self.stop_flag = threading.Event()
        self.slots = threading.BoundedSemaphore(MAX_WORKERS)

    def sharing(self) -> bool:
        return self.policy.level(CAPABILITY) is not Level.DENY and bool(self.available())

    def run(self) -> None:
        while not self.stop_flag.is_set():
            if not self.sharing():
                self.stop_flag.wait(RETRY_AFTER)
                continue
            try:
                reply = self.client.request("/api/nodes/compute/next", {}, timeout=POLL_TIMEOUT)
            except Unauthorized:
                return
            except ServerError as exc:
                log.debug("Canale di calcolo non raggiungibile: %s", exc)
                self.stop_flag.wait(RETRY_AFTER)
                continue
            for job in (reply.get("jobs") or [])[:MAX_WORKERS]:
                if isinstance(job, dict) and self.slots.acquire(blocking=False):
                    threading.Thread(target=self._worker, args=(job,), daemon=True, name="compute-job").start()

    def _worker(self, job: dict) -> None:
        job_id = str(job.get("id") or "")
        try:
            self._execute(job_id, job)
        except Unauthorized:
            log.warning("Relay interrotto: il PC non è più autorizzato")
        except ServerError as exc:
            log.warning("Relay interrotto, il server non risponde: %s", exc)
        finally:
            self.slots.release()

    def _execute(self, job_id: str, job: dict) -> None:
        try:
            method, path, body = decode(job)
            self.gate.check(Request(CAPABILITY, t("compute.ollama.request", path=path)))
        except JobRejected as exc:
            self._send(job_id, error=exc.code)
            return
        except Denied:
            self._send(job_id, error="compute_denied")
            return
        conn = http.client.HTTPConnection(HOST, PORT, timeout=UPSTREAM_TIMEOUT)
        try:
            conn.request(method, path, body or None, {"Content-Type": "application/json"})
            response = conn.getresponse()
            self._pump(job_id, response)
        except (OSError, http.client.HTTPException) as exc:
            log.warning("Ollama locale non ha risposto: %s", exc)
            self._send(job_id, error="compute_ollama_unreachable")
        finally:
            conn.close()

    def _pump(self, job_id: str, response: http.client.HTTPResponse) -> None:
        status, ctype = response.status, response.getheader("Content-Type") or "application/json"
        buffer, last, first = b"", time.monotonic(), True
        while True:
            piece = response.read1(READ_SIZE)
            buffer += piece
            ended = not piece
            if buffer and (ended or first or len(buffer) >= FLUSH_BYTES or time.monotonic() - last >= FLUSH_SECONDS):
                if self._send(job_id, buffer, status if first else None, ctype if first else "", ended):
                    return
                buffer, last, first = b"", time.monotonic(), False
            elif ended:
                self._send(job_id, b"", status if first else None, ctype if first else "", True)
                return

    def _send(self, job_id: str, data: bytes = b"", status: int | None = None, content_type: str = "",
              done: bool = False, error: str = "") -> bool:
        body = {"id": job_id, "data": base64.b64encode(data).decode("ascii"), "done": done or bool(error)}
        if status is not None:
            body.update(status=status, content_type=content_type)
        if error:
            body["error"] = error
        return bool(self.client.request("/api/nodes/compute/chunk", body, timeout=30).get("cancel"))

    def stop(self) -> None:
        self.stop_flag.set()
