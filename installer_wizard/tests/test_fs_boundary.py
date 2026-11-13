import datetime
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "fs_boundary.py"
spec = importlib.util.spec_from_file_location("fs_boundary", SCRIPT)
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)


class BoundaryTest(unittest.TestCase):
    def test_direct_file_access_is_counted(self):
        source = "import shutil\nfrom pathlib import Path\nimport os\nopen('x')\nPath('a').read_text()\nos.remove('b')\nshutil.copy('a', 'b')\n"
        self.assertEqual(boundary.violations(source), 4)

    def test_clean_modules_have_no_violations(self):
        self.assertEqual(boundary.violations("import json\nvalue = json.dumps({})\nprint(value.replace('a', 'b'))\n"), 0)

    def test_scope_is_tools_and_algorithms_but_not_tests(self):
        base = "installer_wizard/agenti/"
        self.assertTrue(boundary.in_scope(Path(base + "cognizione/agent/tools_files.py")))
        self.assertTrue(boundary.in_scope(Path(base + "creativita/forma/algorithms/mesh.py")))
        self.assertFalse(boundary.in_scope(Path(base + "cognizione/agent/registry.py")))
        self.assertFalse(boundary.in_scope(Path("installer_wizard/tests/test_tools_files.py")))

    def test_repository_is_clean_today_and_exceptions_expire(self):
        self.assertEqual(boundary.main(datetime.date.today()), 0)
        self.assertEqual(boundary.main(datetime.date(2099, 1, 1)), 1)


if __name__ == "__main__":
    unittest.main()
