import unittest
from unittest import mock

import httpx
from fastapi import FastAPI

import auth
from remote_admin import RemoteAdmin


class RemoteAdminTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        inner = FastAPI()

        @inner.get("/api/private")
        @inner.post("/api/private")
        async def private():
            return {"ok": True}

        @inner.post("/api/auth/login")
        async def login():
            return {"login": True}

        outer = FastAPI()
        outer.mount("/admin", RemoteAdmin(inner))
        transport = httpx.ASGITransport(app=outer)
        self.http = httpx.AsyncClient(transport=transport, base_url="https://testserver")
        patcher = mock.patch.object(auth, "verify", side_effect=lambda token: "admin" if token == "valid" else None)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addAsyncCleanup(self.http.aclose)

    async def test_anonymous_api_reads_and_writes_are_blocked(self):
        for method in (self.http.get, self.http.post):
            response = await method("/admin/api/private", headers={"X-Nuxiva-Request": "1"})
            self.assertEqual(response.status_code, 401)

    async def test_authenticated_writes_require_csrf(self):
        self.http.cookies.set(auth.SESSION_COOKIE, "valid")
        self.assertEqual((await self.http.get("/admin/api/private")).status_code, 200)
        self.assertEqual((await self.http.post("/admin/api/private")).status_code, 403)
        self.assertEqual((await self.http.post("/admin/api/private", headers={"X-Nuxiva-Request": "1"})).status_code, 200)

    async def test_login_can_be_reached_without_a_session(self):
        self.assertEqual((await self.http.post("/admin/api/auth/login")).status_code, 200)

    async def test_forged_cookie_is_rejected(self):
        self.http.cookies.set(auth.SESSION_COOKIE, "forged")
        self.assertEqual((await self.http.get("/admin/api/private")).status_code, 401)
