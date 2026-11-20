import unittest
from server.web.html_compositor import (
    compose_html,
    build_index_html,
    WEB_DIR,
    LAYOUT_FILE,
    TARGET_INDEX
)

class TestHTMLCompositor(unittest.TestCase):

    def test_master_layout_exists(self):
        """Verifica che il master layout esista e contenga le direttive di inclusione."""
        self.assertTrue(LAYOUT_FILE.exists(), f"File non trovato: {LAYOUT_FILE}")
        content = LAYOUT_FILE.read_text(encoding="utf-8")
        self.assertIn("<!-- @include features/war_room/deck.html -->", content)
        self.assertIn("<!-- @include features/chatbot_mesh/deck.html -->", content)
        self.assertIn("<!-- @include features/onboarding/wizard_modal.html -->", content)

    def test_component_files_exist_and_modular(self):
        """Verifica che tutti i componenti parziali siano stati estratti e abbiano dimensione contenuta."""
        expected_components = [
            "features/war_room/deck.html",
            "features/cognitive_flow/deck.html",
            "features/agent_vault/deck.html",
            "features/rbac/deck.html",
            "features/proximity_hud/deck.html",
            "features/cad_media/deck.html",
            "features/telemetry/deck.html",
            "features/chatbot_mesh/deck.html",
            "features/multimodal_surveillance/deck.html",
            "features/human_affective_engine/deck.html",
            "features/wearable_vitals_hub/deck.html",
            "features/user_presence_vitals/deck.html",
            "features/cognitive_triage_agents/deck.html",
            "features/onboarding/wizard_modal.html",
            "features/chatbot_mesh/emoticon_overlay.html",
        ]
        for comp in expected_components:
            path = WEB_DIR / comp
            self.assertTrue(path.exists(), f"Componente parziale mancante: {comp}")
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertTrue(len(lines) > 0, f"Componente vuoto: {comp}")
            # Ogni componente modulare è compatto (sotto 200 righe)
            self.assertLess(len(lines), 200, f"Componente troppo grande ({len(lines)} righe): {comp}")

    def test_compose_html_integration(self):
        """Verifica che la composizione produca un HTML completo con tutti gli ID necessari."""
        html = compose_html(use_cache=False)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn('id="deck-projects"', html)
        self.assertIn('id="deck-chatbot-mesh"', html)
        self.assertIn('id="deck-cognitive-triage"', html)
        self.assertIn('id="admin-wizard-overlay"', html)
        self.assertIn('id="emoticon-floating-stage"', html)
        self.assertIn('/static/app.js', html)
        # Non devono rimanere direttive non risolte
        self.assertNotIn("<!-- Componente non trovato", html)

    def test_build_index_html(self):
        """Verifica che la compilazione su disco funzioni correttamente."""
        out = build_index_html()
        self.assertTrue(TARGET_INDEX.exists())
        self.assertEqual(TARGET_INDEX.read_text(encoding="utf-8"), out)


if __name__ == "__main__":
    unittest.main()
