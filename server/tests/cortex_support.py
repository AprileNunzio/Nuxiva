import asyncio
import json
import unittest

from server.core.core_platform.native_bridge import load_native

NATIVE_AVAILABLE = load_native().is_ok
requires_native = unittest.skipUnless(NATIVE_AVAILABLE, "nuxiva_native with cortex support is not installed")
SECRET = "unit-test-master-secret-0123456789abcdef"


def asgi_get(app, path):
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, json.loads(body)
