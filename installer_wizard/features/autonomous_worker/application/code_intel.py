import ast
import difflib
from pathlib import PurePosixPath
import re
from typing import Any

from features.autonomous_worker.domain.models import Mission

MAX_FILE_LINES = 500

TS_SYMBOL_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class|interface|type|const|enum)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
RUST_SYMBOL_RE = re.compile(
    r"^\s*(?:pub\s+)?(?:async\s+)?(?:fn|struct|enum|trait|mod)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
TS_IMPORT_RE = re.compile(
    r"import\s+(?:type\s+)?(?:\{([^}]+)\}|([A-Za-z_][A-Za-z0-9_]*))\s+from\s+['\"]([^'\"]+)['\"]"
)
RUST_USE_RE = re.compile(r"^\s*use\s+([A-Za-z0-9_:{}*,\s]+);", re.MULTILINE)


class CodeIntelligenceEngine:
    @staticmethod
    def extract_symbols(file_path: str, content: str) -> list[str]:
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        symbols: list[str] = []

        if ext == "py":
            try:
                tree = ast.parse(content)
                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.ClassDef):
                        methods = [
                            n.name
                            for n in node.body
                            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ]
                        suffix = f" ({', '.join(methods[:6])})" if methods else ""
                        symbols.append(f"class {node.name}{suffix}")
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = [a.arg for a in node.args.args[:5]]
                        symbols.append(f"def {node.name}({', '.join(args)})")
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and not target.id.startswith("_"):
                                symbols.append(f"var {target.id}")
            except SyntaxError:
                pass
        elif ext in ("ts", "tsx", "js", "jsx"):
            for match in TS_SYMBOL_RE.finditer(content):
                sym = match.group(1)
                if sym not in symbols:
                    symbols.append(sym)
        elif ext == "rs":
            for match in RUST_SYMBOL_RE.finditer(content):
                sym = match.group(1)
                if sym not in symbols:
                    symbols.append(sym)

        return symbols[:35]

    @staticmethod
    def extract_imports(file_path: str, content: str) -> list[str]:
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        imports: list[str] = []

        if ext == "py":
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        for alias in node.names:
                            entry = f"{node.module}:{alias.name}"
                            if entry not in imports:
                                imports.append(entry)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name not in imports:
                                imports.append(alias.name)
            except SyntaxError:
                pass
        elif ext in ("ts", "tsx", "js", "jsx"):
            for match in TS_IMPORT_RE.finditer(content):
                named_group, default_ident, mod_path = match.group(1), match.group(2), match.group(3)
                if named_group:
                    for raw_sym in named_group.split(","):
                        sym = raw_sym.strip().split(" as ")[0].replace("type ", "").strip()
                        if sym:
                            entry = f"{mod_path}:{sym}"
                            if entry not in imports:
                                imports.append(entry)
                elif default_ident:
                    entry = f"{mod_path}:{default_ident.strip()}"
                    if entry not in imports:
                        imports.append(entry)
        elif ext == "rs":
            for match in RUST_USE_RE.finditer(content):
                use_stmt = match.group(1).strip()
                if use_stmt not in imports:
                    imports.append(use_stmt)

        return imports[:40]

    @staticmethod
    def bare_symbol_names(symbols: list[str]) -> set[str]:
        names: set[str] = set()
        for sym in symbols:
            cleaned = sym.strip()
            if cleaned.startswith("class "):
                head = cleaned[6:].split("(", 1)[0].strip()
                names.add(head)
            elif cleaned.startswith("def "):
                head = cleaned[4:].split("(", 1)[0].strip()
                names.add(head)
            elif cleaned.startswith("var "):
                names.add(cleaned[4:].strip())
            else:
                names.add(cleaned.split("(", 1)[0].strip())
        return names

    @classmethod
    def analyze_dependencies(cls, mission: Mission) -> tuple[list[dict[str, str]], list[str]]:
        edges: list[dict[str, str]] = []
        warnings: list[str] = []
        stem_map: dict[str, Any] = {}
        for art in mission.artifacts:
            posix = PurePosixPath(art.relative_path)
            stem_no_ext = str(posix.with_suffix("")).replace("/", ".")
            stem_map[stem_no_ext] = art
            stem_map[posix.stem] = art

        for art in mission.artifacts:
            for imp in art.imports:
                if ":" not in imp:
                    continue
                mod_ref, sym_name = imp.split(":", 1)
                if sym_name == "*":
                    continue
                norm_mod = mod_ref.lstrip("./").replace("/", ".")
                target_art = stem_map.get(norm_mod) or stem_map.get(norm_mod.rsplit(".", 1)[-1])
                if not target_art or target_art.relative_path == art.relative_path:
                    continue
                edges.append({
                    "from": art.relative_path,
                    "to": target_art.relative_path,
                    "symbol": sym_name,
                })
                exported = cls.bare_symbol_names(target_art.symbols)
                if exported and sym_name not in exported:
                    warnings.append(
                        f"Contratto disallineato: '{art.relative_path}' importa '{sym_name}' da '{target_art.relative_path}', "
                        f"ma i simboli esportati sono [{', '.join(sorted(exported))}]"
                    )
        return edges, warnings

    @staticmethod
    def compute_unified_diff(old_text: str, new_text: str, relative_path: str) -> str:
        old_lines = old_text.splitlines(keepends=True) if old_text else []
        new_lines = new_text.splitlines(keepends=True) if new_text else []
        diff_gen = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
            n=3,
        )
        diff_str = "".join(diff_gen)
        return diff_str[:12000]

    @staticmethod
    def count_lines(content: str) -> int:
        if not content:
            return 0
        return len(content.splitlines())

    @classmethod
    def build_repo_map(cls, mission: Mission, focus_text: str = "") -> str:
        if not mission.artifacts:
            return "Workspace vuoto (nessun file ancora generato)."
        edges, warnings = cls.analyze_dependencies(mission)
        focus_tokens = {w.lower() for w in re.findall(r"[A-Za-z0-9_]{3,}", focus_text)}

        def score_art(art: Any) -> int:
            score = sum(1 for e in edges if e["to"] == art.relative_path or e["from"] == art.relative_path)
            path_low = art.relative_path.lower()
            for tok in focus_tokens:
                if tok in path_low or any(tok in s.lower() for s in art.symbols):
                    score += 5
            return score

        ranked = sorted(mission.artifacts, key=score_art, reverse=True)
        lines: list[str] = ["REPOSITORY MAP (Simboli AST, Versioni & Dipendenze Cross-File):"]
        for art in ranked[:45]:
            sym_str = ", ".join(art.symbols[:10]) if art.symbols else "nessun simbolo esportato"
            imp_str = f" | imports: {', '.join(art.imports[:6])}" if art.imports else ""
            lines.append(
                f"- {art.relative_path} (v{art.version}, {art.line_count}L, {art.size_bytes}B) [by {art.generated_by}]: {sym_str}{imp_str}"
            )
        if warnings:
            lines.append("\nAVVISI DI CONTRATTO CROSS-FILE RILEVATI:")
            for w in warnings[:10]:
                lines.append(f"  ! {w}")
        return "\n".join(lines)

    @classmethod
    def export_repo_map_data(cls, mission: Mission) -> dict[str, Any]:
        files = []
        total_lines = 0
        total_symbols = 0
        edges, warnings = cls.analyze_dependencies(mission)
        for art in mission.artifacts:
            total_lines += art.line_count
            total_symbols += len(art.symbols)
            files.append({
                "path": art.relative_path,
                "title": art.title,
                "kind": art.kind,
                "version": art.version,
                "line_count": art.line_count,
                "size_bytes": art.size_bytes,
                "checksum": art.checksum,
                "generated_by": art.generated_by,
                "symbols": list(art.symbols),
                "imports": list(art.imports),
                "revisions_count": len(art.revisions),
                "has_diff": bool(art.diff),
                "timestamp": art.timestamp,
            })
        return {
            "mission_id": mission.id,
            "total_files": len(files),
            "total_lines": total_lines,
            "total_symbols": total_symbols,
            "dependency_edges": edges,
            "contract_warnings": warnings,
            "files": files,
        }


code_intel = CodeIntelligenceEngine()
