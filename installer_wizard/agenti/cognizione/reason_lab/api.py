import json
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, SecretStr

from access import NO_CACHE, require_admin
from agenti.authz.access_control import require_permission
from agenti.reason_lab import lab, store
from agenti.reason_lab.runner import MAX_ACTIVE, MAX_CASES, MAX_CONCURRENCY, runner

admin_routes = APIRouter(prefix="/api/v5/reason-lab", tags=["Reason Lab"], dependencies=[Depends(require_admin)])
READ, EDIT, RUN = ["lab.read"], ["lab.edit"], ["lab.run"]
NODE = "local"
Category = Literal["simple", "composite", "novel", "adversarial"]


class DatasetBody(BaseModel):
    name: str = Field(max_length=store.MAX_NAME)
    scenarios: list[dict] = Field(max_length=1000)


class ProfileBody(BaseModel):
    name: str = Field(max_length=store.MAX_NAME)
    backend: Literal["ollama", "openai"]
    base_url: str = Field(max_length=256)
    model: str = Field(max_length=100)
    timeout_seconds: int = Field(60, ge=5, le=300)


class RunBody(BaseModel):
    dataset: str
    backend: Literal["ollama", "openai"]
    base_url: str = Field(max_length=256)
    model: str = Field(max_length=100)
    key: SecretStr | None = Field(None, max_length=512)
    label: str = Field("", max_length=store.MAX_NAME)
    languages: list[str] = Field(default_factory=list, max_length=12)
    categories: list[Category] = Field(default_factory=list, max_length=4)
    limit: int = Field(MAX_CASES, ge=1, le=MAX_CASES)
    concurrency: int = Field(1, ge=1, le=MAX_CONCURRENCY)
    timeout_seconds: int = Field(60, ge=5, le=300)


def json_response(payload) -> JSONResponse:
    return JSONResponse(payload, headers=NO_CACHE)


def attachment(content: str, media: str, name: str) -> Response:
    return Response(content, media_type=media, headers={**NO_CACHE, "Content-Disposition": f'attachment; filename="{name}"'})


def allow(user: str, capability: str) -> None:
    require_permission(user, capability, NODE)


@admin_routes.get("/status", openapi_extra={"x-nuxiva-capabilities": READ})
async def status(user: str = Depends(require_admin)):
    allow(user, "lab.read")
    return json_response({"native": lab.native_ready(), "max_active": MAX_ACTIVE, "active": runner.active(), "max_cases": MAX_CASES,
                          "max_concurrency": MAX_CONCURRENCY, "backends": list(store.BACKENDS)})


@admin_routes.get("/template", openapi_extra={"x-nuxiva-capabilities": READ})
async def template(user: str = Depends(require_admin)):
    allow(user, "lab.read")
    return json_response({"scenarios": lab.TEMPLATE})


@admin_routes.get("/datasets", openapi_extra={"x-nuxiva-capabilities": READ})
async def datasets(user: str = Depends(require_admin)):
    allow(user, "lab.read")
    return json_response({"datasets": store.list_datasets()})


@admin_routes.post("/datasets/inspect", openapi_extra={"x-nuxiva-capabilities": READ})
async def inspect(body: DatasetBody, user: str = Depends(require_admin)):
    allow(user, "lab.read")
    return json_response(lab.inspect(body.scenarios))


@admin_routes.get("/datasets/{dataset_id}", openapi_extra={"x-nuxiva-capabilities": READ})
async def dataset(dataset_id: str, user: str = Depends(require_admin)):
    allow(user, "lab.read")
    return json_response({"id": dataset_id, **store.load_dataset(dataset_id)})


@admin_routes.put("/datasets/{dataset_id}", openapi_extra={"x-nuxiva-capabilities": EDIT})
async def save_dataset(dataset_id: str, body: DatasetBody, user: str = Depends(require_admin)):
    allow(user, "lab.edit")
    summary = lab.inspect(body.scenarios)
    record = store.save_dataset(dataset_id, body.name, body.scenarios, summary)
    return json_response({"id": dataset_id, "name": record["name"], "summary": summary})


@admin_routes.delete("/datasets/{dataset_id}", openapi_extra={"x-nuxiva-capabilities": EDIT})
async def delete_dataset(dataset_id: str, user: str = Depends(require_admin)):
    allow(user, "lab.edit")
    store.delete_dataset(dataset_id)
    return json_response({"deleted": dataset_id})


@admin_routes.get("/datasets/{dataset_id}/export", openapi_extra={"x-nuxiva-capabilities": READ})
async def export_dataset(dataset_id: str, user: str = Depends(require_admin)):
    allow(user, "lab.read")
    record = store.load_dataset(dataset_id)
    return attachment(json.dumps(record["scenarios"], ensure_ascii=False, indent=1), "application/json", f"{dataset_id}.json")


@admin_routes.get("/profiles", openapi_extra={"x-nuxiva-capabilities": READ})
async def profiles(user: str = Depends(require_admin)):
    allow(user, "lab.read")
    return json_response({"profiles": [{"id": key, **value} for key, value in sorted(store.profiles().items())]})


