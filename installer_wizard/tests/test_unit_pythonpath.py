import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNITS = ROOT / "scripts" / "os" / "systemd"
INSTALL_ROOT = "/opt/Nuxiva"
PROJECT_DIRS = (ROOT / "installer_wizard" / "backend", ROOT / "installer_wizard", ROOT)


def local(path: str) -> Path | None:
    if path == INSTALL_ROOT or path.startswith(INSTALL_ROOT + "/"):
        return ROOT / path[len(INSTALL_ROOT):].lstrip("/")
    return None


def unit_value(text: str, key: str) -> list[str]:
    return re.findall(rf"^{key}=(.*)$", text, re.MULTILINE)


def python_script(text: str) -> Path | None:
    for line in unit_value(text, "ExecStart"):
        match = re.search(r"(/opt/Nuxiva/\S+\.py)\b", line)
        if match and "python" in line.split()[0]:
            return local(match.group(1))
    return None


def search_path(text: str, script: Path) -> list[Path]:
    dirs = [script.parent]
    for line in unit_value(text, "Environment"):
        if line.startswith("PYTHONPATH="):
            for entry in line.split("=", 1)[1].split(":"):
                resolved = local(entry.strip())
                if resolved is not None:
                    dirs.append(resolved)
    return dirs


def imports_of(file: Path) -> set[str]:
    names: set[str] = set()
    tree = ast.parse(file.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def unresolved(script: Path, path: list[Path]) -> list[str]:
    seen: set[Path] = set()
    queue = [script]
    missing: set[str] = set()
    while queue:
        current = queue.pop()
        if current in seen:
            continue
        seen.add(current)
        for name in imports_of(current):
            owner = next((d for d in path if provides(d, name)), None)
            if owner is None:
                hint = next((d for d in PROJECT_DIRS if provides(d, name)), None)
                if hint is not None:
                    missing.add(f"{name} (in {hint.relative_to(ROOT)})")
            elif (owner / f"{name}.py").is_file():
                queue.append(owner / f"{name}.py")
    return sorted(missing)


def provides(directory: Path, name: str) -> bool:
    return (directory / f"{name}.py").is_file() or (directory / name).is_dir()


class UnitPythonPathTest(unittest.TestCase):
    def test_every_python_unit_resolves_its_project_imports(self):
        checked = 0
        for unit in sorted(UNITS.glob("*.service")):
            text = unit.read_text(encoding="utf-8")
            script = python_script(text)
            if script is None:
                continue
            checked += 1
            path = search_path(text, script)
            missing = unresolved(script, path)
            with self.subTest(unit=unit.name):
                self.assertEqual(missing, [])
        self.assertGreater(checked, 0)

    def test_vision_unit_exposes_native_core(self):
        text = (UNITS / "nuxiva-vision.service").read_text(encoding="utf-8")
        script = python_script(text)
        self.assertIsNotNone(script)
        path = search_path(text, script)
        self.assertTrue(any(provides(d, "native_core") for d in path))
        self.assertTrue(any(provides(d, "backend") for d in path))


if __name__ == "__main__":
    unittest.main()
