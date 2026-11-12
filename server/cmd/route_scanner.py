import os
import importlib
from typing import List
from fastapi import APIRouter

class FeatureRouteScanner:
    def __init__(self, features_dir: str = None) -> None:
        if features_dir is None:
            features_dir = os.path.join(os.path.dirname(__file__), "..", "features")
        self.features_dir = os.path.abspath(features_dir)

    def scan_routers(self) -> List[APIRouter]:
        routers: List[APIRouter] = []
        seen_names = set()

        if not os.path.exists(self.features_dir):
            return routers

        for root, dirs, files in os.walk(self.features_dir):
            for file in files:
                if (file.endswith("_controller.py") or file == "controller.py") and not file.startswith("__"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, os.path.dirname(self.features_dir))
                    package = __name__.split(".cmd.", 1)[0]
                    mod_path = package + "." + rel_path.replace(os.path.sep, ".").removesuffix(".py")

                    try:
                        mod = importlib.import_module(mod_path)
                        for attr_name in dir(mod):
                            if attr_name.startswith("_"):
                                continue
                            attr = getattr(mod, attr_name)
                            if isinstance(attr, APIRouter) and attr not in routers:
                                key = f"{mod_path}.{attr_name}"
                                if key not in seen_names:
                                    seen_names.add(key)
                                    routers.append(attr)
                    except Exception:
                        pass

        return routers

route_scanner = FeatureRouteScanner()
