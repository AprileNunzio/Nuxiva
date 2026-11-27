import asyncio
import time
import unittest
from unittest import mock

from agenti.brain import inflight
from agenti.chat.anticipate import service
from agenti.chat.anticipate.budget import Budget

DELAY = 0.3


class KeyAndBudgetTest(unittest.TestCase):

    def test_punctuation_case_and_spacing_do_not_change_the_key(self):
        self.assertEqual(inflight.key("Che tempo fa domani?"), inflight.key("  che TEMPO fa,  domani "))
        self.assertNotEqual(inflight.key("accendi la luce"), inflight.key("spegni la luce"))

    def test_the_budget_refills_after_a_minute(self):
        now = [0.0]
        budget = Budget(2, clock=lambda: now[0])
        self.assertEqual([budget.take("a"), budget.take("a"), budget.take("a")], [True, True, False])
        self.assertTrue(budget.take("b"))
        now[0] = 61.0
        self.assertTrue(budget.take("a"))

    def test_the_assistant_name_is_not_part_of_the_command(self):
        with mock.patch.dict("os.environ", {"NUXIVA_ASSISTANT_NAME": "Nuxiva"}):
            self.assertEqual(service.command_of("Nuxiva, che tempo fa domani?"), "che tempo fa domani?")
            self.assertEqual(service.command_of("che tempo fa domani?"), "che tempo fa domani?")

    def test_short_or_repeated_partials_are_not_worth_a_thought(self):
        service.recent.clear()
        self.assertFalse(service.worth("ciao"))
        self.assertTrue(service.worth("che tempo fa domani"))
        self.assertFalse(service.worth("Che tempo fa domani?"))


class FlightTest(unittest.IsolatedAsyncioTestCase):

    async def test_the_final_turn_joins_the_thought_started_while_speaking(self):
        from agenti.agent import grounding
        grounding.cache.clear()
        calls = []

        async def slow(prompt, **kwargs):
            calls.append(prompt)
            await asyncio.sleep(DELAY)
            return {"lookup": True}

        with mock.patch.object(grounding, "generate", slow):
            started = time.monotonic()
            ahead = asyncio.create_task(grounding.needs_lookup("Chi ha vinto ieri sera"))
            await asyncio.sleep(DELAY * 0.7)
            final_at = time.monotonic()
            verdict = await grounding.needs_lookup("chi ha vinto ieri sera?")
            waited = time.monotonic() - final_at
            await ahead
        self.assertTrue(verdict)
        self.assertEqual(len(calls), 1)
        self.assertLess(waited, DELAY * 0.5)
        self.assertGreaterEqual(time.monotonic() - started, DELAY)

    async def test_a_failure_reaches_every_waiter_and_is_not_kept(self):
        flight = inflight.Flight()

        async def broken():
            await asyncio.sleep(0.01)
            raise ValueError("x")

        results = await asyncio.gather(flight.run("k", broken), flight.run("k", broken), return_exceptions=True)
        self.assertTrue(all(isinstance(r, ValueError) for r in results))
        self.assertEqual(flight.joined, 1)
        self.assertEqual(flight.running, {})

    async def test_think_ahead_warms_lookup_and_orchestration_on_the_resolved_command(self):
        service.recent.clear()
        lookup, orchestrate = mock.AsyncMock(), mock.AsyncMock()
        with mock.patch.object(service, "_lookup", lookup), mock.patch.object(service, "_orchestrate", orchestrate), \
                mock.patch.object(service.dialogue, "resolve", lambda device, text: text + " resolved"), \
                mock.patch.dict("os.environ", {"NUXIVA_ASSISTANT_NAME": "Nuxiva"}):
            self.assertTrue(await service.think_ahead("Nuxiva quanto costa un bitcoin", "kiosk"))
            self.assertFalse(await service.think_ahead("Nuxiva quanto costa un bitcoin", "kiosk"))
        lookup.assert_awaited_once_with("quanto costa un bitcoin resolved")
        orchestrate.assert_awaited_once_with("quanto costa un bitcoin resolved")


class WarmupTest(unittest.IsolatedAsyncioTestCase):

    async def test_only_public_cloud_providers_are_warmed_and_not_twice(self):
        from agenti.chat.anticipate import warmup
        warmup.warmed.clear()
        cfg = {"chat": ["cloud:groq/llama", "granite3.3:2b", "cloud:myserver/x"], "deep": ["cloud:anthropic/claude", "cloud:groq/other"]}
        client = mock.Mock()
        client.head = mock.AsyncMock()
        with mock.patch.object(warmup.brains, "config", lambda: cfg), mock.patch.object(warmup, "shared", lambda: client):
            self.assertEqual(warmup.hosts(), ["https://api.groq.com/openai/v1", "https://api.anthropic.com/v1"])
            self.assertEqual(await warmup.warm(), 2)
            self.assertEqual(await warmup.warm(), 0)
        for call in client.head.await_args_list:
            self.assertNotIn("headers", call.kwargs)


class RouteTest(unittest.TestCase):

    def test_display_only_bounded_and_rate_limited(self):
        from fastapi import FastAPI, HTTPException
        from fastapi.testclient import TestClient
        from agenti.chat.anticipate import routes

        def deny(request, message="x"):
            raise HTTPException(401, message)

        app = FastAPI()
        app.include_router(routes.router)
        client = TestClient(app)
        with mock.patch.object(routes, "require_display", deny):
            self.assertEqual(client.post("/api/assistant/anticipate", json={}).status_code, 401)
        queued = []
        with mock.patch.object(routes, "require_display", lambda request, message="": None), \
                mock.patch.object(routes, "is_host_display", lambda request: True), \
                mock.patch.object(routes, "background", lambda coro: (queued.append(coro), coro.close())), \
                mock.patch.object(routes, "thoughts", Budget(1)), mock.patch.object(routes, "warmups", Budget(1)):
            first = client.post("/api/assistant/anticipate", json={"text": "che tempo fa domani"}).json()
            second = client.post("/api/assistant/anticipate", json={"text": "che tempo fa dopodomani"}).json()
            self.assertEqual(client.post("/api/assistant/anticipate", json=["x"]).status_code, 400)
        self.assertEqual(first["queued"], {"warm": True, "think": True})
        self.assertEqual(second["queued"], {"warm": False, "think": False})
        self.assertEqual(len(queued), 2)


if __name__ == "__main__":
    unittest.main()
