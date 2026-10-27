import ast
import difflib
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
    def build_repo_map(cls, mission: Mission) -> str:
        if not mission.artifacts:
            return "Workspace vuoto (nessun file ancora generato)."
        lines: list[str] = ["REPOSITORY MAP (Simboli & Architettura Attuale):"]
        for art in mission.artifacts:
            sym_str = ", ".join(art.symbols[:10]) if art.symbols else "nessun simbolo esportato"
            lines.append(
                f"- {art.relative_path} ({art.line_count} righe, {art.size_bytes}B) [by {art.generated_by}]: {sym_str}"
            )
        return "\n".join(lines)

    @classmethod
    def export_repo_map_data(cls, mission: Mission) -> dict[str, Any]:
        files = []
        total_lines = 0
        total_symbols = 0
        for art in mission.artifacts:
            total_lines += art.line_count
            total_symbols += len(art.symbols)
            files.append({
                "path": art.relative_path,
                "title": art.title,
                "kind": art.kind,
                "line_count": art.line_count,
                "size_bytes": art.size_bytes,
                "checksum": art.checksum,
                "generated_by": art.generated_by,
                "symbols": list(art.symbols),
                "has_diff": bool(art.diff),
                "timestamp": art.timestamp,
            })
        return {
            "mission_id": mission.id,
            "total_files": len(files),
            "total_lines": total_lines,
            "total_symbols": total_symbols,
            "files": files,
        }


code_intel = CodeIntelligenceEngine()
