import tempfile
from datetime import datetime
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access import require_admin
from features.people import people, private_store
from features.people.vitals import api as vitals_api
from features.people.vitals import book as book_module
from features.people.vitals import cloud, service
from features.people.vitals.lease import Arbiter
from features.people.vitals.live import Live
from features.people.vitals.model import clean_sample

MAC = "AA:BB:CC:DD:EE:01"
MAC2 = "AA:BB:CC:DD:EE:02"


class ModelTest(unittest.TestCase):
    def test_valid_and_invalid_samples(self):
        now = 1000.0
        self.assertEqual(clean_sample({"metric": "heart_rate", "value": "72.4", "ts": 990}, now)["value"], 72)
        self.assertEqual(clean_sample({"metric": "body_temp", "value": 36.62}, now)["value"], 36.6)
        for bad in ({"metric": "heart_rate", "value": 400}, {"metric": "spo2", "value": 50}, {"metric": "x", "value": 1},
                    {"metric": "heart_rate", "value": "abc"}, {"metric": "heart_rate", "value": float("nan")},
                    {"metric": "heart_rate", "value": 70, "ts": 5000}, {"metric": "heart_rate", "value": 70, "ts": -3000}, "x", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    clean_sample(bad, now)


class LiveTest(unittest.TestCase):
    def test_priority_wins_ties_and_newest_wins_otherwise(self):
        live = Live()
        live.put("a", {"metric": "heart_rate", "value": 70, "ts": 100.0}, "nodo", "ble", 101.0)
        live.put("a", {"metric": "heart_rate", "value": 72, "ts": 101.0}, "tel", "phone", 101.0)
        self.assertEqual(live.latest("a", 102.0)["heart_rate"]["source"], "tel")
        live.put("a", {"metric": "heart_rate", "value": 80, "ts": 110.0}, "nodo", "ble", 111.0)
        self.assertEqual(live.latest("a", 112.0)["heart_rate"]["value"], 80)

    def test_stale_values_disappear_and_duplicates_are_ignored(self):
        live = Live()
        self.assertTrue(live.put("a", {"metric": "spo2", "value": 97, "ts": 100.0}, "x", "ble", 100.0))
        self.assertFalse(live.put("a", {"metric": "spo2", "value": 97, "ts": 100.0}, "x", "ble", 100.0))
        self.assertEqual(live.latest("a", 400.0), {})


class LeaseTest(unittest.TestCase):
    def test_hysteresis_and_expiry(self):
        arb = Arbiter()
        self.assertEqual(arb.claim("a", "salotto", -70, now=0), "salotto")
        self.assertEqual(arb.claim("a", "cucina", -66, now=1), "salotto")
        self.assertEqual(arb.claim("a", "cucina", -55, now=2), "cucina")
        self.assertEqual(arb.holder("a", now=3), "cucina")
        self.assertEqual(arb.holder("a", now=100), "")
        self.assertEqual(arb.claim("a", "salotto", -90, now=100), "salotto")

    def test_camera_bonus_beats_a_slightly_stronger_signal(self):
        arb = Arbiter()
        arb.claim("a", "salotto", -60, now=0)
        self.assertEqual(arb.claim("a", "cucina", -64, face=True, now=1), "cucina")

    def test_garbage_rssi_is_clamped(self):
        arb = Arbiter()
        self.assertEqual(arb.claim("a", "n", "boh", now=0), "n")
        self.assertEqual(arb.view("a", now=1)["score"], -127.0)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        patches = (mock.patch.object(people, "PEOPLE_DIR", root), mock.patch.object(private_store, "KEY_FILE", root / "people.key"),
                   mock.patch.object(book_module, "FILE", root / "vitals.json"), mock.patch.object(vitals_api.store, "event"),
                   mock.patch.object(cloud, "ready", return_value=False))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        book_module.book._data = None
        service.live.forget("anna")
        service.arbiter._claims.clear()
        service.push_limit._hits.clear()
        service.node_limit._hits.clear()
        people.ensure("anna", "Anna Rossi")
        app = FastAPI()
        app.include_router(vitals_api.admin_routes)
        app.include_router(vitals_api.public_routes)
        app.dependency_overrides[require_admin] = lambda: "admin"
        self.client = TestClient(app)
        self.addCleanup(self.tmp.cleanup)


class DeviceApiTest(Base):
    def add(self, **body):
        return self.client.post("/api/people/anna/vitals/devices", json=body)

    def test_ble_device_needs_valid_address_and_is_unique(self):
        self.assertEqual(self.add(kind="ble", label="Fitbit", address="zz").status_code, 400)
        self.assertEqual(self.add(kind="ble", label="Fitbit", address=MAC.lower().replace(":", "-")).status_code, 200)
        self.assertEqual(self.add(kind="ble", label="Altro", address=MAC).status_code, 400)

    def test_push_device_token_is_shown_once_and_stored_hashed(self):
        data = self.add(kind="phone", label="Telefono").json()
        self.assertTrue(data["token"])
        listing = self.client.get("/api/people/anna/vitals").json()
        self.assertNotIn("token", listing["devices"][0])
        self.assertNotIn(data["token"], book_module.FILE.read_text())

    def test_unknown_kind_person_and_limits(self):
        self.assertEqual(self.add(kind="boh", label="x").status_code, 400)
        self.assertEqual(self.client.post("/api/people/nessuno/vitals/devices", json={"kind": "phone"}).status_code, 404)
        for i in range(6):
            self.assertEqual(self.add(kind="push", label=f"d{i}").status_code, 200)
        self.assertEqual(self.add(kind="push", label="troppi").status_code, 400)

    def test_rotate_and_remove(self):
        data = self.add(kind="push", label="Hub").json()
        old, did = data["token"], data["device"]["id"]
        new = self.client.post(f"/api/people/anna/vitals/devices/{did}/token").json()["token"]
        self.assertNotEqual(old, new)
        headers = {"Authorization": f"Bearer {old}"}
        self.assertEqual(self.client.post("/api/vitals/push", json={"samples": []}, headers=headers).status_code, 401)
        self.assertEqual(self.client.delete(f"/api/people/anna/vitals/devices/{did}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/people/anna/vitals/devices/{did}").status_code, 404)


class PushTest(Base):
    def setUp(self):
        super().setUp()
        self.token = self.client.post("/api/people/anna/vitals/devices", json={"kind": "phone", "label": "Tel"}).json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_push_accepts_valid_and_counts_rejected(self):
        now = time.time()
        body = {"samples": [{"metric": "heart_rate", "value": 71, "ts": now}, {"metric": "spo2", "value": 97, "ts": now},
                            {"metric": "heart_rate", "value": 999, "ts": now}]}
        result = self.client.post("/api/vitals/push", json=body, headers=self.headers).json()
        self.assertEqual(result, {"accepted": 2, "rejected": 1})
        values = self.client.get("/api/people/anna/vitals").json()["values"]
        self.assertEqual(values["heart_rate"]["value"], 71)
        self.assertEqual(values["spo2"]["kind"], "phone")

    def test_push_rejects_bad_auth_shape_size_and_flood(self):
        self.assertEqual(self.client.post("/api/vitals/push", json={"samples": []}).status_code, 401)
        self.assertEqual(self.client.post("/api/vitals/push", json={"samples": []}, headers={"Authorization": "Bearer x"}).status_code, 401)
        self.assertEqual(self.client.post("/api/vitals/push", json={"samples": "x"}, headers=self.headers).status_code, 400)
        self.assertEqual(self.client.post("/api/vitals/push", json={"samples": [{}] * 61}, headers=self.headers).status_code, 400)
        self.assertEqual(self.client.post("/api/vitals/push", content=b"x" * 9000, headers=self.headers).status_code, 413)
        self.assertEqual(self.client.post("/api/vitals/push", content=b"[1]", headers=self.headers).status_code, 400)
        codes = {self.client.post("/api/vitals/push", json={"samples": []}, headers=self.headers).status_code for _ in range(130)}
        self.assertIn(429, codes)

    def test_ble_devices_cannot_push(self):
        self.client.post("/api/people/anna/vitals/devices", json={"kind": "ble", "label": "B", "address": MAC})
        self.assertEqual(self.client.post("/api/vitals/push", json={"samples": []}, headers={"Authorization": "Bearer "}).status_code, 401)


class NodeTest(Base):
    def setUp(self):
        super().setUp()
        self.client.post("/api/people/anna/vitals/devices", json={"kind": "ble", "label": "Fitbit Air", "address": MAC})
        nodes = {"salotto": {"id": "salotto"}, "cucina": {"id": "cucina"}}

        def auth(node_id, token):
            if token != "ok" or node_id not in nodes:
                raise PermissionError("Nodo non autorizzato")
            return nodes[node_id]
        patcher = mock.patch.object(vitals_api.registry, "authenticate", side_effect=auth)
        patcher.start()
        self.addCleanup(patcher.stop)

    def report(self, node, body):
        return self.client.post("/api/vitals/node", json=body, headers={"x-nuxiva-node": node, "Authorization": "Bearer ok"})

    def test_unauthorised_nodes_are_refused(self):
        r = self.client.post("/api/vitals/node", json={}, headers={"x-nuxiva-node": "salotto", "Authorization": "Bearer no"})
        self.assertEqual(r.status_code, 401)

    def test_nearest_node_gets_the_lease_and_only_it_can_feed_samples(self):
        now = time.time()
        sample = {"address": MAC, "metric": "heart_rate", "value": 66, "ts": now}
        first = self.report("salotto", {"seen": [{"address": MAC, "rssi": -80}], "samples": [sample]}).json()
        self.assertEqual((first["connect"], first["accepted"]), ([MAC], 1))
        far = self.report("cucina", {"seen": [{"address": MAC, "rssi": -78}], "samples": [{**sample, "value": 150}]}).json()
        self.assertEqual((far["connect"], far["accepted"], far["ignored"]), ([], 0, 1))
        near = self.report("cucina", {"seen": [{"address": MAC, "rssi": -50}]}).json()
        self.assertEqual(near["connect"], [MAC])
        back = self.report("salotto", {"samples": [{**sample, "ts": now + 1, "value": 67}]}).json()
        self.assertEqual((back["connect"], back["accepted"]), ([], 0))
        self.assertEqual(service.live.latest("anna")["heart_rate"]["value"], 66)

    def test_camera_recognition_alone_starts_a_connection(self):
        out = self.report("cucina", {"faces": ["anna"]}).json()
        self.assertEqual(out["connect"], [MAC])
        self.assertEqual(out["watch"], [MAC])

    def test_unknown_addresses_and_garbage_are_ignored(self):
        out = self.report("salotto", {"seen": [{"address": MAC2, "rssi": -40}, "x", {"rssi": 1}], "faces": [1, None], "samples": [{"address": MAC2}, 5]}).json()
        self.assertEqual((out["connect"], out["accepted"]), ([], 0))


class CloudTest(unittest.TestCase):
    def test_google_points_are_parsed_and_validated(self):
        now = 1_800_000_000.0
        stamp = "2027-01-15T08:00:00Z"
        ts = datetime.fromisoformat("2027-01-15T08:00:00+00:00").timestamp()
        body = {"dataPoints": [{"heartRate": {"sampleTime": {"physicalTime": stamp}, "beatsPerMinute": "64"}},
                               {"heartRate": {"sampleTime": {"physicalTime": stamp}, "beatsPerMinute": "9999"}}, {"x": 1}, "y"]}
        rows = cloud.points(body, "heartRate", "beatsPerMinute", "heart_rate", ts + 5)
        self.assertEqual([(r["metric"], r["value"]) for r in rows], [("heart_rate", 64)])
        self.assertEqual(cloud.points({}, "heartRate", "beatsPerMinute", "heart_rate", now), [])



class GuidedFlowTest(NodeTest):
    def nodes_online(self):
        return mock.patch.object(service, "capable_nodes", return_value=["Salotto"])

    def beacon(self, rows, node="salotto"):
        return self.report(node, {"nearby": rows}).json()

    def test_search_lists_health_devices_without_exposing_addresses(self):
        with self.nodes_online():
            self.client.delete(f"/api/people/anna/vitals/devices/{self.client.get('/api/people/anna/vitals').json()['devices'][0]['id']}")
            self.assertEqual(self.client.post("/api/people/anna/vitals/search").json()["nodes"], ["Salotto"])
            first = self.beacon([{"address": "11:22:33:44:55:66", "name": "Fitbit Air", "rssi": -50, "services": []},
                                 {"address": "11:22:33:44:55:77", "name": "TV Samsung", "rssi": -40, "services": []},
                                 {"address": "11:22:33:44:55:88", "name": "", "rssi": -70, "services": ["0000180d-0000-1000-8000-00805f9b34fb"]},
                                 {"address": "zz", "name": "Polar", "rssi": -50}])
            self.assertTrue(first["discover"])
            data = self.client.get("/api/people/anna/vitals/nearby").json()
            self.assertEqual([d["name"] for d in data["found"]], ["Fitbit Air", ""])
            self.assertEqual(data["found"][0]["level"], 4)
            self.assertTrue(data["found"][1]["standard"])
            self.assertNotIn("11:22", str(data))

    def test_nothing_is_collected_when_nobody_searches(self):
        self.assertFalse(self.beacon([{"address": "11:22:33:44:55:66", "name": "Fitbit Air", "rssi": -50}])["discover"])
        self.assertEqual(self.client.get("/api/people/anna/vitals/nearby").json()["found"], [])

    def test_pick_from_the_list_creates_the_device_and_ends_the_search(self):
        with self.nodes_online():
            self.client.post("/api/people/anna/vitals/search")
            self.beacon([{"address": "11:22:33:44:55:66", "name": "Fitbit Air", "rssi": -50}])
            ref = self.client.get("/api/people/anna/vitals/nearby").json()["found"][0]["ref"]
            r = self.client.post("/api/people/anna/vitals/devices", json={"kind": "ble", "label": "Fitbit Air", "ref": ref})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["device"]["address"], "11:22:33:44:55:66")
            self.assertEqual(self.client.get("/api/people/anna/vitals/nearby").json()["found"], [])
            bad = self.client.post("/api/people/anna/vitals/devices", json={"kind": "ble", "label": "x", "ref": "nonesiste"})
            self.assertEqual(bad.status_code, 400)

    def test_search_without_capable_nodes_is_logged_with_a_warning(self):
        with mock.patch.object(service, "capable_nodes", return_value=[]):
            self.assertEqual(self.client.post("/api/people/anna/vitals/search").json()["nodes"], [])
        entries = self.client.get("/api/people/anna/vitals/log").json()["entries"]
        self.assertEqual((entries[0]["code"], entries[0]["level"]), ("search_no_nodes", "warn"))

    def test_errors_and_profiles_reported_by_nodes_reach_the_log_and_state(self):
        now = time.time()
        self.report("salotto", {"seen": [{"address": MAC, "rssi": -60}], "errors": [{"address": MAC, "code": "connect_failed"}, {"address": MAC, "code": "boh"}]})
        self.report("salotto", {"profiles": {MAC: []}})
        codes = [e["code"] for e in self.client.get("/api/people/anna/vitals/log").json()["entries"]]
        self.assertIn("connect_failed", codes)
        self.assertIn("no_profiles", codes)
        self.assertNotIn("boh", codes)
        self.assertEqual(self.client.get("/api/people/anna/vitals").json()["devices"][0]["state"], "unsupported")
        self.report("salotto", {"profiles": {MAC: ["heart_rate"]}})
        self.assertEqual(self.client.get("/api/people/anna/vitals").json()["devices"][0]["state"], "connected")
        self.report("salotto", {"samples": [{"address": MAC, "metric": "heart_rate", "value": 70, "ts": now}]})
        self.assertEqual(self.client.get("/api/people/anna/vitals").json()["devices"][0]["state"], "streaming")

    def test_device_states_progress_from_waiting_to_seen(self):
        self.assertEqual(self.client.get("/api/people/anna/vitals").json()["devices"][0]["state"], "waiting")
        self.report("cucina", {"seen": [{"address": MAC, "rssi": -70}]})
        service.arbiter._claims.clear()
        self.assertEqual(self.client.get("/api/people/anna/vitals").json()["devices"][0]["state"], "seen")

    def test_repeated_errors_do_not_flood_the_log(self):
        for _ in range(5):
            self.report("salotto", {"errors": [{"address": MAC, "code": "connect_failed"}]})
        entries = [e for e in self.client.get("/api/people/anna/vitals/log").json()["entries"] if e["code"] == "connect_failed"]
        self.assertEqual(len(entries), 1)


