import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import runtime_check  # noqa: E402


def locate(dist: Path) -> Path:
    for candidate in (dist / "_internal" / "customtkinter", dist / "customtkinter"):
        if candidate.is_dir():
            return candidate
    return dist / "_internal" / "customtkinter"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("uso: verify_bundle.py <cartella-dist>", file=sys.stderr)
        return 2
    absent = runtime_check.missing_assets(locate(Path(argv[1])))
    if absent:
        print("File mancanti nel pacchetto: " + ", ".join(absent), file=sys.stderr)
        return 1
    print("Pacchetto completo")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
