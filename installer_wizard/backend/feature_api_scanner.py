import importlib
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger("nuxiva.feature_api_scanner")


def discover_feature_apis(root: Path | None = None):
    directory = root or Path(__file__).resolve().parents[1] / "features"
    modules = []
    for manifest in sorted(directory.glob("*/feature.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            folder = manifest.parent.name
            if data.get("api") != "api.py" or not re.fullmatch(r"[a-z][a-z0-9_]*", folder):
                continue
            modules.append(importlib.import_module(f"features.{folder}.api"))
        except (OSError, ValueError, ImportError) as exc:
            logger.warning("Feature API unavailable: %s (%s)", manifest.parent.name, type(exc).__name__)
    return modules
