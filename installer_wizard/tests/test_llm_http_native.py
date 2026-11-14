import asyncio
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

import httpx
import native_core

from agenti.brain import llm


class Handler(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        Handler.seen.append((self.path, json.loads(body)))
        if self.path == "/api/generate" and json.loads(body).get("model") == "limit":
            payload, status = b'{"error":"slow"}', 429
        else:
            payload, status = json.dumps({"response": "ciao", "prompt_eval_count": 3, "eval_count": 4}).encode(), 200
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        return


def serve():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def enabled(value):
    return mock.patch.object(llm, "env_get", side_effect=lambda key, default="": value if key == "NUXIVA_LLM_CLIENT" else default)


@unittest.skipIf(native_core.symbol("llm_post_json") is None, "modulo nativo assente")
class LlmHttpParityTest(unittest.TestCase):
    def setUp(self):
        Handler.seen = []
        self.server, self.base = serve()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def run_post(self, mode, model="m"):
        with enabled(mode):
            return asyncio.run(llm._post_generate(self.base, {"model": model, "prompt": "ciao"}, 5.0))

    def test_rust_and_python_return_the_same_data(self):
        self.assertEqual(self.run_post("rust"), self.run_post("python"))
        self.assertEqual(len(Handler.seen), 2)
        self.assertEqual(Handler.seen[0], Handler.seen[1])

    def test_status_errors_raise_the_same_exception_type(self):
        for mode in ("rust", "python"):
            with self.subTest(mode=mode):
                with self.assertRaises(httpx.HTTPStatusError) as raised:
                    self.run_post(mode, "limit")
                self.assertEqual(raised.exception.response.status_code, 429)

    def test_default_is_python(self):
        with enabled("python"):
            self.assertIsNone(llm._native_client())
        with enabled("rust"):
            self.assertIsNotNone(llm._native_client())

    def test_closed_port_falls_back_and_fails_like_before(self):
        self.server.shutdown()
        self.server.server_close()
        with self.assertRaises(httpx.HTTPError):
            self.run_post("rust")

    def test_hostile_inputs_rejected_natively(self):
        post = native_core.symbol("llm_post_json")
        for base in ("ftp://x", "http://u:p@h", "nonsense"):
            with self.assertRaises(ValueError):
                post(base, "api/generate", "{}", 1.0, None)
        with self.assertRaises(ValueError):
            post(self.base, "../x", "{}", 1.0, None)
        with self.assertRaises(ValueError):
            post(self.base, "api/generate", "not json", 1.0, None)
        with self.assertRaises(ValueError):
            post(self.base, "api/generate", "{}", 0.0, None)


if __name__ == "__main__":
    unittest.main()
