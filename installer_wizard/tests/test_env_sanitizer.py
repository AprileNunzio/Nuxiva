import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from config import _format_env_line, sanitize_env_file, read_global_env, write_env
from env_format import decode_value, entries, format_line, normalize

class EnvSanitizerTest(unittest.TestCase):
    def test_normalization_is_idempotent_and_preserves_escaped_values(self):
        values = {"PATH_VALUE": r"C:\models\new", "QUOTES": 'modello "italiano"', "LITERAL": '$HOME `touch nope`',
                  "DOLLARS": r"literal\$HOME ${VALUE} $$", "APOSTROPHE": "it's $HOME",
                  "UNICODE": "città", "EMPTY": ""}
        text = "\n".join(format_line(key, value) for key, value in values.items()) + "\n"
        for _ in range(5):
            text = normalize(text)
            self.assertEqual(dict(entries(text)), values)
            self.assertEqual(normalize(text), text)

    def test_supervisor_repeated_writes_do_not_reescape_existing_values(self):
        values = {"MODEL_PATH": r"C:\models\new", "MODEL_NAME": 'modello "italiano"'}
        with tempfile.TemporaryDirectory() as tmpdir, patch("config.ENV_FILE", Path(tmpdir) / "nuxiva.env"):
            write_env(values)
            for _ in range(5):
                sanitize_env_file()
                write_env({"OTHER": "value"})
                self.assertEqual({key: read_global_env()[key] for key in values}, values)

    def test_plain_and_malformed_quoted_values_are_repaired(self):
        self.assertEqual(decode_value('"""hello"""'), "hello")
        self.assertEqual(decode_value("'value'"), "value")
        self.assertEqual(decode_value(r'"C:\models"'), r"C:\models")

    def test_format_env_line_strips_nested_quotes(self) -> None:
        raw_key = "ANTHROPIC_API_KEY"
        raw_val = '"""""""sk-ant-usr-1234567890"""""""'
        formatted = _format_env_line(raw_key, raw_val)
        self.assertEqual(formatted, 'ANTHROPIC_API_KEY="sk-ant-usr-1234567890"')

    def test_sanitize_env_file_removes_invalid_and_duplicate_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "nuxiva.env"
            corrupted_content = (
                '"""""""sk-ant-usr-badline"""""""\n'
                'ANTHROPIC_API_KEY="""sk-ant-usr-valid"""\n'
                '# comment line\n'
                'NUXIVA_VOICESTUDIO="""1"""\n'
                'INVALID-KEY=test\n'
            )
            env_path.write_text(corrupted_content, encoding="utf-8")

            with patch("config.ENV_FILE", env_path):
                sanitize_env_file()
                cleaned = env_path.read_text(encoding="utf-8")
                self.assertNotIn('"""""""sk-ant-usr-badline"""""""', cleaned)
                self.assertNotIn("INVALID-KEY", cleaned)
                self.assertIn('ANTHROPIC_API_KEY="sk-ant-usr-valid"', cleaned)
                self.assertIn('NUXIVA_VOICESTUDIO="1"', cleaned)

                read_back = read_global_env()
                self.assertEqual(read_back.get("ANTHROPIC_API_KEY"), "sk-ant-usr-valid")
                self.assertEqual(read_back.get("NUXIVA_VOICESTUDIO"), "1")

if __name__ == "__main__":
    unittest.main()
