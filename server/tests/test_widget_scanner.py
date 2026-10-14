import unittest
from server.web.widgets.scanner import widget_scanner
from server.web.widgets.base import BaseWidget

class TestWidgetScanner(unittest.TestCase):
    def test_widgets_discovered(self):
        widgets = widget_scanner.scan_all()
        self.assertGreaterEqual(len(widgets), 4)
        self.assertIn("system_status", widgets)
        self.assertIn("quick_actions", widgets)
        self.assertIn("weather", widgets)
        self.assertIn("smart_switch", widgets)

    def test_widget_state_execution(self):
        widget = widget_scanner.get_widget("smart_switch")
        self.assertIsNotNone(widget)
        self.assertIsInstance(widget, BaseWidget)
        self.assertEqual(widget.manifest.icon, "💡")

if __name__ == "__main__":
    unittest.main()
