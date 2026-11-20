import json
import tempfile
import unittest
from pathlib import Path

from agenti.agency.project_scaffolder import project_scaffolder
from agenti.agency.scanner import department_scanner, tool_scanner
from agenti.agency.scanner.recursive_scanner import recursive_scanner


class TestAgencyRecursiveCategoricalScaling(unittest.TestCase):
    def test_recursive_scanner_finds_nested_catalogs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            p1 = base / "engineering" / "web"
            p1.mkdir(parents=True, exist_ok=True)
            (p1 / "react_specialist.json").write_text(json.dumps({"id": "react_specialist"}), encoding="utf-8")

            p2 = base / "security" / "crypto"
            p2.mkdir(parents=True, exist_ok=True)
            (p2 / "vault_guard.json").write_text(json.dumps({"id": "vault_guard"}), encoding="utf-8")

            found = list(recursive_scanner.scan_json_files(base))
            self.assertEqual(len(found), 2)

            cats = {item[2] for item in found}
            self.assertIn("engineering.web", cats)
            self.assertIn("security.crypto", cats)

    def test_department_scanner_recursive_categories(self):
        deps = department_scanner.scan_departments()
        self.assertGreaterEqual(len(deps), 27)

        cats = department_scanner.list_categories()
        for expected in ("engineering", "security", "operations", "business", "creative", "lifestyle", "specialized"):
            self.assertIn(expected, cats)

        eng_deps = department_scanner.get_departments_by_category("engineering")
        eng_ids = [d["id"] for d in eng_deps]
        self.assertIn("rust_expert", eng_ids)
        self.assertIn("tsx_expert", eng_ids)
        self.assertIn("html5_expert", eng_ids)
        self.assertIn("php_expert", eng_ids)

        sec_deps = department_scanner.get_departments_by_category("security")
        sec_ids = [d["id"] for d in sec_deps]
        self.assertIn("security_crypto_expert", sec_ids)

    def test_forge_department_places_into_categorical_subfolder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            dep = department_scanner.forge_department(
                domain="quantum_cryptography",
                name="Quantum Crypto Specialist",
                category="security",
                target_dir=base,
            )
            file_path = Path(dep["path"])
            self.assertTrue(file_path.exists())
            self.assertEqual(file_path.parent.name, "security")
            self.assertEqual(dep["category"], "security")

            scanned = department_scanner.scan_departments([base])
            self.assertIn("quantum_cryptography", scanned)
            self.assertEqual(scanned["quantum_cryptography"]["category"], "security")

    def test_tool_scanner_recursive_discovery(self):
        tools = tool_scanner.scan_tools()
        self.assertIn("scaffold_modular_project", tools)
        self.assertIn("assign_pair_programming_desk", tools)
        self.assertIn("verify_project_architecture", tools)

    def test_enterprise_scale_safety_and_modularity_audit(self):
        catalog_dir = department_scanner.DEFAULT_CATALOG_DIR
        audit = recursive_scanner.audit_enterprise_scale_safety(catalog_dir)
        self.assertTrue(audit["safe"])
        self.assertGreater(audit["directories_count"], 5)
        self.assertLessEqual(audit["max_entries_in_single_dir"], 500)

        scaffold = project_scaffolder.scaffold_modular_architecture(
            project_name="banking_settlement_system",
            domain="fintech_core",
            capabilities=["transfer_funds", "settle_batch"],
        )
        mod_report = project_scaffolder.verify_categorical_modularity(scaffold)
        self.assertTrue(mod_report["modular"])
        self.assertTrue(mod_report["enterprise_scale_safe"])
        self.assertEqual(mod_report["max_items_per_partition_guarantee"], 500)


if __name__ == "__main__":
    unittest.main()
