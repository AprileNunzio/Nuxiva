import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from agenti.agency.scanner.department_scanner import find_specialist, scan_departments
from agenti.agency.tools import Context
from agenti.agency.tools_catalog.universal_director import TOOLS as DIRECTOR_TOOLS
from agenti.agency.universal_resolver import universal_resolver


class TestAgencyUniversalAutonomousResolver(unittest.TestCase):
    def test_intent_classification(self):
        self.assertEqual(
            universal_resolver.classify_intent("Voglio stampare un oggetto 3D con filamento PLA e tolleranze strette"),
            "object_3d_cad"
        )
        self.assertEqual(
            universal_resolver.classify_intent("Prepara una stampa laser su compensato con taglio e incisione vettoriale SVG"),
            "laser_cnc_vector"
        )
        self.assertEqual(
            universal_resolver.classify_intent("Sviluppa una landing page moderna con frontend reattivo TSX e API backend"),
            "software_web"
        )
        self.assertEqual(
            universal_resolver.classify_intent("Monta un video reel per i social con musica di sottofondo e sottotitoli"),
            "audio_video_multimedia"
        )
        self.assertEqual(
            universal_resolver.classify_intent("Programma un firmware per scheda ESP32 con gestione sensore di temperatura"),
            "iot_hardware"
        )

    def test_3d_cad_resolution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            plan = universal_resolver.resolve_any_request(
                query="Crea un supporto per telecamera con filettatura 3D per stampa",
                workspace_dir=tmp_dir,
            )
            self.assertEqual(plan.domain, "object_3d_cad")
            self.assertEqual(plan.lead_specialist, "cad_3d_specialist")
            self.assertEqual(plan.pair_specialist, "architect")
            self.assertTrue(plan.zero_block_guarantee)
            self.assertEqual(plan.execution_status, "completed_100_percent")

            cad_art = next(a for a in plan.generated_artifacts if a["kind"] == "cad_model")
            self.assertIn(cad_art["resolution_level"], ("LEVEL_4_GENERATIVE_AI_PARAMETRIC", "LEVEL_0_INTERNAL_SOLUTION_BANK_ZERO_TOKEN"))
            self.assertTrue(Path(cad_art["details"]["scad_file"]).exists())
            self.assertTrue(Path(cad_art["details"]["stl_file"]).exists())

            scad_content = Path(cad_art["details"]["scad_file"]).read_text(encoding="utf-8")
            self.assertIn("cube", scad_content)

    def test_laser_cutting_resolution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            plan = universal_resolver.resolve_any_request(
                query="Prepara file di taglio laser per insegna in legno con logo inciso",
                workspace_dir=tmp_dir,
            )
            self.assertEqual(plan.domain, "laser_cnc_vector")
            self.assertEqual(plan.lead_specialist, "laser_cnc_specialist")
            self.assertEqual(plan.pair_specialist, "field_tech")

            vec_art = next(a for a in plan.generated_artifacts if a["kind"] == "vector_blueprint")
            self.assertIn(vec_art["resolution_level"], ("LEVEL_4_GENERATIVE_AI_PARAMETRIC", "LEVEL_0_INTERNAL_SOLUTION_BANK_ZERO_TOKEN"))
            self.assertTrue(Path(vec_art["details"]["svg_path"]).exists())
            self.assertTrue(Path(vec_art["details"]["dxf_path"]).exists())

            svg_content = Path(vec_art["details"]["svg_path"]).read_text(encoding="utf-8")
            self.assertIn("#FF0000", svg_content)
            self.assertIn("#0000FF", svg_content)

    def test_specialist_catalog_routing_and_departments(self):
        deps = scan_departments()
        self.assertIn("cad_3d_specialist", deps)
        self.assertIn("laser_cnc_specialist", deps)

        c_dep = deps["cad_3d_specialist"]
        self.assertEqual(c_dep["name"], "Valerio · CAD & 3D Manufacturing Engineer")
        self.assertIn("specialized", c_dep["category"])

        l_dep = deps["laser_cnc_specialist"]
        self.assertEqual(l_dep["name"], "Ettore · Laser Cutting & CNC Tooling Specialist")
        self.assertIn("specialized", l_dep["category"])

        found_cad = find_specialist("devo progettare un oggetto 3d e generare il file stl")
        self.assertIsNotNone(found_cad)
        self.assertEqual(found_cad["id"], "cad_3d_specialist")

        found_laser = find_specialist("taglio laser su misura con vettoriale e calcolo kerf")
        self.assertIsNotNone(found_laser)
        self.assertEqual(found_laser["id"], "laser_cnc_specialist")

    def test_universal_director_tool_execution(self):
        ctx = Context(project_id="proj_universal_test", folder="/tmp/test_universal_folder")
        with tempfile.TemporaryDirectory() as tmp_dir:
            out = asyncio.run(DIRECTOR_TOOLS["universal_autonomous_resolve"].run(ctx, {
                "request": "Crea una cover protettiva 3D per scheda elettronica",
                "workspace_dir": tmp_dir,
            }))
            data = json.loads(out)
            self.assertEqual(data["domain"], "object_3d_cad")
            self.assertEqual(data["execution_status"], "completed_100_percent")
            self.assertTrue(data["zero_block_guarantee"])
            self.assertGreater(len(data["generated_artifacts"]), 0)
