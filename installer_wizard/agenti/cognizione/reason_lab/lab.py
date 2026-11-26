import csv
import io
import json

from fastapi import HTTPException

import native_core

TEMPLATE = [
    {"id": "weather_tomorrow", "category": "simple", "expected": {"intent": "weather_forecast", "effects": ["read"]},
     "texts": {"it": "che tempo farà domani a Roma", "en": "what will the weather be like in Rome tomorrow"}},
    {"id": "dog_photo_send", "category": "composite",
     "expected": {"intent": "send_image", "effects": ["read", "send_external"]},
     "texts": {"it": "cerca una foto di un San Bernardo e inviamela su Telegram", "en": "find a photo of a Saint Bernard and send it to me on Telegram"}},
]
CSV_COLUMNS = ("case_id", "lang", "category", "expected_intent", "intent", "intent_match", "success", "wrong_action",
               "completed", "tokens", "latency_ms", "reward_bps")
FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def native(name: str):
    function = native_core.symbol(name)
    if function is None:
        raise HTTPException(503, "native_unavailable")
    return function


def native_ready() -> bool:
    return all(native_core.symbol(n) is not None for n in ("reason_lab_run_case", "reason_lab_report", "reason_lab_rows", "reason_lab_inspect", "reason_lab_cases", "reason_lab_check_endpoint"))


def call(name: str, *args):
    function = native(name)
    try:
        return json.loads(function(*args))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def check_endpoint(base_url: str) -> None:
    try:
        native("reason_lab_check_endpoint")(base_url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def inspect(scenarios: list) -> dict:
    return call("reason_lab_inspect", json.dumps(scenarios, ensure_ascii=False))


def cases(scenarios: list) -> list:
    return call("reason_lab_cases", json.dumps(scenarios, ensure_ascii=False))


def report(scenarios: list, outcomes: str) -> dict:
    return call("reason_lab_report", json.dumps(scenarios, ensure_ascii=False), outcomes)


def rows(scenarios: list, outcomes: str) -> list:
    return call("reason_lab_rows", json.dumps(scenarios, ensure_ascii=False), outcomes)


def compare(baseline: dict, candidate: dict) -> dict:
    function = native_core.symbol("reason_lab_compare")
    if function is None:
        raise HTTPException(503, "native_outdated")
    try:
        result = json.loads(function(json.dumps(baseline, ensure_ascii=False), json.dumps(candidate, ensure_ascii=False)))
    except ValueError as exc:
        if "dataset_mismatch" in str(exc):
            return {"comparable": False}
        raise HTTPException(422, str(exc)) from exc
    return {"comparable": True, **result}


def safe_cell(value) -> str:
    text = ",".join(value) if isinstance(value, list) else str(value)
    return "'" + text if text.startswith(FORMULA_START) else text


def to_csv(table: list) -> str:
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(CSV_COLUMNS)
    for row in table:
        writer.writerow([safe_cell(row.get(column, "")) for column in CSV_COLUMNS])
    return stream.getvalue()
