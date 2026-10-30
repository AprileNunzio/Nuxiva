import ast
import re
import sys
import unittest
from pathlib import Path


class CoreRuntimeRequirementsTest(unittest.TestCase):
    def test_encrypted_storage_external_imports_are_declared_for_runtime(self):
        root = Path(__file__).resolve().parents[2]
        source = root / 'server/core/memory/cache_storage.py'
        imports = set()
        for node in ast.walk(ast.parse(source.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split('.')[0])
        external = imports - sys.stdlib_module_names - {'server'}
        self.assertTrue(external, 'The encrypted storage has external runtime dependencies')
        for requirements in ('server/requirements.txt',):
            declared = {re.split(r'[<>=!~\[;\s]', line.strip())[0].lower().replace('_', '-')
                        for line in (root / requirements).read_text(encoding='utf-8').splitlines()
                        if line.strip() and not line.lstrip().startswith('#')}
            for package in external:
                self.assertIn(package.lower().replace('_', '-'), declared,
                              f'{source.name} imports {package}, missing from {requirements}')
