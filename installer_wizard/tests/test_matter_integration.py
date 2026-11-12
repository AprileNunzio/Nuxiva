import unittest
from fastapi import FastAPI
from starlette.testclient import TestClient

from access import require_admin
from agenti.chat.intents import detect_intent
from agenti.chat.skill_dispatch import run_skill
from agenti.matter.api import admin_routes
from agenti.matter.bridge import MatterBridge
from agenti.matter.controller import MatterController
from agenti.matter.coordinator import MatterCoordinator
from agenti.matter.model import (
    MatterClusterId,
    MatterCommandId,
    MatterDeviceType,
)

class MatterIntegrationTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.dependency_overrides[require_admin] = lambda: "admin"
        self.app.include_router(admin_routes)
        self.client = TestClient(self.app)

    def test_matter_bridge_entity_lifecycle(self):
        bridge = MatterBridge(node_id=0x11223344, vendor_id=0xFFF1, product_id=0x8001)
        ep1 = bridge.bridge_entity("light.kitchen", "on_off_light", "Cucina")
        self.assertEqual(ep1, 1)

        ep2 = bridge.bridge_entity("camera.garden_ptz", "security_camera_ptz", "Giardino 360")
        self.assertEqual(ep2, 2)

        ok = bridge.update_state("light.kitchen", MatterClusterId.ON_OFF.value, 0x0000, True)
        self.assertTrue(ok)
        val = bridge.read_attribute(1, MatterClusterId.ON_OFF.value, 0x0000)
        self.assertEqual(val, True)

        endpoints = bridge.list_endpoints()
        self.assertGreaterEqual(len(endpoints), 3)

    def test_matter_controller_commission_and_ptz_invoke(self):
        controller = MatterController()
        res = controller.commission("1234-5678", name="Salotto PTZ", device_type=MatterDeviceType.SECURITY_CAMERA.value)
        self.assertEqual(res["status"], "commissioned")
        node_id = res["node_id"]

        move_res = controller.invoke_command(
            node_id=node_id,
            endpoint_id=1,
            cluster_id=MatterClusterId.PAN_TILT_ZOOM_CONTROL.value,
            command_id=MatterCommandId.PTZ_MOVE.value,
            payload={"pan": 180.0, "tilt": 45.0, "zoom": 2.5},
        )
        self.assertEqual(move_res["status"], "success")

        node = controller.get_node(node_id)
        self.assertIsNotNone(node)
        ptz_cl = node.endpoints[1].clusters[MatterClusterId.PAN_TILT_ZOOM_CONTROL.value]
        self.assertEqual(ptz_cl.attributes[0x0001].value, 180.0)
        self.assertEqual(ptz_cl.attributes[0x0002].value, 45.0)
        self.assertEqual(ptz_cl.attributes[0x0003].value, 2.5)

    def test_matter_coordinator_status_and_defaults(self):
        coordinator = MatterCoordinator.instance()
        status = coordinator.get_status()
        self.assertEqual(status["spec"], "1.6.1")
        self.assertEqual(status["standard"], "Matter 1.6.1 (CSA)")
        self.assertTrue(status["bridge_active"])
        self.assertGreaterEqual(status["bridge_endpoints_count"], 1)

    def test_matter_api_endpoints(self):
        resp = self.client.get("/api/matter/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["spec"], "1.6.1")

        resp_disc = self.client.get("/api/matter/discover?timeout=0.1")
        self.assertEqual(resp_disc.status_code, 200)
        self.assertIn("discovered", resp_disc.json())

        resp_auto = self.client.post(
            "/api/matter/auto_enroll",
            json={
                "ip": "192.168.1.188",
                "discriminator": 1234,
                "device_name": "Matter Smart Plug",
                "device_type": MatterDeviceType.ON_OFF_PLUG.value,
            },
        )
        self.assertEqual(resp_auto.status_code, 200)
        auto_data = resp_auto.json()
        self.assertTrue(auto_data.get("auto_enrolled"))

        resp_nodes = self.client.get("/api/matter/nodes")
        self.assertEqual(resp_nodes.status_code, 200)

        resp_comm = self.client.post(
            "/api/matter/commission",
            json={"pairing_code": "9876-5432", "name": "Luce Ufficio", "device_type": MatterDeviceType.ON_OFF_LIGHT.value},
        )
        self.assertEqual(resp_comm.status_code, 200)
        comm_data = resp_comm.json()
        node_id = comm_data["node_id"]

        resp_inv = self.client.post(
            "/api/matter/clusters/invoke",
            json={
                "node_id": node_id,
                "endpoint_id": 1,
                "cluster_id": MatterClusterId.ON_OFF.value,
                "command_id": MatterCommandId.ON.value,
            },
        )
        self.assertEqual(resp_inv.status_code, 200)

        resp_sync = self.client.post("/api/matter/bridge/sync")
        self.assertEqual(resp_sync.status_code, 200)

        resp_bridge = self.client.get("/api/matter/bridge/endpoints")
        self.assertEqual(resp_bridge.status_code, 200)
        self.assertIn("endpoints", resp_bridge.json())

    async def test_matter_brain_intent_and_skill(self):
        intent = detect_intent("mostrami i dispositivi matter collegati")
        self.assertEqual(intent, "matter")

        speech, ui = await run_skill("matter", "dispositivi matter")
        self.assertIn("Matter 1.6.1", speech)
        self.assertEqual(ui["mode"], "matter")
        self.assertEqual(ui["spec"], "1.6.1")

if __name__ == "__main__":
    unittest.main()
