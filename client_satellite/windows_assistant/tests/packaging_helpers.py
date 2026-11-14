import importlib.util
from pathlib import Path

PACKAGING = Path(__file__).resolve().parent.parent / "packaging"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, PACKAGING / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
