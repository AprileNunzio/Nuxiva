import asyncio
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "backend"), str(ROOT / "agenti" / "percezione" / "ear")):
    if p not in sys.path:
        sys.path.insert(0, p)

from agenti.ear.danger import rescue_control
from agenti.rescue import contacts
from agenti.rescue.channels import Dispatcher
from agenti.rescue.coordinator import RescueCoordinator
from agenti.rescue.ear_link import EarLink, translate

PEOPLE = [
    {"slug": "nonna", "first_name": "Rosa", "role": "family", "emergency": [{"person": "marco"}, {"name": "Vicina", "phone": "1"}]},
    {"slug": "marco", "first_name": "Marco", "role": "owner", "ui_language": "it"},
    {"slug": "lucia", "first_name": "Lucia", "role": "family", "emergency": [{"person": "zio"}]},
    {"slug": "zio", "first_name": "Zio <b>", "role": "friend", "ui_language": "en"},
    {"slug": "ospite", "first_name": "Ospite", "role": "guest"},
]


class FakeTelegram:
    def __init__(self, chats=None, fail=()):
        self.map = chats if chats is not None else {"marco": ["100"], "lucia": ["200"], "zio": ["300"]}
        self.fail = set(fail)
        self.sent = []
        self.cleared = []
        self.next = 1

    def chats(self, slug):
        return list(self.map.get(slug, []))

    def owners(self):
        return list(self.map.get("marco", []))

    async def send(self, chat_id, text, buttons):
        self.sent.append((chat_id, text, buttons))
        if chat_id in self.fail:
            return None
        self.next += 1
        return self.next

    async def clear(self, chat_id, message_id):
        self.cleared.append((chat_id, message_id))


class FakeAlarm:
    def __init__(self):
        self.triggered = []
        self.stopped = 0

    def trigger(self, message):
        self.triggered.append(message)

    def stop(self):
        self.stopped += 1


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def build(telegram=None, people=PEOPLE):
    clock = Clock()
    coord = RescueCoordinator(prefer_native=False)
    ear_sent = []

    async def ear(message):
        ear_sent.append(message)
        return True

    audits = []
    alarm = FakeAlarm()
    tg = telegram or FakeTelegram()
    disp = Dispatcher(coord, tg, ear, alarm, lambda: people, lambda kind, inc, params: audits.append((kind, params)), clock)
    coord.listeners.append(disp.submit)
    return coord, disp, tg, alarm, ear_sent, audits, clock


