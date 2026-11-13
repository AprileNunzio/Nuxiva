import asyncio

from agenti.mcpclient import calls, engine, store


class Area:
    def __init__(self, server: str, flag: str, definition) -> None:
        self.server = server
        self.flag = flag
        engine.INTERNAL[server] = definition

    def active(self) -> bool:
        return engine.mode(self.flag) == "mcp" and engine.available()

    def ensure(self) -> None:
        if not engine.published():
            engine.publish(store.load())

    def needs_consent(self, tool: str) -> bool:
        if not self.active():
            return False
        self.ensure()
        return calls.confirm(f"{self.server}.{tool}")

    def consent(self, tool: str):
        return lambda: self.needs_consent(tool)

    async def call(self, tool: str, **arguments) -> str:
        tool_id = f"{self.server}.{tool}"
        await asyncio.to_thread(self.ensure)
        if not await asyncio.to_thread(engine.wait_tool, tool_id):
            raise RuntimeError(f"il server «{self.server}» non è disponibile")
        out = (await asyncio.to_thread(calls.invoke, tool_id, arguments, calls.operation(), self.server))["external"]
        if out["is_error"]:
            raise RuntimeError(out["text"])
        return out["text"]
