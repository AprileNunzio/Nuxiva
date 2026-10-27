import ast
import json
import re

MAX_ALLOWED_LINES = 500


class SandboxPreValidator:
    DANGEROUS_PATTERNS = [
        re.compile(r"\b(os\.system|subprocess\.Popen|subprocess\.call|shutil\.rmtree)\b"),
        re.compile(r"\b(__import__|exec|eval)\b"),
        re.compile(r"(\.\./\.\./|/etc/passwd|/etc/shadow)"),
    ]

    @classmethod
    def validate_code(cls, file_path: str, content: str) -> tuple[bool, str]:
        ext = file_path.split(".")[-1].lower() if "." in file_path else ""

        line_count = len(content.splitlines()) if content else 0
        if line_count > MAX_ALLOWED_LINES:
            return (
                False,
                f"Limite strutturale violato: {file_path} contiene {line_count} righe (massimo consentito: {MAX_ALLOWED_LINES}). Modularizza il file.",
            )

        for pat in cls.DANGEROUS_PATTERNS:
            if pat.search(content):
                return False, f"Rilevato pattern potenzialmente distruttivo o vulnerabile: {pat.pattern}"

        if ext == "py":
            try:
                ast.parse(content)
            except SyntaxError as exc:
                return False, f"Errore sintassi Python alla riga {exc.lineno}: {exc.msg}"
        elif ext == "json":
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                return False, f"JSON non valido alla riga {exc.lineno}: {exc.msg}"

        return True, ""


sandbox_validator = SandboxPreValidator()
