import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main(version: str) -> int:
    now = datetime.datetime.now(datetime.timezone.utc)
    name = f"{now:%Y%m%d%H%M%S}-release-{version.replace('.', '-')}.json"
    note = {
        "schema": 1,
        "date": f"{now:%Y-%m-%d}",
        "title": {
            "it": f"Rilascio {version}",
            "en": f"Release {version}",
            "fr": f"Version {version}",
            "es": f"Versión {version}",
        },
        "fixes": [{
            "it": f"Versione {version} allineata su server, app Android e installer Windows.",
            "en": f"Version {version} aligned across server, Android app and Windows installer.",
            "fr": f"Version {version} alignée sur le serveur, l'application Android et l'installateur Windows.",
            "es": f"Versión {version} alineada en servidor, aplicación Android e instalador de Windows.",
        }],
    }
    (ROOT / "changelog" / name).write_text(json.dumps(note, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
