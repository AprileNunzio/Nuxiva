import unittest
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _ROOT / "installer_wizard" / "backend"
_SERVER = _ROOT / "server"
for p in (str(_ROOT), str(_BACKEND), str(_SERVER)):
    if p not in sys.path:
        sys.path.insert(0, p)

from node_api import (
    get_usb_ports,
    onboard_node,
    delete_node,
    list_nodes,
    OnboardNodeRequest,
)


class NodesProvisioningApiTests(unittest.TestCase):
    def test_get_usb_ports_returns_list(self):
        ports = get_usb_ports()
        self.assertIsInstance(ports, list)
        for p in ports:
            self.assertIn("device", p)
            self.assertIn("description", p)

    def test_onboard_esp32_satellite(self):
        req = OnboardNodeRequest(
            target="esp32",
            name="LivingRoom-Mic-ESP32",
            parent_id="virtual_core",
            parent_ip="192.168.1.10",
            usb_port="/dev/ttyUSB0",
            wifi_ssid="HomeMesh_5G",
            wifi_key="secretpass123",
        )
        res = onboard_node(req)
        self.assertEqual(res["target"], "esp32")
        self.assertEqual(res["name"], "LivingRoom-Mic-ESP32")
        self.assertEqual(res["status"], "provisioned")
        self.assertIn("Tier-3", res["tier"])
        self.assertIn("node-esp32", res["node_id"])

        # Verifica che sia presente nella lista nodi
        nodes = list_nodes()
        node_ids = [n["id"] for n in nodes]
        self.assertIn(res["node_id"], node_ids)

        # De-provisioning / rimozione
        del_res = delete_node(res["node_id"])
        self.assertTrue(del_res["removed"])
        self.assertEqual(del_res["status"], "deleted")

    def test_onboard_pc_workstation(self):
        req = OnboardNodeRequest(
            target="pc",
            name="Studio-i9-GPU",
            parent_id="virtual_core",
            parent_ip="192.168.1.200",
        )
        res = onboard_node(req)
        self.assertEqual(res["target"], "pc")
        self.assertIn("Tier-1", res["tier"])

        del_res = delete_node(res["node_id"])
        self.assertTrue(del_res["removed"])

    def test_rename_node(self):
        from node_api import rename_node, get_node, RenameNodeRequest
        req = RenameNodeRequest(name="Salotto Principale Nuxiva")
        res = rename_node("node-test-rename", req)
        self.assertEqual(res["status"], "renamed")
        self.assertEqual(res["name"], "Salotto Principale Nuxiva")

        # Verify get_node reflects the custom name
        node = get_node("node-test-rename")
        self.assertEqual(node["name"], "Salotto Principale Nuxiva")


    def test_node_brain_lifecycle(self):
        import asyncio
        from node_api import (
            get_node_brain,
            save_node_brain,
            test_node_brain,
            BrainConfigRequest,
            BrainTestRequest,
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 1. Fetch default brain config
            brain_data = loop.run_until_complete(get_node_brain("node-test-01"))
            self.assertIn("config", brain_data)
            self.assertIn("local_ollama", brain_data)
            self.assertIn("cloud_providers", brain_data)

            # 2. Save new brain config
            save_req = BrainConfigRequest(
                mode="cloud_llm",
                cloud_provider="deepseek",
                cloud_model="deepseek-chat",
                cloud_api_key="sk-testkey123",
                temperature=0.5,
            )
            saved = save_node_brain("node-test-01", save_req)
            self.assertEqual(saved["status"], "saved")
            self.assertEqual(saved["config"]["cloud_provider"], "deepseek")

            # 3. Test brain inference error handling for missing key or offline host
            test_req = BrainTestRequest(
                mode="cloud_llm",
                cloud_provider="deepseek",
                cloud_api_key="",
            )
            test_res = loop.run_until_complete(test_node_brain("node-test-01", test_req))
            self.assertFalse(test_res["success"])
            self.assertIn("mancante", test_res["error"])
        finally:
            loop.close()

    def test_node_hardware_and_whiteboards(self):
        from node_api import (
            get_node_hardware,
            test_node_audio,
            test_node_print,
            list_node_whiteboards,
            save_node_whiteboard,
            delete_node_whiteboard,
            HardwareTestToneRequest,
            HardwareTestPrintRequest,
            WhiteboardSaveRequest,
        )

        # Hardware
        hw = get_node_hardware("node-test-01")
        self.assertIn("audio_outputs", hw)
        self.assertIn("audio_inputs", hw)
        self.assertIn("cameras", hw)
        self.assertIn("printers", hw)
        self.assertIn("bluetooth", hw)
        self.assertIn("display", hw)

        # Audio tone test
        audio_res = test_node_audio("node-test-01", HardwareTestToneRequest(frequency=880))
        self.assertTrue(audio_res["success"])
        self.assertEqual(audio_res["frequency"], 880)

        # Print test
        print_res = test_node_print("node-test-01", HardwareTestPrintRequest(printer_id="printer-hp-laser"))
        self.assertTrue(print_res["success"])
        self.assertIn("job-print", print_res["job_id"])

        # Whiteboards
        wb_save = save_node_whiteboard("node-test-01", WhiteboardSaveRequest(title="Diagramma Architettura Mesh", strokes_count=25))
        self.assertEqual(wb_save["status"], "saved")
        wb_id = wb_save["whiteboard"]["id"]

        wbs = list_node_whiteboards("node-test-01")
        self.assertTrue(any(w["id"] == wb_id for w in wbs))

        del_wb = delete_node_whiteboard("node-test-01", wb_id)
        self.assertEqual(del_wb["status"], "deleted")

    def test_ollama_local_and_remote_mesh_endpoints(self):
        from node_api import (
            get_local_ollama_status,
            install_local_ollama,
            uninstall_local_ollama,
            get_node_remote_mesh_instances,
            save_node_remote_mesh_instances,
            RemoteMeshSaveRequest,
            RemoteOllamaInstance,
        )

        # 1. Local Ollama status probe
        status = get_local_ollama_status("node-test-01")
        self.assertIn("installed", status)
        self.assertIn("running", status)
        self.assertIn("models", status)
        self.assertIn("catalog", status)

        # 2. Automated Install & Uninstall invocation
        install_res = install_local_ollama("node-test-01")
        self.assertIn("status", install_res)
        self.assertIn(install_res["status"], ("installing", "manual_action_required", "success"))

        uninstall_res = uninstall_local_ollama("node-test-01")
        self.assertIn("status", uninstall_res)
        self.assertIn(uninstall_res["status"], ("uninstalled", "manual_action_required"))

        # 3. Multi-instance Remote Mesh Ollama configuration
        remote_res = get_node_remote_mesh_instances("node-test-01")
        self.assertIn("instances", remote_res)
        self.assertIsInstance(remote_res["instances"], list)

        # Save multiple remote instances with specialized tasks
        new_instances = [
            RemoteOllamaInstance(
                id="inst-test-fast",
                name="Workstation-RTX4090",
                host_url="http://192.168.1.50:11434",
                model="llama3.2:3b",
                task="fast_chat",
                latency_ms=1.8,
            ),
            RemoteOllamaInstance(
                id="inst-test-reasoning",
                name="Server-Studio-GPU",
                host_url="http://192.168.1.60:11434",
                model="deepseek-r1:7b",
                task="deep_reasoning",
                latency_ms=4.2,
            ),
        ]
        save_remote_res = save_node_remote_mesh_instances("node-test-01", RemoteMeshSaveRequest(instances=new_instances))
        self.assertEqual(save_remote_res["status"], "saved")
        self.assertEqual(len(save_remote_res["instances"]), 2)
        self.assertEqual(save_remote_res["instances"][0]["task"], "fast_chat")
        self.assertEqual(save_remote_res["instances"][1]["task"], "deep_reasoning")


if __name__ == "__main__":
    unittest.main()

