import logging

from agenti.mcpclient import engine, store

log = logging.getLogger("nuxiva.mcpclient")


def rust() -> bool:
    return engine.available()


def impl():
    if not rust():
        raise RuntimeError("motore MCP nativo non disponibile")
    from agenti.mcpclient import rust_service
    return rust_service


def add_server(body: dict) -> str:
    if not rust():
        raise ValueError("motore MCP nativo non disponibile")
    token = str(body.get("token", "")).strip()[:400]
    ident = store.add(body.get("name", ""), body.get("url", ""), "", bool(body.get("trusted")), body.get("lan"))
    if token:
        engine.set_token(ident, token)
        store.update(ident, has_token=True)
    return ident


async def forget(server_id: str) -> None:
    await impl().remove(server_id)


async def run() -> None:
    if not rust():
        log.warning("Server MCP esterni disattivati: motore nativo non disponibile")
        return
    await impl().run()
