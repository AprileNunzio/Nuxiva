import native_core
from agenti.mcpclient import engine, service, store


def rust() -> bool:
    return engine.available()


def impl():
    if rust():
        from agenti.mcpclient import rust_service
        return rust_service
    native_core.python_fallback("mcpclient")
    return service


def add_server(body: dict) -> str:
    sealed = rust()
    token = str(body.get("token", "")).strip()[:400]
    ident = store.add(body.get("name", ""), body.get("url", ""), "" if sealed else token, bool(body.get("trusted")), body.get("lan"))
    if sealed and token:
        engine.set_token(ident, token)
        store.update(ident, has_token=True)
    return ident


async def forget(server_id: str) -> None:
    if rust():
        from agenti.mcpclient import rust_service
        await rust_service.remove(server_id)
    else:
        service.drop(server_id)


async def run() -> None:
    await impl().run()
