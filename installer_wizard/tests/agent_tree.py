from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "agenti"


class AgentTree:
    root = ROOT

    def __truediv__(self, ident: str) -> Path:
        for path in sorted(ROOT.glob(f"*/{ident}")):
            if path.is_dir():
                return path
        return ROOT / "_assente" / ident

    def glob(self, pattern: str) -> list[Path]:
        return sorted(ROOT.glob(f"*/{pattern}"))

    def categories(self) -> list[Path]:
        return sorted(p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith("_"))


AGENTS = AgentTree()
