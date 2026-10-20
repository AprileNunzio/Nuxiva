"""Read presentation metadata from each scanned feature's own dictionaries."""
import json
import re
from pathlib import Path


def localize_feature(manifest: dict, language: str | None) -> dict:
    if not language or not re.fullmatch(r"[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*", language):
        return manifest
    directory = Path(manifest["dir"]) / "language"
    candidates = [directory / f"{language}.json", directory / f"{language.split('-')[0].split('_')[0]}.json"]
    candidates.extend(sorted(directory.glob("*.json")))
    dictionary = {}
    for path in candidates:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            candidate = raw.get("dictionary", raw) if isinstance(raw, dict) else {}
            if isinstance(candidate, dict):
                dictionary = candidate
                break
        except (OSError, ValueError):
            continue
    result = dict(manifest)
    for key in ("name", "description"):
        if isinstance(dictionary.get(key), str):
            result[key] = dictionary[key]
    capabilities = dictionary.get("capabilities")
    if isinstance(capabilities, list) and all(isinstance(value, str) for value in capabilities):
        result["capabilities"] = capabilities
    labels = dictionary.get("settings", {})
    if isinstance(labels, dict):
        result["settings"] = [{**setting, "label": labels[setting["key"]] if isinstance(labels.get(setting["key"]), str) else setting.get("label", setting["key"])}
                              for setting in manifest.get("settings", [])]
    return result