@mock.patch("agenti.sentinel.record.record")
class RescueAlertsTest(unittest.TestCase):
    def test_contacts_plan_orders_subject_contacts_then_household(self, _):
        levels = contacts.plan(PEOPLE, "nonna", 2)
        self.assertEqual(levels[0], ["marco", "lucia"])
        self.assertEqual(levels[1], ["zio"])
        self.assertNotIn("ospite", contacts.everyone(levels))
        self.assertEqual(contacts.plan(PEOPLE, None, 1)[0], ["marco", "lucia", "nonna"])
        self.assertEqual(contacts.plan(PEOPLE, "../x", 3)[2], ["zio"])
        self.assertEqual(contacts.plan([], None, 2), [[], []])

    def test_translate_maps_ear_events(self, _):
        self.assertEqual(translate({"type": "danger", "source": "sound", "kind": "smoke_alarm", "probability": 0.9,
                                    "confidence": 0.8}), [("observe", "smoke", 0.9, 0.8, "ear:sound")])
        self.assertEqual(translate({"type": "danger", "source": "sound", "kind": "boom", "probability": 1, "confidence": 1}), [])
        words = translate({"type": "danger", "source": "words", "help": 0.9, "threat": 0.1, "fire": 0.0,
                           "confidence": 0.7, "answer": "not_ok", "asked": False, "speaker": "nonna"})
        self.assertEqual(words, [("observe", "help_words", 0.9, 0.7, "ear:words"), ("subject", "nonna")])
        self.assertEqual(translate({"type": "danger", "source": "words", "help": 0.0, "threat": 0.0, "fire": 0.0,
                                    "confidence": 0.9, "answer": "ok", "asked": True}), [("answer", "ok", "voice")])
        self.assertEqual(translate({"type": "danger", "source": "words", "help": 0.0, "threat": 0.0, "fire": 0.0,
                                    "confidence": 0.9, "answer": "ok", "asked": False}), [])
        self.assertEqual(translate({"type": "danger", "source": "words", "help": float("nan"), "confidence": 0.9}), [])
        self.assertEqual(translate({"type": "danger", "source": "touch", "answer": "not_ok"}), [("answer", "not_ok", "touch")])
        self.assertEqual(translate({"type": "danger", "source": "words", "help": 0.9, "confidence": 0.9,
                                    "speaker": "../../etc"}), [("observe", "help_words", 0.9, 0.9, "ear:words")])
        self.assertEqual(translate({"type": "level"}), [])
        self.assertEqual(translate("x"), [])

    def test_help_words_alert_family_with_buttons_and_ack(self, _):
        coord, disp, tg, alarm, ear, audits, clock = build()
        link = EarLink(coord, disp, clock)

        async def flow():
            link.apply({"type": "danger", "source": "words", "help": 0.97, "threat": 0, "fire": 0, "confidence": 0.95,
                        "answer": "not_ok", "asked": False, "speaker": "nonna"})
            link.apply({"type": "danger", "source": "touch", "answer": "not_ok"})
            await disp.flush()
            self.assertEqual(coord.status()["stage"], "alerting")
            chats = [c for c, _, b in tg.sent if b]
            self.assertEqual(chats, ["100", "200", "300"])
            text = tg.sent[0][1]
            self.assertIn("Rosa", text)
            self.assertIn("112", text)
            self.assertIn("dispositivo medico", text)
            token = tg.sent[0][2][0][0]["callback_data"]
            self.assertTrue(token.startswith("rescue:") and token.endswith(":a"))
            self.assertLessEqual(len(token.encode()), 64)
            self.assertIn(("delivery", {"delivered": 2, "total": 2, "tier": 0}), audits)
            self.assertIn("rescue_remind", [m["type"] for m in ear])
            stale = await disp.callback("100", "rescue:" + "0" * 16 + ":a")
            self.assertEqual(coord.status()["stage"], "alerting")
            self.assertIn("non", stale)
            outsider = await disp.callback("999", token)
            self.assertEqual(coord.status()["stage"], "alerting")
            self.assertTrue(outsider)
            await disp.callback("200", token)
            self.assertEqual(coord.status()["stage"], "acknowledged")
            ack = [m for m in ear if m["type"] == "rescue_ack"]
            self.assertEqual(ack[-1]["name"], "Lucia")
            notified = [c for c, t, b in tg.sent if b is None]
            self.assertEqual(notified, ["100", "300"])
            self.assertEqual(alarm.triggered, [])

        asyncio.run(flow())

    def test_unreachable_contacts_spread_alarm_in_home_and_retry(self, _):
        coord, disp, tg, alarm, ear, audits, clock = build(FakeTelegram(fail={"100", "200"}))

        async def flow():
            coord.need_help(now=clock())
            await disp.flush()
            self.assertEqual(len(alarm.triggered), 1)
            self.assertIn(("unreachable", {"hazard": "medical"}), audits)
            tg.fail.clear()
            clock.t += 6
            await disp.flush()
            self.assertEqual(sorted(disp.incident.recipients), ["100", "200"])

        asyncio.run(flow())

    def test_cancel_from_telegram_stands_down_everything(self, _):
        coord, disp, tg, alarm, ear, audits, clock = build()

        async def flow():
            coord.need_help(now=clock())
            await disp.flush()
            token = tg.sent[0][2][1][0]["callback_data"]
            self.assertTrue(token.endswith(":c"))
            await disp.callback("100", token)
            self.assertEqual(coord.status()["stage"], "cooldown")
            self.assertEqual(alarm.stopped, 1)
            self.assertIn("rescue_stop", [m["type"] for m in ear])
            self.assertTrue(disp.incident.closed)
            again = await disp.callback("100", token)
            self.assertIn("non", again)
            self.assertEqual(len(tg.cleared), 2)

        asyncio.run(flow())

    def test_voice_cannot_cancel_violence(self, _):
        coord, disp, tg, alarm, ear, audits, clock = build()
        link = EarLink(coord, disp, clock)

        async def flow():
            self.assertEqual(link.apply({"type": "danger", "source": "words", "help": 0, "threat": 0.99, "fire": 0,
                                         "confidence": 1.0}), 1)
            coord.observe("violence", 0.99, 1.0, "mic2", at=clock(), now=clock())
            await disp.flush()
            stage = coord.status()["stage"]
            self.assertIn(stage, ("check_in", "alerting"))
            self.assertEqual(coord.status()["hazard"], "violence")
            link.apply({"type": "danger", "source": "touch", "answer": "ok"})
            self.assertEqual(coord.status()["stage"], stage)
            ask = [m for m in ear if m["type"] == "rescue_ask"]
            self.assertTrue(all(m["tone"] == "discreet" for m in ask))

        asyncio.run(flow())

    def test_person_ok_by_touch_during_check_in(self, _):
        coord, disp, tg, alarm, ear, audits, clock = build()
        link = EarLink(coord, disp, clock)

        async def flow():
            coord.observe("fall", 0.9, 0.8, "cam", at=clock(), now=clock())
            coord.observe("immobility", 0.9, 0.8, "cam", at=clock(), now=clock())
            await disp.flush()
            self.assertEqual(coord.status()["stage"], "check_in")
            self.assertEqual(ear[0]["type"], "rescue_ask")
            self.assertEqual(link.apply({"type": "danger", "source": "touch", "answer": "ok"}), 1)
            await disp.flush()
            self.assertEqual(coord.status()["stage"], "cooldown")
            self.assertEqual(tg.sent, [])
            self.assertEqual(link.apply({"type": "danger", "source": "touch", "answer": "ok"}), 0)

        asyncio.run(flow())

    def test_ear_rescue_control_broadcasts_prompts(self, _):
        class Session:
            def __init__(self):
                self.asked = None
                self.danger = self
                self.asked_until = 5.0

            def ask(self, seconds):
                self.asked = seconds

        sessions = {Session(), Session()}
        out = []

        async def broadcast(**event):
            out.append(event)

        async def flow():
            await rescue_control("rescue_ask", {"seconds": 40, "hazard": "fire", "tone": "x", "number": "١١٢",
                                                "name": "<script>"}, sessions, broadcast)
            await rescue_control("rescue_answer", {"answer": "ok"}, sessions, broadcast)
            await rescue_control("rescue_answer", {"answer": "maybe"}, sessions, broadcast)
            await rescue_control("rescue_stop", {}, sessions, broadcast)

        asyncio.run(flow())
        self.assertTrue(all(s.asked == 40 for s in sessions))
        self.assertTrue(all(s.asked_until == 0.0 for s in sessions))
        self.assertEqual(out[0], {"type": "rescue_prompt", "stage": "ask", "hazard": "fire", "tone": "spoken",
                                  "seconds": 40, "number": "112", "name": "script"})
        self.assertEqual(out[1], {"type": "danger", "source": "touch", "answer": "ok"})
        self.assertEqual(out[2]["stage"], "stop")
        self.assertEqual(len(out), 3)


if __name__ == "__main__":
    unittest.main()
