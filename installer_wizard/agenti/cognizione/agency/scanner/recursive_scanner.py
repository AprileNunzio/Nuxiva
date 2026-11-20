import json
import re
from pathlib import Path
from typing import Any, Generator


class RecursiveDirectoryScanner:
    def __init__(self, max_items_per_directory: int = 500) -> None:
        self.max_items_per_directory = max_items_per_directory

    def clean_slug(self, value: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9_-]", "_", str(value or "").lower().strip())
        return re.sub(r"_+", "_", s).strip("_") or "item"

    def scan_json_files(
        self,
        base_dir: Path,
        pattern: str = "*.json",
    ) -> Generator[tuple[Path, dict[str, Any], str], None, None]:
        if not base_dir.exists() or not base_dir.is_dir():
            return
        for file_path in sorted(base_dir.rglob(pattern)):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(base_dir)
            category = ".".join(rel.parent.parts) if str(rel.parent) != "." else "general"
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    yield file_path, data, category
            except Exception:
                continue

    def scan_python_modules(
        self,
        base_dir: Path,
        pattern: str = "*.py",
    ) -> Generator[tuple[Path, list[str], str], None, None]:
        if not base_dir.exists() or not base_dir.is_dir():
            return
        for file_path in sorted(base_dir.rglob(pattern)):
            if not file_path.is_file() or file_path.name.startswith("__"):
                continue
            rel = file_path.relative_to(base_dir)
            category = ".".join(rel.parent.parts) if str(rel.parent) != "." else "general"
            module_parts = list(rel.with_suffix("").parts)
            yield file_path, module_parts, category

    def compute_partition_path(
        self,
        base_dir: Path,
        category: str,
        item_id: str,
        shard_depth: int = 1,
    ) -> Path:
        cat_slug = self.clean_slug(category) or "general"
        target_dir = base_dir / cat_slug
        if shard_depth > 0 and len(item_id) >= 2:
            prefix = item_id[:2].lower()
            target_dir = target_dir / prefix
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / f"{item_id}.json"

    def audit_enterprise_scale_safety(self, base_dir: Path) -> dict[str, Any]:
        if not base_dir.exists() or not base_dir.is_dir():
            return {"safe": True, "directories_count": 0, "max_entries_in_single_dir": 0}

        max_entries = 0
        total_dirs = 0
        violations = []

        for p in base_dir.rglob("*"):
            if p.is_dir():
                total_dirs += 1
                try:
                    count = len(list(p.iterdir()))
                    if count > max_entries:
                        max_entries = count
                    if count > self.max_items_per_directory:
                        violations.append({"path": str(p), "entries": count})
                except Exception:
                    continue

        return {
            "safe": len(violations) == 0,
            "directories_count": total_dirs,
            "max_entries_in_single_dir": max_entries,
            "limit": self.max_items_per_directory,
            "violations": violations,
        }


recursive_scanner = RecursiveDirectoryScanner()
