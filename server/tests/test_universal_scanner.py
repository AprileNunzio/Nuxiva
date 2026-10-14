import os
import shutil
import tempfile
import unittest
from server.core.scanner.base import BaseDiscoverable, DiscoveryManifest
from server.core.scanner.universal_scanner import UniversalScanner
from server.core.scanner.security import ZeroTrustValidator, SecurityViolationError

class DummyItem(BaseDiscoverable):
    def __init__(self, manifest_data=None):
        self._manifest_data = manifest_data or {}

    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id=self._manifest_data.get("id", "dummy"),
            name=self._manifest_data.get("name", "Dummy Item"),
            category="dummy",
        )

class TestUniversalScanner(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_zero_trust_validator_blocks_eval(self):
        code = "def bad(): eval('1+1')"
        valid, violations = ZeroTrustValidator.validate_source(code)
        self.assertFalse(valid)
        self.assertTrue(any("eval" in v for v in violations))

    def test_zero_trust_validator_allows_pure_code(self):
        code = "def good(x: int) -> int:\n    return x * 2"
        valid, violations = ZeroTrustValidator.validate_source(code)
        self.assertTrue(valid)
        self.assertEqual(len(violations), 0)

    def test_scanner_discovers_item_in_directory(self):
        item_dir = os.path.join(self.test_dir, "test_plugin")
        os.makedirs(item_dir)
        code_file = os.path.join(item_dir, "item.py")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(
                "from server.core.scanner.base import BaseDiscoverable, DiscoveryManifest\n"
                "class PluginItem(BaseDiscoverable):\n"
                "    @property\n"
                "    def manifest(self):\n"
                "        return DiscoveryManifest(id='plugin_1', name='Plugin One', category='test')\n"
            )

        scanner = UniversalScanner(
            root_dir=self.test_dir,
            target_filename="item.py",
            expected_type=BaseDiscoverable,
            category="test",
        )
        items = scanner.scan_all()
        self.assertEqual(len(items), 1)
        self.assertIn("test_plugin", items)
        self.assertEqual(items["test_plugin"].manifest.name, "Plugin One")
        self.assertEqual(scanner.get("test_plugin").id, "plugin_1")

    def test_common_scanner_reexport(self):
        from server.core.common.scanner import UniversalScanner as CommonScanner
        self.assertIs(CommonScanner, UniversalScanner)

if __name__ == "__main__":
    unittest.main()
