import unittest
import asyncio
from server.features.voice_engine.vocal_profiles.registry import vocal_profile_registry
from server.features.voice_engine.reactions.reaction_service import emoticon_reaction_service
from server.features.chatbot_mesh.chatbot_models import ChatMessagePayload, UserAgentPersonalization
from server.features.chatbot_mesh.conversational_engine import conversational_bot_engine
from server.features.chatbot_mesh.user_agent_customization_service import user_agent_customization_service


class TestVocalProfilesAndReactions(unittest.TestCase):

    def test_vocal_profiles_auto_discovery(self):
        """Verifica che tutti i profili vocali indipendenti vengano registrati automaticamente."""
        profiles = vocal_profile_registry.list_profiles()
        engine_ids = [p["engine_id"] for p in profiles]
        
        self.assertIn("elevenlabs", engine_ids)
        self.assertIn("piper", engine_ids)
        self.assertIn("kokoro", engine_ids)
        self.assertIn("azure", engine_ids)
        self.assertIn("openai", engine_ids)
        self.assertIn("bark", engine_ids)

    def test_elevenlabs_profile_behavior(self):
        """Verifica che ElevenLabs mantenga i tag vocali nativi e rimuova i comandi reaction."""
        profile = vocal_profile_registry.get_profile("elevenlabs")
        self.assertEqual(profile.engine_id, "elevenlabs")
        self.assertIn("laughs", profile.supported_tags)
        self.assertIn("sighs", profile.supported_tags)

        # Prepara sintesi
        raw = "Grazie mille! [laughs] Che bella notizia! [reaction:hearts]"
        cleaned = profile.prepare_for_synthesis(raw)
        self.assertIn("[laughs]", cleaned)
        self.assertNotIn("reaction:hearts", cleaned)

        instructions = profile.get_system_prompt_instructions()
        self.assertIn("ELEVENLABS", instructions)
        self.assertIn("[laughs]", instructions)

    def test_piper_profile_behavior(self):
        """Verifica che Piper rimuova rigorosamente tutti i tag tra parentesi quadre."""
        profile = vocal_profile_registry.get_profile("piper")
        self.assertEqual(profile.engine_id, "piper")
        self.assertEqual(profile.supported_tags, [])

        raw = "Grazie mille! [laughs] Che bella notizia! [reaction:hearts]"
        cleaned = profile.prepare_for_synthesis(raw)
        self.assertEqual(cleaned, "Grazie mille! Che bella notizia!")
        self.assertNotIn("[", cleaned)
        self.assertNotIn("]", cleaned)

        instructions = profile.get_system_prompt_instructions()
        self.assertIn("PIPER", instructions)
        self.assertIn("NON inserire MAI", instructions)

    def test_azure_ssml_profile_behavior(self):
        """Verifica il profilo Azure SSML."""
        profile = vocal_profile_registry.get_profile("azure")
        self.assertEqual(profile.engine_id, "azure")
        raw = "<style:cheerful>Evviva!</style:cheerful> [reaction:celebration]"
        cleaned = profile.prepare_for_synthesis(raw)
        self.assertIn('<mstts:express-as style="cheerful">Evviva!</mstts:express-as>', cleaned)
        self.assertNotIn("reaction:celebration", cleaned)

    def test_reaction_service_extraction(self):
        """Verifica l'estrazione e formattazione delle reazioni grafiche ed emoticons."""
        text = "Sei fantastica! [reaction:hearts] Congratulazioni! [reaction:celebration]"
        reactions = emoticon_reaction_service.extract_reactions(text)
        self.assertEqual(len(reactions), 2)
        self.assertEqual(reactions[0]["reaction_id"], "hearts")
        self.assertIn("❤️", reactions[0]["emojis"])
        self.assertEqual(reactions[1]["reaction_id"], "celebration")
        self.assertIn("🎉", reactions[1]["emojis"])

        clean = emoticon_reaction_service.strip_reaction_tags(text)
        self.assertEqual(clean, "Sei fantastica! Congratulazioni!")

    def test_compliment_heuristics_with_elevenlabs(self):
        """Verifica che 'come sei bella Nuxiva' generi risposta con tag ElevenLabs e cuori."""
        match = emoticon_reaction_service.check_compliment_heuristics(
            "come sei bella Nuxiva",
            engine_id="elevenlabs",
            bot_name="Nuxiva"
        )
        self.assertIsNotNone(match)
        reply, reactions = match
        self.assertIn("[laughs]", reply)
        self.assertIn("[reaction:hearts]", reply)
        self.assertEqual(reactions[0]["reaction_id"], "hearts")

    def test_compliment_heuristics_with_piper(self):
        """Verifica che 'come sei bella Nuxiva' con Piper non inserisca tag [laughs] ma punteggiatura."""
        match = emoticon_reaction_service.check_compliment_heuristics(
            "come sei bella Nuxiva",
            engine_id="piper",
            bot_name="Nuxiva"
        )
        self.assertIsNotNone(match)
        reply, reactions = match
        self.assertNotIn("[laughs]", reply)
        self.assertIn("[reaction:hearts]", reply)
        self.assertIn("...", reply)

    def test_conversational_engine_end_to_end(self):
        """Test end-to-end con ConversationalBotEngine e payload chat."""
        user_id = "test_user_compliment"
        agent_id = "chief_supervisor"

        # Configura utente con ElevenLabs
        custom = UserAgentPersonalization(
            user_id=user_id,
            agent_id=agent_id,
            tts_engine="elevenlabs"
        )
        user_agent_customization_service.save_personalization(custom)

        # Prompt personalizzato deve includere ElevenLabs e Reazioni
        prompt = conversational_bot_engine.build_personalized_system_prompt(user_id, agent_id)
        self.assertIn("ELEVENLABS", prompt)
        self.assertIn("REAZIONI GRAFICHE", prompt)

        # Invia messaggio di complimento
        payload = ChatMessagePayload(
            user_id=user_id,
            agent_id=agent_id,
            text="come sei bella Nuxiva"
        )
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(conversational_bot_engine.handle_message(payload))
        finally:
            loop.close()

        self.assertIn("[reaction:hearts]", response.reply_text)
        self.assertIn("[laughs]", response.reply_text)
        self.assertTrue(len(response.reactions) > 0)
        self.assertEqual(response.reactions[0]["reaction_id"], "hearts")

        # Verifica che tra i widget attivi ci sia emoticon_reaction
        widget_types = [w.widget_type for w in response.active_widgets]
        self.assertIn("emoticon_reaction", widget_types)


if __name__ == "__main__":
    unittest.main()
