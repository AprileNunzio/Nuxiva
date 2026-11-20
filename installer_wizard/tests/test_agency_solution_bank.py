import asyncio
import json
import tempfile
import unittest

from agenti.agency.solution_bank import InternalSolutionBank
from agenti.agency.tools import Context
from agenti.agency.tools_catalog.solution_bank_tools import TOOLS as BANK_TOOLS
from agenti.agency.universal_resolver import universal_resolver


class TestAgencySolutionBank(unittest.TestCase):
    def test_solution_bank_registration_and_lookup(self):
        with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
            bank = InternalSolutionBank(storage_path=tmp.name)
            entry = bank.register_solution(
                domain="laser_cnc_vector",
                title="Taglio Supporto Ingranaggio Acrilico",
                keywords=["supporto", "ingranaggio", "acrilico", "laser", "dxf"],
                summary="Pattern vettoriale per taglio laser di ingranaggi con dima di centraggio",
                template_payload={"kerf": 0.12, "laser_speed": 600},
            )
            self.assertEqual(entry.domain, "laser_cnc_vector")

            match = bank.find_best_solution("Vorrei tagliare un supporto per ingranaggio in acrilico col laser")
            self.assertIsNotNone(match)
            best_entry, score = match
            self.assertEqual(best_entry.solution_id, entry.solution_id)
            self.assertGreater(score, 0.4)

    def test_solution_bank_zero_token_savings_and_refinement(self):
        with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
            bank = InternalSolutionBank(storage_path=tmp.name)
            entry = bank.register_solution(
                domain="object_3d_cad",
                title="Staffa Angolare Rinforzata",
                keywords=["staffa", "angolare", "3d", "stl", "rinforzo"],
                summary="Staffa a L con nervatura diagonale per stampa 3D",
                template_payload={"angle": 90, "thickness": 4},
            )
            initial_tokens = entry.tokens_saved_estimate
            entry.record_usage(success=True)
            self.assertGreater(entry.tokens_saved_estimate, initial_tokens)
            self.assertEqual(entry.usage_count, 2)

            refined = bank.refine_solution(entry.solution_id, {"thickness": 5}, improvement_note="Aumentato spessore per carichi gravosi")
            self.assertIsNotNone(refined)
            self.assertEqual(refined.optimization_generation, 2)
            self.assertGreater(refined.quality_score, 1.0)

    def test_universal_resolver_cache_integration(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            query = "Costruisci una scatola cover per telecomando con stampa 3d"
            plan1 = universal_resolver.resolve_any_request(query=query, workspace_dir=tmp_dir)
            self.assertEqual(plan1.domain, "object_3d_cad")

            plan2 = universal_resolver.resolve_any_request(query=query, workspace_dir=tmp_dir)
            self.assertTrue(plan2.cache_hit)
            self.assertGreater(plan2.tokens_saved, 0)
            self.assertIn("LEVEL_0_INTERNAL_SOLUTION_BANK_ZERO_TOKEN", plan2.prerequisites[0].resolution_level)

    def test_solution_bank_tools_execution(self):
        ctx = Context(project_id="proj_bank_test", folder="/tmp/test_bank_folder")
        stats_out = asyncio.run(BANK_TOOLS["solution_bank_stats"].run(ctx, {}))
        stats_data = json.loads(stats_out)
        self.assertIn("total_solutions_indexed", stats_data)
        self.assertIn("total_tokens_saved", stats_data)

        query_out = asyncio.run(BANK_TOOLS["solution_bank_query"].run(ctx, {
            "query": "scatola cover protettiva per 3d",
            "domain": "object_3d_cad",
        }))
        query_data = json.loads(query_out)
        self.assertIn(query_data["status"], ("matched", "no_match"))
