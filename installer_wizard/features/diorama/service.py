import asyncio
import logging
import time

from features.brain.llm import BrainUnavailable
from tasks import background

from features.diorama import export, planner, recall, spec as S, store, templates

log = logging.getLogger("nuxiva.diorama")
CHUNK = 5
PACE = 0.28
jobs: dict[str, dict] = {}
FAILURES = (BrainUnavailable, ValueError, KeyError, TypeError, AttributeError)


def status(did: str) -> dict:
    return dict(jobs.get(did) or {"state": "idle", "stage": "", "stages": []})


def _set(did: str, **changes) -> None:
    jobs[did] = {**jobs.get(did, {"state": "idle", "stage": "", "stages": []}), **changes}


def create(prompt: str, ambient: bool = False) -> dict:
    clean = S.clean_text(prompt, 600)
    if len(clean) < 3:
        raise S.SpecError("prompt_short")
    known = recall.find(clean)
    if known:
        return store.load(known)
    if not ambient and store.count() >= store.MAX_DIORAMAS:
        raise S.SpecError("library_full")
    did = S.new_id()
    record = {"id": did, "title": "", "story": "", "prompt": clean, "created": int(time.time()), "base": S.clean_base({}),
              "look": S.clean_look({}), "items": [], "revision": 0, "ambient": ambient}
    if ambient:
        store.prune_ambient()
    store.save(record)
    _set(did, state="building", stage="outline", stages=list(templates.STAGES))
    background(_build(did))
    return record


async def _reveal(did: str, rows: list[dict]) -> None:
    for start in range(0, len(rows), CHUNK):
        record = store.load(did)
        record["items"] = S.clean_items(record["items"] + rows[start:start + CHUNK])
        record["revision"] += 1
        store.save(record)
        await asyncio.sleep(PACE)


async def _apply_outline(did: str, data: dict) -> dict:
    record = store.load(did)
    record["title"] = S.clean_text(data.get("title"), 80) or record["title"]
    record["story"] = S.clean_text(data.get("story"), 400)
    record["base"] = S.clean_base({**record["base"], **(data.get("base") if isinstance(data.get("base"), dict) else {})})
    record["look"] = S.clean_look({**record["look"], **(data.get("look") if isinstance(data.get("look"), dict) else {})})
    record["revision"] += 1
    store.save(record)
    return record


async def _from_template(did: str, prompt: str) -> None:
    plan = templates.compose(prompt)
    await _apply_outline(did, plan)
    for stage in templates.STAGES:
        _set(did, stage=stage)
        await _reveal(did, plan["stages"].get(stage, []))


async def _build(did: str) -> None:
    prompt = store.load(did)["prompt"]
    try:
        try:
            record = await _apply_outline(did, await planner.outline(prompt))
        except FAILURES as exc:
            log.info("diorama %s: outline fallback (%s)", did, type(exc).__name__)
            await _from_template(did, prompt)
            _set(did, state="done", stage="", mode="template")
            export.save(did)
            return
        for stage in templates.STAGES:
            _set(did, stage=stage)
            try:
                rows = await planner.stage_items(prompt, record["title"], record["base"], stage, store.load(did)["items"])
            except FAILURES as exc:
                log.info("diorama %s: stage %s skipped (%s)", did, stage, type(exc).__name__)
                rows = templates.compose(prompt, seed=int(did, 16))["stages"].get(stage, [])
            await _reveal(did, rows)
        _set(did, state="done", stage="", mode="brain")
        export.save(did)
    except KeyError:
        _set(did, state="error", stage="", error="missing")
    except OSError:
        _set(did, state="error", stage="", error="storage")


def _apply_ops(record: dict, data: dict) -> int:
    ops = data.get("ops") if isinstance(data.get("ops"), list) else []
    items = {i["id"]: i for i in record["items"]}
    changed = 0
    for op in ops[:40]:
        if not isinstance(op, dict):
            continue
        kind = op.get("op")
        try:
            if kind == "add" and len(items) < S.MAX_ITEMS:
                fresh = S.clean_item(op.get("item"))
                items[fresh["id"]] = fresh
                changed += 1
            elif kind == "update" and op.get("id") in items:
                old = items[op["id"]]
                patch = op.get("item") if isinstance(op.get("item"), dict) else {}
                merged = {**old, **{k: v for k, v in patch.items() if k != "id" and k != "kind"}}
                merged["params"] = {**old["params"], **(patch.get("params") if isinstance(patch.get("params"), dict) else {})}
                items[op["id"]] = S.clean_item({**merged, "kind": old["kind"]}, old["id"])
                changed += 1
            elif kind == "remove" and items.pop(op.get("id"), None):
                changed += 1
        except S.SpecError:
            continue
    record["items"] = list(items.values())
    if isinstance(data.get("look"), dict):
        record["look"] = S.clean_look({**record["look"], **data["look"]})
        changed += 1
    return changed


async def refine(did: str, instruction: str) -> dict:
    record = store.load(did)
    if status(did)["state"] == "building":
        raise S.SpecError("busy")
    _set(did, state="building", stage="refine")
    try:
        data = await planner.refine(record["prompt"], instruction, record)
        record = store.load(did)
        changed = _apply_ops(record, data)
        record["revision"] += 1
        store.save(record)
    except FAILURES:
        _set(did, state="done", stage="", error="refine")
        raise S.SpecError("refine_failed")
    _set(did, state="done", stage="", error="")
    export.save(did)
    return {"changed": changed, "revision": record["revision"]}
