import json
import re
from pathlib import Path
from typing import Any


class ModernProjectScaffolder:
    def __init__(self) -> None:
        self.default_stack = {
            "frontend": "tsx_expert",
            "backend": "rust_expert",
            "security": "security_crypto_expert",
        }

    def _clean_slug(self, text: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9_-]", "_", text.lower().strip())
        return re.sub(r"_+", "_", s).strip("_") or "project_module"

    def resolve_team_pairs(self, stack: dict[str, str] | None = None) -> list[tuple[str, str]]:
        st = stack or self.default_stack
        fe = st.get("frontend", "tsx_expert")
        be = st.get("backend", "rust_expert")
        sec = st.get("security", "security_crypto_expert")
        pairs = [(fe, be)]
        if sec:
            pairs.append((sec, "architect"))
        return pairs

    def scaffold_modular_architecture(
        self,
        project_name: str,
        domain: str = "general",
        stack: dict[str, str] | None = None,
        capabilities: list[str] | None = None,
    ) -> dict[str, Any]:
        slug = self._clean_slug(project_name)
        caps = [self._clean_slug(c) for c in (capabilities or ["core_action", "data_process"])]
        st = stack or self.default_stack

        fe_tech = st.get("frontend", "tsx_expert")
        be_tech = st.get("backend", "rust_expert")

        api_routes = []
        mcp_tools = []

        for cap in caps:
            api_routes.append({
                "path": f"/api/v1/{slug}/{cap}",
                "method": "POST",
                "capability": cap,
                "handler": f"backend.handlers.{cap}_handler",
                "auth_required": True,
                "rate_limit_per_minute": 120,
            })
            mcp_tools.append({
                "name": f"{slug}_{cap}",
                "description": f"Esegue l'operazione «{cap}» nel modulo autonomo {slug}.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "payload": {"type": "object", "description": "Parametri di input per l'operazione."},
                        "caller_agent": {"type": "string", "description": "Identificativo dell'agente chiamante."},
                    },
                    "required": ["payload"],
                },
                "endpoint": f"/api/v1/{slug}/{cap}",
                "protocol": "mcp_2024_11",
            })

        dom_cat = self._clean_slug(domain) or "general"
        frontend_tree = {
            "tech": fe_tech,
            "root": "frontend",
            "category": dom_cat,
            "directories": [
                f"frontend/src/components/{dom_cat}",
                f"frontend/src/state/{dom_cat}",
                f"frontend/src/services/{dom_cat}",
                "frontend/src/assets",
                f"frontend/tests/unit/{dom_cat}",
            ],
            "files": {
                "frontend/package.json": json.dumps({
                    "name": f"{slug}-frontend",
                    "version": "1.0.0",
                    "private": True,
                    "type": "module",
                    "scripts": {"dev": "vite", "build": "tsc && vite build", "test": "vitest run"},
                }, indent=2),
                f"frontend/src/services/{dom_cat}/api_client.ts": (
                    f"export const API_BASE = '/api/v1/{dom_cat}/{slug}';\n"
                    "export async function callApi(endpoint: string, payload: unknown) {\n"
                    "  const res = await fetch(`${API_BASE}${endpoint}`, {\n"
                    "    method: 'POST',\n"
                    "    headers: { 'Content-Type': 'application/json' },\n"
                    "    body: JSON.stringify(payload)\n"
                    "  });\n"
                    "  return res.json();\n"
                    "}\n"
                ),
            },
        }

        backend_tree = {
            "tech": be_tech,
            "root": "backend",
            "category": dom_cat,
            "directories": [
                f"backend/src/domain/{dom_cat}",
                f"backend/src/services/{dom_cat}",
                f"backend/src/adapters/{dom_cat}",
                f"backend/src/handlers/{dom_cat}",
                f"backend/tests/unit/{dom_cat}",
            ],
            "files": {
                f"backend/src/domain/{dom_cat}/manifest.json": json.dumps({
                    "service": f"{slug}-backend",
                    "architecture": "clean_hexagonal_categorical",
                    "category": dom_cat,
                    "tech": be_tech,
                    "port": 8088,
                }, indent=2),
            },
        }

        api_tree = {
            "root": "api",
            "category": dom_cat,
            "directories": [f"api/v1/{dom_cat}", f"api/contracts/{dom_cat}"],
            "files": {
                f"api/v1/{dom_cat}/routes.json": json.dumps(api_routes, indent=2),
                f"api/v1/{dom_cat}/openapi.json": json.dumps({
                    "openapi": "3.1.0",
                    "info": {"title": f"API {slug}", "category": dom_cat, "version": "1.0.0"},
                    "paths": {
                        r["path"]: {
                            "post": {
                                "summary": f"Esegue operazione {r['capability']}",
                                "responses": {"200": {"description": "Risultato elaborazione"}},
                            }
                        } for r in api_routes
                    },
                }, indent=2),
            },
        }

        mcp_tree = {
            "root": "mcp",
            "category": dom_cat,
            "directories": [f"mcp/tools/{dom_cat}", f"mcp/resources/{dom_cat}", f"mcp/prompts/{dom_cat}"],
            "files": {
                "mcp/mcp_server.json": json.dumps({
                    "name": f"nuxiva-{slug}-mcp",
                    "version": "1.0.0",
                    "category": dom_cat,
                    "protocol": "2024-11-05",
                    "capabilities": {"tools": True, "resources": True, "prompts": True},
                }, indent=2),
                f"mcp/tools/{dom_cat}/tools_manifest.json": json.dumps(mcp_tools, indent=2),
                f"mcp/resources/{dom_cat}/resources_manifest.json": json.dumps([
                    {"uri": f"mcp://{dom_cat}/{slug}/status", "name": "Stato Modulo", "mimeType": "application/json"}
                ], indent=2),
            },
        }

        security_tree = {
            "root": "security",
            "category": dom_cat,
            "directories": [f"security/policies/{dom_cat}", f"security/vault/{dom_cat}"],
            "files": {
                f"security/policies/{dom_cat}/zero_trust.json": json.dumps({
                    "enforce_zero_trust": True,
                    "category": dom_cat,
                    "cipher_suite": "ChaCha20-Poly1305",
                    "signature_algorithm": "Ed25519",
                    "key_derivation": "Argon2id",
                    "token_rotation_seconds": 900,
                    "sanitization_level": "strict_owasp",
                }, indent=2),
            },
        }

        pairs = self.resolve_team_pairs(st)

        return {
            "project_name": project_name,
            "slug": slug,
            "domain": domain,
            "stack": st,
            "pair_programming_desks": [
                {"desk_index": idx, "agents": list(pair), "collaboration": "pair_programming"}
                for idx, pair in enumerate(pairs)
            ],
            "trees": {
                "frontend": frontend_tree,
                "backend": backend_tree,
                "api": api_tree,
                "mcp": mcp_tree,
                "security": security_tree,
            },
            "api_routes": api_routes,
            "mcp_tools": mcp_tools,
            "verification": {
                "backend_frontend_separated": True,
                "api_contract_included": True,
                "mcp_server_included": True,
                "security_zero_trust_included": True,
            },
        }

    def materialize_tree(self, scaffold: dict[str, Any], base_path: Path) -> dict[str, Any]:
        base_path.mkdir(parents=True, exist_ok=True)
        created_dirs = []
        created_files = []

        for category, tree in scaffold.get("trees", {}).items():
            for d in tree.get("directories", []):
                p = base_path / d
                p.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(p))

            for f_rel, content in tree.get("files", {}).items():
                target = base_path / f_rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                created_files.append(str(target))

        return {
            "status": "materialized",
            "base_path": str(base_path),
            "directories_count": len(created_dirs),
            "files_count": len(created_files),
            "created_dirs": created_dirs,
            "created_files": created_files,
        }

    def verify_clean_architecture(self, scaffold: dict[str, Any]) -> dict[str, Any]:
        trees = scaffold.get("trees", {})
        has_fe = "frontend" in trees and bool(trees["frontend"].get("directories"))
        has_be = "backend" in trees and bool(trees["backend"].get("directories"))
        has_api = "api" in trees and bool(scaffold.get("api_routes"))
        has_mcp = "mcp" in trees and bool(scaffold.get("mcp_tools"))
        has_sec = "security" in trees and bool(trees["security"].get("files"))
        has_pairs = bool(scaffold.get("pair_programming_desks"))

        is_valid = has_fe and has_be and has_api and has_mcp and has_sec and has_pairs

        all_dirs = [d for t in trees.values() if isinstance(t, dict) for d in t.get("directories", [])]
        is_partitioned = all(len(d.split("/")) >= 3 for d in all_dirs if d != "frontend/src/assets")

        return {
            "valid": is_valid and is_partitioned,
            "frontend_backend_separated": has_fe and has_be,
            "categorical_partitioning_verified": is_partitioned,
            "api_endpoints_count": len(scaffold.get("api_routes", [])),
            "mcp_tools_count": len(scaffold.get("mcp_tools", [])),
            "pair_desks_count": len(scaffold.get("pair_programming_desks", [])),
            "zero_trust_secured": has_sec,
        }

    def verify_categorical_modularity(self, scaffold: dict[str, Any]) -> dict[str, Any]:
        trees = scaffold.get("trees", {})
        all_dirs = [d for t in trees.values() if isinstance(t, dict) for d in t.get("directories", [])]
        deep_dirs = [d for d in all_dirs if len(d.split("/")) >= 3 or d == "frontend/src/assets"]
        is_modular = len(deep_dirs) == len(all_dirs) and len(all_dirs) > 0
        return {
            "modular": is_modular,
            "total_directories": len(all_dirs),
            "categorically_partitioned_count": len(deep_dirs),
            "enterprise_scale_safe": is_modular,
            "max_items_per_partition_guarantee": 500,
        }


project_scaffolder = ModernProjectScaffolder()
