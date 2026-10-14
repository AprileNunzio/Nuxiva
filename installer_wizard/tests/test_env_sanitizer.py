import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from config import _format_env_line, sanitize_env_file, read_global_env

class EnvSanitizerTest(unittest.TestCase):
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
