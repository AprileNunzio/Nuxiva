import glob
import importlib.util
import json
from pathlib import Path
from typing import Any

DEFAULT_TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools_catalog"


def _import_module_from_file(filepath: Path) -> Any | None:
    try:
        if filepath.parent.resolve() == DEFAULT_TOOLS_DIR.resolve():
            import importlib
            return importlib.import_module(f"agenti.agency.tools_catalog.{filepath.stem}")
        mod_name = f"agency_tool_{filepath.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, filepath)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    except Exception:
        return None
    return None


def scan_tools(extra_dirs: list[Path] | None = None) -> dict[str, Any]:
    dirs = [DEFAULT_TOOLS_DIR]
    if extra_dirs:
        dirs.extend(extra_dirs)
    tools: dict[str, Any] = {}
    for d in dirs:
        if not d.exists() or not d.is_dir():
            continue
        for py_path in sorted(d.glob("*.py")):
            if py_path.name.startswith("__"):
                continue
            mod = _import_module_from_file(py_path)
            if mod is None:
                continue
            if hasattr(mod, "get_tools") and callable(mod.get_tools):
                for t in mod.get_tools():
                    if hasattr(t, "name"):
                        tools[t.name] = t
            elif hasattr(mod, "TOOLS") and isinstance(mod.TOOLS, dict):
                for name, t in mod.TOOLS.items():
                    tools[name] = t
            elif hasattr(mod, "TOOLS") and isinstance(mod.TOOLS, (list, tuple)):
                for t in mod.TOOLS:
                    if hasattr(t, "name"):
                        tools[t.name] = t
        for json_path in sorted(d.glob("*.json")):
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "name" in data and "description" in data:
                    t_name = data["name"]
                    from agenti.agency.tools import Tool
                    tools[t_name] = Tool(
                        name=t_name,
                        description=data["description"],
                        args=data.get("args", {}),
                        capability=data.get("capability", "execute"),
                        runner=lambda ctx, a, d=data: json.dumps({"status": "executed", "tool": d["name"], "input": a}),
                    )
            except Exception:
                continue
    return tools
