import glob
import json
import os
import re
from pathlib import Path

DEFAULT_CATALOG_DIR = Path(__file__).resolve().parents[1] / "departments_catalog"


def _clean_str(value: str, limit: int = 400) -> str:
    return str(value or "").strip()[:limit]


def scan_departments(extra_dirs: list[Path] | None = None) -> dict[str, dict]:
    dirs = [DEFAULT_CATALOG_DIR]
    if extra_dirs:
        dirs.extend(extra_dirs)
    departments: dict[str, dict] = {}
    for d in dirs:
        if not d.exists() or not d.is_dir():
            continue
        pattern = str(d / "*.json")
        for filepath in sorted(glob.glob(pattern)):
            try:
                content = Path(filepath).read_text(encoding="utf-8")
                data = json.loads(content)
                if not isinstance(data, dict):
                    continue
                dep_id = _clean_str(data.get("id"), 40).lower()
                if not dep_id:
                    continue
                departments[dep_id] = {
                    "id": dep_id,
                    "name": _clean_str(data.get("name"), 120) or f"Specialist · {dep_id.title()}",
                    "department": _clean_str(data.get("department"), 120) or "Dipartimento Speciale",
                    "prompt": _clean_str(data.get("prompt"), 2000),
                    "skills": [str(s)[:60] for s in data.get("skills", []) if isinstance(s, (str, int))],
                    "capabilities": [str(c)[:60] for c in data.get("capabilities", []) if isinstance(c, (str, int))],
                    "widgets": [w for w in data.get("widgets", []) if isinstance(w, dict)],
                    "path": str(filepath),
                }
            except Exception:
                continue
    return departments


def find_specialist(query: str, extra_dirs: list[Path] | None = None) -> dict | None:
    deps = scan_departments(extra_dirs)
    tokens = [t.lower() for t in re.split(r"\W+", query) if len(t) >= 3]
    if not tokens:
        return None
    for dep_id, prof in deps.items():
        if dep_id in tokens:
            return prof
    for dep_id, prof in deps.items():
        search_space = f"{dep_id} {prof['name']} {prof['department']} {' '.join(prof['skills'])} {' '.join(prof['capabilities'])}".lower()
        if any(tok in search_space for tok in tokens):
            return prof
    return None


def forge_department(
    domain: str,
    name: str = "",
    dept_name: str = "",
    prompt: str = "",
    skills: list[str] | None = None,
    widgets: list[dict] | None = None,
    capabilities: list[str] | None = None,
    target_dir: Path | None = None,
) -> dict:
    dest_dir = target_dir or DEFAULT_CATALOG_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9_-]", "_", domain.lower().strip())[:40] or "specialist"
    title = slug.replace("_", " ").title()
    record = {
        "id": slug,
        "name": name or f"Specialist · {title}",
        "department": dept_name or f"Dipartimento {title}",
        "prompt": prompt or f"Sei lo Specialista responsabile del dominio {title} per NunzioTech Agency.",
        "skills": skills or [f"{slug}-core", "domain-execution", "compliance", "verification"],
        "capabilities": capabilities or [f"{slug}_task", "data_synthesis"],
        "widgets": widgets or [{"id": f"{slug}_dashboard", "type": "domain_card", "title": f"Monitor {title}"}],
    }
    file_path = dest_dir / f"{slug}.json"
    file_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    record["path"] = str(file_path)
    return record
