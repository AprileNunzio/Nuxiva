import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from server.core.games_scanner.contracts import (
    GameManifest,
    GameCommand,
    GameCapability,
    CommandInputType,
    CapabilityCategory,
)

class GameIntrospector:
    SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")

    @classmethod
    def validate_game_id(cls, game_id: str) -> bool:
        return bool(cls.SAFE_ID_REGEX.match(game_id))

    @classmethod
    def introspect_directory(cls, dir_path: str) -> Tuple[Optional[GameManifest], List[str]]:
        violations: List[str] = []
        clean_dir = os.path.abspath(dir_path)
        if not os.path.exists(clean_dir) or not os.path.isdir(clean_dir):
            violations.append(f"Directory does not exist: {dir_path}")
            return None, violations

        raw_id = os.path.basename(clean_dir)
        if not cls.validate_game_id(raw_id):
            violations.append(f"Invalid game folder name: {raw_id}")
            return None, violations

        manifest_file = os.path.join(clean_dir, "manifest.json")
        metadata_file = os.path.join(clean_dir, "metadata.json")
        package_file = os.path.join(clean_dir, "package.json")

        manifest_data: Dict[str, Any] = {}
        if os.path.exists(manifest_file):
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
            except Exception as e:
                violations.append(f"Failed to parse manifest.json: {str(e)}")

        if not manifest_data and os.path.exists(metadata_file):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    meta_raw = json.load(f)
                    manifest_data = cls._convert_metadata_to_manifest(meta_raw, raw_id)
            except Exception as e:
                violations.append(f"Failed to parse metadata.json: {str(e)}")

        pkg_data: Dict[str, Any] = {}
        if os.path.exists(package_file):
            try:
                with open(package_file, "r", encoding="utf-8") as f:
                    pkg_data = json.load(f)
            except Exception as e:
                violations.append(f"Failed to parse package.json: {str(e)}")

        entrypoint = cls._detect_entrypoint(clean_dir, manifest_data)
        if not entrypoint:
            violations.append("Entrypoint not detected")
            return None, violations

        tech_stack = cls._detect_tech_stack(clean_dir, pkg_data)
        commands = cls._extract_commands(manifest_data)
        capabilities = cls._extract_capabilities(clean_dir, manifest_data, pkg_data)

        game_manifest = GameManifest(
            game_id=manifest_data.get("id", raw_id),
            name=manifest_data.get("name", raw_id.replace("-", " ").title()),
            version=manifest_data.get("version", pkg_data.get("version", "1.0.0")),
            category=manifest_data.get("category", "games"),
            description=manifest_data.get("description", pkg_data.get("description", "")),
            icon=manifest_data.get("icon", "🎮"),
            entrypoint=entrypoint,
            tech_stack=tech_stack,
            commands=commands,
            capabilities=capabilities,
            directory_path=clean_dir,
            is_active=manifest_data.get("is_active", True),
            metadata=manifest_data.get("metadata", {}),
        )

        return game_manifest, violations

    @classmethod
    def _convert_metadata_to_manifest(cls, meta_raw: Dict[str, Any], raw_id: str) -> Dict[str, Any]:
        return {
            "id": raw_id,
            "name": meta_raw.get("name", raw_id.title()),
            "description": meta_raw.get("description", ""),
            "version": "1.0.0",
            "category": "games",
            "commands": [],
            "capabilities": meta_raw.get("majorCapabilities", []),
        }

    @classmethod
    def _detect_entrypoint(cls, clean_dir: str, manifest_data: Dict[str, Any]) -> Optional[str]:
        if "entrypoint" in manifest_data:
            custom_entry = os.path.join(clean_dir, manifest_data["entrypoint"])
            if os.path.exists(custom_entry):
                return manifest_data["entrypoint"]

        candidates = [
            "index.html",
            "src/main.tsx",
            "src/main.ts",
            "src/App.tsx",
            "src/index.js",
            "main.py",
            "app.py",
        ]
        for candidate in candidates:
            if os.path.exists(os.path.join(clean_dir, candidate)):
                return candidate
        return None

    @classmethod
    def _detect_tech_stack(cls, clean_dir: str, pkg_data: Dict[str, Any]) -> List[str]:
        stack: List[str] = []
        deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}

        if "three" in deps or os.path.exists(os.path.join(clean_dir, "public", "assets", "glb")):
            stack.append("threejs")
            stack.append("webgl_3d")
        if "react" in deps:
            stack.append("react")
        if "vite" in deps or os.path.exists(os.path.join(clean_dir, "vite.config.ts")):
            stack.append("vite")
        if "@google/genai" in deps:
            stack.append("gemini_genai")
        if os.path.exists(os.path.join(clean_dir, "requirements.txt")) or os.path.exists(os.path.join(clean_dir, "main.py")):
            stack.append("python")

        return sorted(list(set(stack)))

    @classmethod
    def _extract_commands(cls, manifest_data: Dict[str, Any]) -> List[GameCommand]:
        raw_commands = manifest_data.get("commands", [])
        commands: List[GameCommand] = []

        for item in raw_commands:
            input_types: List[CommandInputType] = []
            for it in item.get("input_types", ["ui_action"]):
                try:
                    input_types.append(CommandInputType(it))
                except ValueError:
                    input_types.append(CommandInputType.UI_ACTION)

            commands.append(
                GameCommand(
                    command_id=item["command_id"],
                    name_key=item.get("name_key", item["command_id"]),
                    description_key=item.get("description_key", f"{item['command_id']}_desc"),
                    input_types=input_types,
                    voice_triggers=item.get("voice_triggers", []),
                    parameters=item.get("parameters", {}),
                    requires_confirmation=item.get("requires_confirmation", False),
                    is_async=item.get("is_async", False),
                )
            )

        return commands

    @classmethod
    def _extract_capabilities(cls, clean_dir: str, manifest_data: Dict[str, Any], pkg_data: Dict[str, Any]) -> List[GameCapability]:
        declared = manifest_data.get("capabilities", [])
        capabilities: List[GameCapability] = []
        declared_ids = set()

        for item in declared:
            if isinstance(item, dict):
                cid = item["capability_id"]
                category = CapabilityCategory.INPUT
                try:
                    category = CapabilityCategory(item.get("category", "input"))
                except ValueError:
                    pass
                capabilities.append(
                    GameCapability(
                        capability_id=cid,
                        category=category,
                        name_key=item.get("name_key", cid),
                        description_key=item.get("description_key", f"{cid}_desc"),
                        enabled=item.get("enabled", True),
                        metadata=item.get("metadata", {}),
                    )
                )
                declared_ids.add(cid)
            elif isinstance(item, str):
                capabilities.append(
                    GameCapability(
                        capability_id=item,
                        category=CapabilityCategory.INPUT,
                        name_key=item,
                        description_key=f"{item}_desc",
                        enabled=True,
                    )
                )
                declared_ids.add(item)

        if "threejs" in cls._detect_tech_stack(clean_dir, pkg_data) and "3d_rendering" not in declared_ids:
            capabilities.append(
                GameCapability(
                    capability_id="3d_rendering",
                    category=CapabilityCategory.RENDERING,
                    name_key="capability_3d_rendering",
                    description_key="capability_3d_rendering_desc",
                    enabled=True,
                )
            )

        return capabilities
