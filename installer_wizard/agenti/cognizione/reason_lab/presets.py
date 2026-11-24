import json
from pathlib import Path

from fastapi import HTTPException

FOLDER = Path(__file__).parent / "presets"
CATALOG = ("simple", "composite", "novel", "adversarial")
ALL = "all"


def scenarios_of(preset_id: str) -> list:
    if preset_id == ALL:
        merged, seen = [], set()
        for name in CATALOG:
            for scenario in scenarios_of(name):
                if scenario["id"] not in seen:
                    seen.add(scenario["id"])
                    merged.append(scenario)
        return merged
    if preset_id not in CATALOG:
        raise HTTPException(404, "preset_not_found")
    try:
        data = json.loads((FOLDER / f"{preset_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(500, "preset_unreadable") from exc
    if not isinstance(data, list):
        raise HTTPException(500, "preset_unreadable")
    return data


def listing() -> list[dict]:
    return [{"id": name, "dataset": f"predefinito_{name}", "scenarios": len(scenarios_of(name))} for name in (*CATALOG, ALL)]