@admin_routes.put("/profiles/{profile_id}", openapi_extra={"x-nuxiva-capabilities": EDIT})
async def save_profile(profile_id: str, body: ProfileBody, user: str = Depends(require_admin)):
    allow(user, "lab.edit")
    store.slug(profile_id)
    lab.check_endpoint(body.base_url)
    current = store.profiles()
    current[profile_id] = {"name": store.clean_name(body.name), "backend": body.backend, "base_url": body.base_url,
                           "model": store.valid_model(body.model), "timeout_seconds": body.timeout_seconds}
    store.save_profiles(current)
    return json_response({"id": profile_id, **current[profile_id]})


@admin_routes.delete("/profiles/{profile_id}", openapi_extra={"x-nuxiva-capabilities": EDIT})
async def delete_profile(profile_id: str, user: str = Depends(require_admin)):
    allow(user, "lab.edit")
    current = store.profiles()
    current.pop(store.slug(profile_id), None)
    store.save_profiles(current)
    return json_response({"deleted": profile_id})


@admin_routes.get("/runs", openapi_extra={"x-nuxiva-capabilities": READ})
async def runs(user: str = Depends(require_admin)):
    allow(user, "lab.read")
    runner.recover()
    return json_response({"runs": store.list_runs()})


@admin_routes.post("/runs", openapi_extra={"x-nuxiva-capabilities": RUN})
async def start_run(body: RunBody, user: str = Depends(require_admin)):
    allow(user, "lab.run")
    store.prune_runs()
    spec = {**body.model_dump(exclude={"key"}), "model": store.valid_model(body.model)}
    key = body.key.get_secret_value() if body.key else None
    return json_response(await runner.start(user, spec, key))


@admin_routes.get("/runs/{run_id}", openapi_extra={"x-nuxiva-capabilities": READ})
async def run(run_id: str, user: str = Depends(require_admin)):
    allow(user, "lab.read")
    return json_response(store.load_run(run_id))


@admin_routes.post("/runs/{run_id}/cancel", openapi_extra={"x-nuxiva-capabilities": RUN})
async def cancel_run(run_id: str, user: str = Depends(require_admin)):
    allow(user, "lab.run")
    store.load_run(run_id)
    runner.cancel(run_id)
    return json_response({"cancelling": run_id})


@admin_routes.delete("/runs/{run_id}", openapi_extra={"x-nuxiva-capabilities": RUN})
async def delete_run(run_id: str, user: str = Depends(require_admin)):
    allow(user, "lab.run")
    if store.load_run(run_id).get("state") not in store.FINAL_STATES:
        runner.cancel(run_id)
    store.delete_run(run_id)
    return json_response({"deleted": run_id})


def scenarios_of(meta: dict) -> list:
    return store.load_dataset(meta["dataset"])["scenarios"]


@admin_routes.get("/runs/{run_id}/report", openapi_extra={"x-nuxiva-capabilities": READ})
async def report(run_id: str, user: str = Depends(require_admin)):
    allow(user, "lab.read")
    meta = store.load_run(run_id)
    text = store.outcomes_text(run_id)
    return json_response({"run": meta, "report": lab.report(scenarios_of(meta), text) if text.strip() else None})


@admin_routes.get("/runs/{run_id}/rows", openapi_extra={"x-nuxiva-capabilities": READ})
async def rows(run_id: str, only: Literal["all", "failed", "wrong"] = "all", lang: str = Query("", max_length=3),
               offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), user: str = Depends(require_admin)):
    allow(user, "lab.read")
    meta = store.load_run(run_id)
    table = lab.rows(scenarios_of(meta), store.outcomes_text(run_id))
    if lang:
        table = [row for row in table if row["lang"] == lang]
    if only == "failed":
        table = [row for row in table if not row["success"]]
    elif only == "wrong":
        table = [row for row in table if row["wrong_action"]]
    return json_response({"total": len(table), "rows": table[offset: offset + limit]})


@admin_routes.get("/runs/{run_id}/download", openapi_extra={"x-nuxiva-capabilities": READ})
async def download(run_id: str, kind: Literal["outcomes", "report", "csv"] = "outcomes", user: str = Depends(require_admin)):
    allow(user, "lab.read")
    meta = store.load_run(run_id)
    text = store.outcomes_text(run_id)
    if kind == "outcomes":
        return attachment(text, "application/x-ndjson", f"nuxiva-lab-{run_id}.jsonl")
    if kind == "csv":
        return attachment(lab.to_csv(lab.rows(scenarios_of(meta), text)), "text/csv", f"nuxiva-lab-{run_id}.csv")
    payload = {"run": meta, "report": lab.report(scenarios_of(meta), text) if text.strip() else None}
    return attachment(json.dumps(payload, ensure_ascii=False, indent=1), "application/json", f"nuxiva-lab-{run_id}.json")