class PhoneCodeTest(Base):
    def test_code_pairs_a_phone_once(self):
        code = self.client.post("/api/people/anna/vitals/phone-code").json()["code"]
        self.assertRegex(code, r"^\d{6}$")
        ok = self.client.post("/api/vitals/pair", json={"code": code, "label": "Pixel"})
        self.assertEqual(ok.status_code, 200)
        headers = {"Authorization": f"Bearer {ok.json()['token']}"}
        self.assertEqual(self.client.post("/api/vitals/push", json={"samples": []}, headers=headers).status_code, 200)
        self.assertEqual(self.client.post("/api/vitals/pair", json={"code": code}).status_code, 403)

    def test_wrong_codes_are_refused_and_throttled(self):
        service.pair_limit._hits.clear()
        codes = [self.client.post("/api/vitals/pair", json={"code": "000000"}).status_code for _ in range(12)]
        self.assertEqual(codes[0], 403)
        self.assertIn(429, codes)



class SwitchTest(NodeTest):
    def device(self):
        return self.client.get("/api/people/anna/vitals").json()["devices"][0]

    def test_disconnect_stops_everything_and_reconnect_restarts(self):
        did = self.device()["id"]
        now = time.time()
        self.report("salotto", {"seen": [{"address": MAC, "rssi": -60}], "samples": [{"address": MAC, "metric": "heart_rate", "value": 70, "ts": now}]})
        self.assertEqual(self.client.post(f"/api/people/anna/vitals/devices/{did}/disconnect").status_code, 200)
        self.assertEqual(self.device()["state"], "off")
        out = self.report("salotto", {"seen": [{"address": MAC, "rssi": -60}], "samples": [{"address": MAC, "metric": "heart_rate", "value": 71, "ts": now + 1}]}).json()
        self.assertEqual((out["watch"], out["connect"], out["accepted"]), ([], [], 0))
        self.assertEqual(service.live.latest("anna"), {})
        self.assertEqual(self.client.post(f"/api/people/anna/vitals/devices/{did}/reconnect").status_code, 200)
        back = self.report("salotto", {"seen": [{"address": MAC, "rssi": -60}]}).json()
        self.assertEqual(back["connect"], [MAC])

    def test_reconnect_tells_the_node_to_drop_the_old_link_once(self):
        did = self.device()["id"]
        self.client.post(f"/api/people/anna/vitals/devices/{did}/reconnect")
        out = self.report("salotto", {"seen": [{"address": MAC, "rssi": -60}]}).json()
        self.assertEqual([d["address"] for d in out["drop"]], [MAC])
        self.assertTrue(out["drop"][0]["nonce"])

    def test_disabled_push_device_cannot_send(self):
        data = self.client.post("/api/people/anna/vitals/devices", json={"kind": "phone", "label": "Tel"}).json()
        headers = {"Authorization": f"Bearer {data['token']}"}
        self.assertEqual(self.client.post("/api/vitals/push", json={"samples": []}, headers=headers).status_code, 200)
        self.client.post(f"/api/people/anna/vitals/devices/{data['device']['id']}/disconnect")
        self.assertEqual(self.client.post("/api/vitals/push", json={"samples": []}, headers=headers).status_code, 401)
        self.client.post(f"/api/people/anna/vitals/devices/{data['device']['id']}/reconnect")
        self.assertEqual(self.client.post("/api/vitals/push", json={"samples": []}, headers=headers).status_code, 200)

    def test_unknown_action_or_device(self):
        self.assertEqual(self.client.post("/api/people/anna/vitals/devices/aaaa/boh").status_code, 404)
        self.assertEqual(self.client.post("/api/people/anna/vitals/devices/aaaa/disconnect").status_code, 404)


if __name__ == "__main__":
    unittest.main()
