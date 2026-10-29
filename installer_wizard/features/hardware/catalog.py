from __future__ import annotations

import fnmatch
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from features.hardware.catalog_validation import validate_catalog
from typing import Any, Dict, List, Optional

log = logging.getLogger("nuxiva.hardware.catalog")

CATALOG_DIR = Path(__file__).resolve().parent / "data"

PKG_KEY = {"apt": "apt", "dnf": "dnf", "yum": "dnf", "zypper": "zypper", "pacman": "pacman"}


@dataclass
class Recipe:
    id: str
    name: str
    category: str
    modules: List[str] = field(default_factory=list)
    firmware: List[str] = field(default_factory=list)
    packages: Dict[str, List[str]] = field(default_factory=dict)
    repos: List[str] = field(default_factory=list)
    dkms: Optional[Dict[str, Any]] = None
    tools: List[str] = field(default_factory=list)

    def packages_for(self, pkg_manager: str, distro_family: str = "") -> List[str]:
        return distro_packages(list(self.packages.get(PKG_KEY.get(pkg_manager, ""), [])), distro_family)


class Catalog:
    def __init__(self, directory: Path = CATALOG_DIR) -> None:
        self._dir = directory
        self._loaded = False
        self._recipes: List[Recipe] = []
        self._index: Dict[str, Recipe] = {}
        self._categories: Dict[str, Dict[str, Any]] = {}
        self._firmware_map: List[List[Any]] = []
        self._gpu: Dict[str, Dict[str, Any]] = {}

    def _read(self, name: str) -> Dict[str, Any]:
        try:
            return validate_catalog(json.loads((self._dir / name).read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            log.warning("Catalogo %s non leggibile: %s", name, exc)
            raise ValueError(f"Invalid hardware catalog: {name}") from exc

    def _load(self) -> None:
        if self._loaded:
            return
        data = self._read("drivers.json")
        for raw in data.get("recipes", []):
            recipe = Recipe(
                id=raw["id"],
                name=raw.get("name", raw["id"]),
                category=raw.get("category", "other"),
                modules=list(raw.get("modules", [])),
                firmware=list(raw.get("firmware", [])),
                packages={k: list(v) for k, v in raw.get("packages", {}).items()},
                repos=list(raw.get("repos", [])),
                dkms=raw.get("dkms"),
            )
            self._recipes.append(recipe)
            for bus, ids in raw.get("match", {}).items():
                for pair in ids:
                    self._index[f"{bus}:{pair.lower()}"] = recipe
        self._categories = data.get("categories", {})
        self._firmware_map = data.get("firmware_map", [])
        self._gpu = self._read("gpu.json").get("vendors", {})
        self._loaded = True

    def reload(self) -> None:
        self._loaded = False
        self._recipes.clear()
        self._index.clear()
        self._load()

    @property
    def recipes(self) -> List[Recipe]:
        self._load()
        return list(self._recipes)

    def find(self, bus: str, vendor_id: str, product_id: str) -> Optional[Recipe]:
        self._load()
        return self._index.get(f"{bus}:{vendor_id.lower()}:{product_id.lower()}")

    def category(self, name: str) -> Dict[str, Any]:
        self._load()
        return self._categories.get(name, {})

    def category_packages(self, name: str, pkg_manager: str, distro_family: str = "") -> List[str]:
        cat = self.category(name)
        return distro_packages(list(cat.get("packages", {}).get(PKG_KEY.get(pkg_manager, ""), [])), distro_family)

    def firmware_packages(self, firmware_file: str, pkg_manager: str, distro_family: str = "") -> List[str]:

        self._load()
        key = PKG_KEY.get(pkg_manager, "")
        for pattern, per_manager in self._firmware_map:
            if fnmatch.fnmatchcase(firmware_file, pattern):
                if key in per_manager:
                    return distro_packages(list(per_manager[key]), distro_family)
        return []

    def gpu_vendor(self, vendor_id: str) -> Optional[Dict[str, Any]]:
        self._load()
        return self._gpu.get(vendor_id.lower())


catalog = Catalog()


def distro_packages(packages, family):
    if family != "ubuntu":
        return packages
    result = []
    for package in packages:
        if package.startswith("firmware-"):
            package = "linux-firmware"
        if package not in result:
            result.append(package)
    return result
