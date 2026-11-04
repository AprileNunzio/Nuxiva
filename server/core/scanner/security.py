import ast
from typing import List, Tuple

class SecurityViolationError(Exception):
    pass

class ZeroTrustValidator:
    BANNED_CALLS = {"eval", "exec", "__import__"}
    BANNED_MODULES = {"pty", "posix"}

    @classmethod
    def validate_source(cls, source_code: str, file_path: str = "") -> Tuple[bool, List[str]]:
        violations: List[str] = []
        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError as e:
            return False, [f"SyntaxError: {str(e)}"]

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.BANNED_CALLS:
                    violations.append(f"Forbidden call '{node.func.id}' at line {node.lineno}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in cls.BANNED_MODULES:
                        violations.append(f"Forbidden import '{alias.name}' at line {node.lineno}")
            elif isinstance(node, ast.ImportFrom):
                if node.module in cls.BANNED_MODULES:
                    violations.append(f"Forbidden import from '{node.module}' at line {node.lineno}")

        return len(violations) == 0, violations
