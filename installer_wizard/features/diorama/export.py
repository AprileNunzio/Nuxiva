import json
import logging

from features.diorama import store
from features.shares import archive

log = logging.getLogger("nuxiva.diorama")


def save(did: str) -> None:
    try:
        record = store.load(did)
        if not record["items"]:
            return
        target = archive.folder("diorami") / f"{archive.clean(record['title'] or record['prompt'], 'diorama')[:50]}-{did}.json"
        payload = {"title": record["title"], "story": record["story"], "prompt": record["prompt"], "created": record["created"],
                   "base": record["base"], "look": record["look"], "items": record["items"]}
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except (KeyError, OSError) as exc:
        log.info("diorama %s: export to share skipped (%s)", did, type(exc).__name__)
