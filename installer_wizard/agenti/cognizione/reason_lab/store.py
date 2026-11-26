import json
import os
import re
import secrets
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import HTTPException

from config import STATE_DIR

ROOT = Path(STATE_DIR) / "reason_lab"
SLUG = re.compile(r"[a-z0-9][a-z0-9_]{2,39}")
RUN_ID = re.compile(r"[0-9]{14}-[0-9a-f]{6}")
MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@-]{0,99}")
BACKENDS = ("ollama", "openai", "studio")
MAX_DATASETS = 64
MAX_PROFILES = 32
MAX_RUNS = 200
MAX_NAME = 80
FINAL_STATES = ("completed", "cancelled", "failed", "interrupted")


def slug(value: str) -> str:
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise HTTPException(422, "invalid_id")
    return value


def run_id(value: str) -> str:
    if not isinstance(value, str) or not RUN_ID.fullmatch(value):
        raise HTTPException(422, "invalid_run_id")
    return value


def clean_name(value) -> str:
    text = value.strip() if isinstance(value, str) else ""
    if not text or len(text) > MAX_NAME or any(ord(c) < 32 for c in text):
        raise HTTPException(422, "invalid_name")
    return text


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.chmod(name, 0o600)
        os.replace(name, path)
    except OSError as exc:
        Path(name).unlink(missing_ok=True)
        raise HTTPException(503, "lab_storage_unavailable") from exc


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as exc:
        raise HTTPException(503, "lab_storage_invalid") from exc


def dataset_path(dataset_id: str) -> Path:
    return ROOT / "datasets" / f"{slug(dataset_id)}.json"


def list_datasets() -> list[dict]:
    folder = ROOT / "datasets"
    if not folder.is_dir():
        return []
    rows = []
    for path in sorted(folder.glob("*.json")):
        record = read_json(path, None)
        if isinstance(record, dict) and SLUG.fullmatch(path.stem):
            rows.append({"id": path.stem, "name": record.get("name", path.stem), "updated": record.get("updated", 0),
                         "summary": record.get("summary", {})})
    return rows


def load_dataset(dataset_id: str) -> dict:
    record = read_json(dataset_path(dataset_id), None)
    if not isinstance(record, dict) or not isinstance(record.get("scenarios"), list):
        raise HTTPException(404, "dataset_not_found")
    return record


def save_dataset(dataset_id: str, name: str, scenarios: list, summary: dict) -> dict:
    path = dataset_path(dataset_id)
    if not path.exists() and len(list_datasets()) >= MAX_DATASETS:
        raise HTTPException(409, "too_many_datasets")
    record = {"name": clean_name(name), "updated": int(time.time()), "summary": summary, "scenarios": scenarios}
    write_atomic(path, json.dumps(record, ensure_ascii=False))
    return record


def delete_dataset(dataset_id: str) -> None:
    path = dataset_path(dataset_id)
    if not path.exists():
        raise HTTPException(404, "dataset_not_found")
    path.unlink()


def profiles() -> dict:
    value = read_json(ROOT / "profiles.json", {})
    return value if isinstance(value, dict) else {}


def save_profiles(value: dict) -> None:
    if len(value) > MAX_PROFILES:
        raise HTTPException(409, "too_many_profiles")
    write_atomic(ROOT / "profiles.json", json.dumps(value, ensure_ascii=False))


def valid_model(value) -> str:
    if not isinstance(value, str) or not MODEL.fullmatch(value):
        raise HTTPException(422, "invalid_model")
    return value


def new_run_id() -> str:
    return time.strftime("%Y%m%d%H%M%S", time.gmtime()) + "-" + secrets.token_hex(3)


def run_dir(identifier: str) -> Path:
    return ROOT / "runs" / run_id(identifier)


def list_runs() -> list[dict]:
    folder = ROOT / "runs"
    if not folder.is_dir():
        return []
    rows = []
    for path in sorted(folder.iterdir(), reverse=True):
        meta = read_json(path / "meta.json", None) if RUN_ID.fullmatch(path.name) else None
        if isinstance(meta, dict):
            rows.append(meta)
    return rows


def load_run(identifier: str) -> dict:
    meta = read_json(run_dir(identifier) / "meta.json", None)
    if not isinstance(meta, dict):
        raise HTTPException(404, "run_not_found")
    return meta


def save_run(meta: dict) -> None:
    write_atomic(run_dir(meta["id"]) / "meta.json", json.dumps(meta, ensure_ascii=False))


def append_outcome(identifier: str, line: str) -> None:
    path = run_dir(identifier) / "outcomes.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(line + "\n")
        os.chmod(path, 0o600)
    except OSError as exc:
        raise HTTPException(503, "lab_storage_unavailable") from exc


def outcomes_text(identifier: str) -> str:
    try:
        return (run_dir(identifier) / "outcomes.jsonl").read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError as exc:
        raise HTTPException(503, "lab_storage_unavailable") from exc


def delete_run(identifier: str) -> None:
    folder = run_dir(identifier)
    if not folder.is_dir():
        raise HTTPException(404, "run_not_found")
    shutil.rmtree(folder)


def prune_runs() -> None:
    finished = [meta for meta in list_runs() if meta.get("state") in FINAL_STATES]
    for meta in finished[MAX_RUNS:]:
        shutil.rmtree(run_dir(meta["id"]), ignore_errors=True)
