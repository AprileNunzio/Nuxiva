import json
import logging
import shutil

from features.diorama import spec as S, store
from features.shares import archive

log = logging.getLogger("nuxiva.diorama")
LABELS = {"terrain": "terreno", "structures": "strutture", "vegetation": "vegetazione", "props": "arredi", "life": "vita", "details": "rifiniture", "user": "aggiunte"}


def _write(path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def save(did: str) -> None:
    try:
        record = store.load(did)
        if not record["items"]:
            return
        root = archive.folder("diorami")
        name = f"{archive.clean(record['title'] or record['prompt'], 'diorama')[:50]}-{did}"
        shutil.rmtree(root / name, ignore_errors=True)
        (root / f"{name}.json").unlink(missing_ok=True)
        target = root / name
        target.mkdir(parents=True, exist_ok=True)
        _write(target / "scena.json", {k: record[k] for k in ("title", "story", "prompt", "created", "base", "look", "brief")})
        for layer in S.LAYERS:
            rows = [i for i in record["items"] if i["layer"] == layer]
            if rows:
                _write(target / f"{LABELS[layer]}.json", rows)
    except (KeyError, OSError) as exc:
        log.info("diorama %s: export to share skipped (%s)", did, type(exc).__name__)
