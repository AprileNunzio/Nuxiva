import logging
import time

from autonomy import profile
from autonomy.brain import BrainError
from connection.client import ServerError

log = logging.getLogger("nuxiva.router")
RETRY_AFTER = 30.0


class Router:
    def __init__(self, client, brain, cfg: dict, has_server: bool, memory=None, sync=None) -> None:
        self.client, self.brain, self.cfg, self.has_server = client, brain, cfg, has_server
        self.memory, self.sync = memory, sync
        self.down_until = 0.0
        self.last = "none"

    def mode(self) -> profile.Mode:
        return profile.parse_mode(self.cfg.get("mode"))

    def server_up(self) -> bool:
        return self.has_server and time.monotonic() >= self.down_until

    def assist(self, body: dict) -> dict:
        mode = self.mode()
        route = profile.resolve(mode, self.server_up(), self.brain.ready() if mode is not profile.Mode.SERVER else False)
        if route == "server":
            try:
                result = self.client.assist(body)
            except ServerError as exc:
                if mode is profile.Mode.SERVER or not self.brain.ready():
                    raise
                self.down_until = time.monotonic() + RETRY_AFTER
                log.info("Server non raggiungibile, passo al cervello locale: %s", exc)
            except Exception as exc:
                if mode is profile.Mode.SERVER or not self.brain.ready():
                    raise ServerError(f"Connessione al server non riuscita: {exc}") from exc
                self.down_until = time.monotonic() + RETRY_AFTER
                log.info("Errore connessione server (%s), passo al cervello locale", exc)
            else:
                self.last = "server"
                if self.sync is not None:
                    self.sync.flush_later()
                return result
        elif route == "none":
            raise ServerError("Nessun cervello disponibile: collega il PC a NUXIVA oppure installa Ollama con un modello")
        try:
            result = self.brain.assist(body)
        except (OSError, BrainError) as exc:
            raise ServerError(str(exc)) from exc
        except Exception as exc:
            raise ServerError(f"Errore cervello locale: {exc}") from exc
        if not isinstance(result, dict):
            result = {"reply": str(result or ""), "actions": []}
        self.last = "local"
        if self.memory is not None and not body.get("results") and result.get("reply"):
            self.memory.record(str(body.get("text") or ""), str(result["reply"]))
        return result
