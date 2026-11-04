import unittest
from server.core.games_scanner.scanner import games_scanner
from server.core.games_scanner.contracts import CommandInputType, CapabilityCategory

class TestGamesScanner(unittest.TestCase):
    def test_games_scanner_discovers_scacchi(self):
        games = games_scanner.scan_all(force=True)
        self.assertIn("scacchi-3d", games)
        game = games_scanner.get_game("scacchi-3d")
        self.assertIsNotNone(game)
        self.assertEqual(game.game_id, "scacchi-3d")
        self.assertEqual(game.name, "Wizard Chess 3D")
        self.assertGreaterEqual(len(game.commands), 8)
        self.assertGreaterEqual(len(game.capabilities), 6)

    def test_games_scanner_command_introspection(self):
        commands = games_scanner.get_commands("scacchi-3d")
        cmd_ids = [c.command_id for c in commands]
        self.assertIn("voice_move", cmd_ids)
        self.assertIn("pause", cmd_ids)
        self.assertIn("resume", cmd_ids)
        self.assertIn("get_hint", cmd_ids)

        voice_cmd = next(c for c in commands if c.command_id == "voice_move")
        self.assertIn(CommandInputType.VOICE, voice_cmd.input_types)
        self.assertIn("cavallo", voice_cmd.voice_triggers)

    def test_games_scanner_capabilities(self):
        caps = games_scanner.get_capabilities("scacchi-3d")
        cap_ids = [c.capability_id for c in caps]
        self.assertIn("3d_rendering", cap_ids)
        self.assertIn("voice_recognition", cap_ids)
        self.assertIn("session_vault", cap_ids)

        render_cap = next(c for c in caps if c.capability_id == "3d_rendering")
        self.assertEqual(render_cap.category, CapabilityCategory.RENDERING)

if __name__ == "__main__":
    unittest.main()
