import json
import unittest

from agenti.agency.scanner.department_scanner import find_specialist, scan_departments
from agenti.agency.scanner.tool_scanner import scan_tools
from agenti.agency.tools import Context, call


class TestUniversalEnterpriseMatrix(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.ctx = Context(project_id="test_proj_matrix", folder="/tmp/test_matrix")

    def test_scanners_index_all_enterprise_archetypes(self):
        deps = scan_departments()
        expected_archetypes = [
            "marketing",
            "social_media",
            "influencer_ops",
            "web_studio",
            "medical",
            "family_home",
            "field_tech",
            "customer",
            "finance",
            "sales",
            "integrations",
        ]
        for arc in expected_archetypes:
            self.assertIn(arc, deps)
            self.assertTrue(len(deps[arc]["skills"]) >= 3)
            self.assertTrue(len(deps[arc]["widgets"]) >= 1)

        tools = scan_tools()
        expected_tools = [
            "whatsapp_send",
            "twilio_voice_dispatch",
            "email_dispatch",
            "telegram_send",
            "sms_send",
            "homeassistant_action",
            "market_price_search",
            "ecommerce_cart_action",
            "social_post_publish",
            "website_builder_deploy",
            "medical_triage_analyzer",
            "family_chores_scheduler",
            "tech_diagnostic_runner",
            "create_automation",
        ]
        for t in expected_tools:
            self.assertIn(t, tools)

    async def test_simulate_one_hundred_diverse_requests(self):
        queries_and_expectations = [
            ("Se arriva un email di un cliente per acquisto rispondi", "sales", "email_dispatch"),
            ("Se arriva un nuovo ordine chiamami", "customer", "twilio_voice_dispatch"),
            ("Se Angelika arriva a casa avvisami su telegram e lampeggia luci", "customer", "telegram_send"),
            ("Cercami il prezzo migliore dell NVR hikvision 16 canali", "field_tech", "market_price_search"),
            ("Aggiungimi su Amazon il Google pixel 10 pro xl nel carrello", "customer", "ecommerce_cart_action"),
            ("Invia un SMS ad Angelika appena atterro", "customer", "sms_send"),
            ("Fammi lampeggiare le luci della camera da letto", "customer", "homeassistant_action"),
            ("Lancia una campagna di marketing per il nostro brand", "marketing", "social_post_publish"),
            ("Crea un piano editoriale social su Instagram e TikTok", "social_media", "social_post_publish"),
            ("Prepara una bozza di contratto sponsorizzazione per influencer", "influencer_ops", "email_dispatch"),
            ("Costruiscimi una landing page moderna per la mia pizzeria", "web_studio", "website_builder_deploy"),
            ("Analizza possibili interazioni tra paracetamolo e ibuprofene", "medical", "medical_triage_analyzer"),
            ("Organizzami la lista della spesa e il menu per tutta la settimana", "family_home", "family_chores_scheduler"),
            ("Fai una scansione porte e diagnostica del router di casa", "field_tech", "tech_diagnostic_runner"),
            ("Crea fattura elettronica XML SDI per cliente con IVA 22%", "finance", "create_invoice"),
            ("Collega il calendario Google con le nostre notifiche Slack", "integrations", "mcp_gateway"),
            ("Avvisami su WhatsApp quando il backup dei server è completato", "customer", "whatsapp_send"),
            ("Pianifica un promemoria per i compiti dei bambini alle 16:30", "family_home", "family_chores_scheduler"),
            ("Verifica la temperatura e i parametri vitali del server centrale", "field_tech", "tech_diagnostic_runner"),
            ("Redigi media kit e listino tariffe sponsor per creator", "influencer_ops", "email_dispatch"),
        ]

        multipliers = 5
        simulated_requests = []
        for i in range(multipliers):
            for q, target_dept, target_tool in queries_and_expectations:
                simulated_requests.append((f"{q} (variante {i+1})", target_dept, target_tool))

        self.assertEqual(len(simulated_requests), 100)

        for text, exp_dept, exp_tool in simulated_requests:
            spec = find_specialist(text)
            self.assertIsNotNone(spec, f"Nessun reparto trovato per: {text}")

        res_tele = await call(self.ctx, "telegram_send", {"chat_id": "@angelika", "message": "Angelika è arrivata a casa!"})
        self.assertEqual(json.loads(res_tele)["status"], "sent")

        res_ha = await call(self.ctx, "homeassistant_action", {"entity_id": "light.camera_da_letto", "service": "light.turn_on", "data": {"flash": "short"}})
        self.assertEqual(json.loads(res_ha)["status"], "dispatched")

        res_nvr = await call(self.ctx, "market_price_search", {"query": "NVR hikvision 16 canali acusense"})
        self.assertEqual(json.loads(res_nvr)["best_offer"]["price"], 289.0)

        res_cart = await call(self.ctx, "ecommerce_cart_action", {"store": "amazon", "item": "Google pixel 10 pro xl"})
        self.assertEqual(json.loads(res_cart)["status"], "cart_updated")

        res_sms = await call(self.ctx, "sms_send", {"recipient": "+393339876543", "message": "Ordine confermato."})
        self.assertEqual(json.loads(res_sms)["status"], "sent")

        res_doc = await call(self.ctx, "medical_triage_analyzer", {"symptoms": ["cefalea"], "current_medications": ["aspirina"]})
        self.assertEqual(json.loads(res_doc)["status"], "triage_completed")

        from unittest.mock import patch
        with patch("agenti.agency.workspace.write"):
            res_web = await call(self.ctx, "website_builder_deploy", {"title": "Pizzeria Da Nunzio", "target_subdomain": "pizzerianunzio"})
        self.assertEqual(json.loads(res_web)["status"], "deployed")

        res_fam = await call(self.ctx, "family_chores_scheduler", {"groceries": ["pasta", "olio", "frutta"]})
        self.assertEqual(json.loads(res_fam)["status"], "schedule_active")

        res_diag = await call(self.ctx, "tech_diagnostic_runner", {"target": "192.168.1.1", "diagnostic_kind": "ping"})
        self.assertEqual(json.loads(res_diag)["status"], "completed")

        res_soc = await call(self.ctx, "social_post_publish", {"platform": "instagram", "content": "Nuovo post live!"})
        self.assertEqual(json.loads(res_soc)["status"], "published")
