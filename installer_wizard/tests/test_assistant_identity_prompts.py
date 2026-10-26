import unittest
from unittest import mock

import identity
from features.chat import speaker


def reader(name, gender):
    return lambda key, default: {"NUXIVA_ASSISTANT_NAME": name, "NUXIVA_ASSISTANT_GENDER": gender}.get(key, default)


class PromptTest(unittest.TestCase):
    def test_gender_line_follows_the_choice(self):
        male = identity.assistant_identity(reader("Astra", "male"))
        female = identity.assistant_identity(reader("Astra", "female"))
        self.assertIn("maschile", identity.gender_line(male))
        self.assertIn("femminile", identity.gender_line(female))
        self.assertEqual(identity.gender_line(identity.assistant_identity(reader("Astra", "neutral"))), "")

    def test_speaker_instruction_uses_the_configured_name_and_gender(self):
        who = identity.assistant_identity(reader("Orion", "male"))
        with mock.patch.object(speaker, "assistant_name", return_value="Orion"), \
                mock.patch.object(speaker, "self_line", return_value=identity.self_line(who)):
            text = speaker.instruction()
        self.assertIn("Orion", text)
        self.assertIn("maschile", text)
        self.assertIn("Non chiamarti mai Nuxiva", text)
