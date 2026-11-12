import json
import os
import stat
from pathlib import Path

from . import _icon, _manifest

LANGUAGES = ("it", "en", "fr", "es")
PACKAGES = ("tools", "skills", "algorithms")
WIDGET_DIR = "widget"
FILES = ("feature.json", "agent.py", "icon.png")


class ScaffoldError(ValueError):
    def __init__(self, issues: list[dict]) -> None:
        super().__init__(json.dumps(issues, ensure_ascii=False))
        self.issues = issues


def _is(path: Path, kind) -> bool:
    try:
        return kind(os.lstat(path).st_mode)
    except OSError:
        return False


def _package(directory: Path, name: str) -> bool:
    return _is(directory / f"{name}.py", stat.S_ISREG) or _is(directory / name / "__init__.py", stat.S_ISREG)


def categories() -> tuple[str, ...]:
    return tuple(_manifest.CATEGORIES) + tuple(_manifest.LEGACY_CATEGORIES)


def required_parts() -> list[str]:
    return [*FILES, *(f"{p}/" for p in PACKAGES), *(f"language/{lang}.json" for lang in LANGUAGES)]


def inspect(directory: Path) -> dict:
    directory = Path(directory)
    missing = [f for f in FILES if not _is(directory / f, stat.S_ISREG)]
    missing += [f"{p}/" for p in PACKAGES if not _package(directory, p)]
    missing += [f"language/{lang}.json" for lang in LANGUAGES
                if not _is(directory / "language" / f"{lang}.json", stat.S_ISREG)]
    optional = [] if _is(directory / WIDGET_DIR, stat.S_ISDIR) else [f"{WIDGET_DIR}/"]
    total = len(required_parts())
    score = min((total - len(missing)) * 100 // total, 100)
    return {"missing": missing, "optional_missing": optional, "complete": not missing, "score": score}


def _pretty(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _literal(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


def _manifest_value(spec: dict) -> dict:
    return {
        "id": spec["id"], "name": spec["name"], "icon": spec.get("icon") or "◆", "category": spec["category"],
        "version": "1.0.0", "description": spec["description"], "capabilities": list(spec.get("capabilities", [])),
        "routing": {"nouns": list(spec.get("nouns", [])), "phrases": list(spec.get("phrases", [])), "verbs": []},
        "profile": {"ram_mb": 64, "vram_mb": 0, "heavy": False}, "tools": [f"{spec['id']}_describe"],
        "skills": [], "widgets": [], "icon3d": "./icon.png",
    }


def _agent_py(spec: dict) -> str:
    return (
        "from agenti._registry import registry\n\n"
        f"AGENT_ID = {_literal(spec['id'])}\n\n\n"
        "class Agent:\n    agent_id = AGENT_ID\n\n"
        "    def __init__(self) -> None:\n        self.running = False\n\n"
        "    @property\n    def manifest(self) -> dict:\n"
        "        found = registry.get(AGENT_ID)\n        return dict(found.manifest) if found else {}\n\n"
        "    def start(self) -> None:\n        self.running = True\n\n"
        "    def stop(self) -> None:\n        self.running = False\n\n"
        "    def describe(self) -> dict:\n        m = self.manifest\n"
        '        return {"id": AGENT_ID, "name": m.get("name", AGENT_ID), "capabilities": list(m.get("capabilities", []))}\n\n\n'
        "agent = Agent()\n"
    )


def _tools_py(spec: dict) -> str:
    ident = spec["id"]
    return (
        f"from agenti.agent.registry import tool\nfrom agenti.{ident}.agent import agent\n\n\n"
        f"@tool({_literal(ident + '_describe')}, {_literal(spec['description'])}, {{}}, agent={_literal(ident)})\n"
        f"async def {ident}_describe() -> dict:\n    return agent.describe()\n"
    )


def _language(spec: dict, lang: str) -> str:
    return _pretty({
        "meta": {"locale": lang}, "name": spec["name"], "description": spec["description"],
        "capabilities": list(spec.get("capabilities", [])), "scope": f"features/{spec['id']}",
        "dictionary": {"name": spec["name"], "description": spec["description"]},
    })


def _error(field: str, code: str) -> dict:
    return {"field": field, "code": code, "severity": "error"}


def scaffold(spec: dict) -> list[tuple[str, bytes]]:
    spec = {"capabilities": [], "nouns": [], "phrases": [], "icon": "", **spec}
    issues: list[dict] = []
    if spec["category"] not in _manifest.CATEGORIES:
        issues.append(_error("category", "category_unknown"))
    value = _manifest_value(spec)
    report = _manifest.validate_value(value, spec["id"], spec["category"])
    issues += [i for i in report["issues"] if i["severity"] == "error"]
    if not spec["description"].strip():
        issues.append(_error("description", "description_missing"))
    if issues:
        raise ScaffoldError(issues)
    ident = spec["id"]
    files = [
        ("feature.json", _pretty(value)),
        ("agent.py", _agent_py(spec)),
        ("__init__.py", ""),
        ("tools/__init__.py", f'from agenti.{ident}.tools import {ident}_tools\n\n__all__ = ["{ident}_tools"]\n'),
        (f"tools/{ident}_tools.py", _tools_py(spec)),
        ("skills/__init__.py", "SKILLS: tuple = ()\n"),
        ("algorithms/__init__.py", "ALGORITHMS: tuple = ()\n"),
        *((f"language/{lang}.json", _language(spec, lang)) for lang in LANGUAGES),
    ]
    out = [(path, body.encode("utf-8")) for path, body in files]
    out.append(("icon.png", _icon.render(spec["category"], ident)))
    return out
