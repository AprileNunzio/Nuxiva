import asyncio
import concurrent.futures
import contextvars
import importlib
import json

from state import store

from agenti.reasoning.contracts import CHAT, CONNECTOR

STEP_TIMEOUT = 240
REFUSED = ("ERRORE", "NEGATO")


def _ok(output: str) -> str:
    return json.dumps({"ok": True, "output": output}, ensure_ascii=False)


def _fail(kind: str) -> str:
    return json.dumps({"ok": False, "failure": kind})


class Invoker:
    def __init__(self, text: str, loop: asyncio.AbstractEventLoop) -> None:
        self.text = text
        self.loop = loop
        self.ui: dict = {"mode": "face"}
        self.agent = ""
        self.errors: list[str] = []

    def __call__(self, capability: str, key: str, args_json: str) -> str:
        args = json.loads(args_json)
        context = contextvars.copy_context()
        future: concurrent.futures.Future = concurrent.futures.Future()

        def start() -> None:
            task = self.loop.create_task(self.dispatch(capability, args), context=context)

            def settle(done: asyncio.Task) -> None:
                if done.cancelled():
                    future.set_exception(concurrent.futures.CancelledError())
                elif done.exception() is not None:
                    future.set_exception(done.exception())
                else:
                    future.set_result(done.result())

            task.add_done_callback(settle)

        self.loop.call_soon_threadsafe(start)
        return future.result(timeout=STEP_TIMEOUT)

    async def dispatch(self, capability: str, args: dict) -> str:
        if capability == CHAT:
            return _fail("permanent")
        if capability.startswith(CONNECTOR):
            return await self._connector(capability.removeprefix(CONNECTOR), args)
        return await self._tool(capability, args)

    async def _connector(self, name: str, args: dict) -> str:
        from agenti.authz import gate
        from agenti.chat import assistant
        module = assistant.CONNECTORS.get(name)
        if module is None or not gate.connector_allowed(name):
            return _fail("permanent")
        try:
            speech, ui = await importlib.import_module(module).answer(str(args.get("request") or self.text))
        except LookupError:
            return _fail("permanent")
        except Exception as exc:
            store.event("WARN", f"Motore · connettore {name}: {exc}", "reasoning")
            self.errors.append(f"{name}: {str(exc)[:160]}")
            return _fail("permanent")
        self.ui, self.agent = ui if isinstance(ui, dict) else {"mode": "face"}, name
        return _ok(str(speech))

    async def _tool(self, name: str, args: dict) -> str:
        from agenti.agent import registry
        from agenti.team import runner
        if name not in registry.TOOLS:
            return _fail("permanent")
        token = registry.REQUEST.set(self.text)
        try:
            refusal = registry.unrequested(name) or registry.precheck(name, args)
            if refusal or registry.needs_confirm(name, args):
                return _fail("permanent")
            result = await runner.run_as(name, args)
        except PermissionError as exc:
            self.errors.append(f"{name}: {str(exc)[:160]}")
            return _fail("permanent")
        except Exception as exc:
            store.event("WARN", f"Motore · strumento {name}: {exc}", "reasoning")
            self.errors.append(f"{name}: {str(exc)[:160]}")
            return _fail("permanent")
        finally:
            registry.REQUEST.reset(token)
        if result.startswith(REFUSED):
            self.errors.append(f"{name}: {result[:160]}")
            return _fail("permanent")
        self.agent = name
        return _ok(result)
