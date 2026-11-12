import unittest
from server.features.agent_tools.scanner import tool_scanner
from server.features.agent_tools.base import BaseAgentTool

class TestToolScanner(unittest.TestCase):
    def test_tools_discovered(self):
        tools = tool_scanner.scan_all()
        self.assertGreaterEqual(len(tools), 5)
        self.assertIn("web_search", tools)
        self.assertIn("maps", tools)
        self.assertIn("music", tools)
        self.assertIn("cad", tools)
        self.assertIn("social", tools)

    def test_get_tool_by_id_and_alias(self):
        tool = tool_scanner.get_tool("web_search")
        self.assertIsNotNone(tool)
        self.assertIsInstance(tool, BaseAgentTool)
        self.assertEqual(tool.manifest.id, "web_search")

        maps_tool = tool_scanner.get_tool("maps")
        self.assertIsNotNone(maps_tool)
        self.assertEqual(maps_tool.manifest.name, "Google Maps Route")

if __name__ == "__main__":
    unittest.main()
