import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for p in (str(_ROOT / "installer_wizard"), str(_ROOT / "installer_wizard" / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from identity import DEFAULT_NAME, assistant_identity, normalize_name


class AssistantIdentityTests(unittest.TestCase):
    def test_custom_name_is_kept_as_typed(self):
        ident = assistant_identity(lambda key, default: {"NUXIVA_ASSISTANT_NAME": "Amelia"}.get(key, default))
        self.assertEqual(ident.name, "Amelia")
        self.assertEqual(ident.wake_word, "amelia")
        self.assertTrue(ident.is_custom)
        self.assertIn("ehi amelia", ident.wake_phrases)

    def test_wake_prefix_and_shouting_are_normalized(self):
        self.assertEqual(normalize_name("Hey NUXIVA"), "Nuxiva")
        self.assertEqual(normalize_name("ehi Amelia"), "Amelia")

    def test_markup_is_stripped(self):
        self.assertEqual(normalize_name("<script>Amelia</script>"), "scriptAmeliascript")
        self.assertNotIn("<", normalize_name("A<b>"))

    def test_empty_falls_back_to_default(self):
        self.assertEqual(normalize_name("   "), DEFAULT_NAME)
        self.assertEqual(normalize_name("hey "), "hey")


if __name__ == "__main__":
    unittest.main()
