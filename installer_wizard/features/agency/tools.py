import json
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from features.agency import feature, workspace
from features.agency.client import AgencyRejected, client
from features.agency.forge import sandbox, smith
from features.agency.forge.guard import ForgeRejected
from features.agency.forge.registry import registry
from features.devstudio import runner as checks
from features.devstudio.workspace import DevError

OBSERVATION = 4000
CONTENT_LIMIT = workspace.FILE_LIMIT
PATH_LIMIT = 240
QUERY_LIMIT = 200
FORGES_PER_TASK = 2


class ToolError(ValueError):
    pass


@dataclass
class Context:
    project_id: str
    folder: str
    task: str = ""
    tokens: int = 0
    forged: list[str] = field(default_factory=list)
    forge_attempts: int = 0
    written: list[str] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args: dict
    capability: str
    run: Callable[[Context, dict], Awaitable[str]]


def _text(args: dict, key: str, limit: int, required: bool = True) -> str:
    value = args.get(key, "")
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > limit:
        raise ToolError(f"argument '{key}' must be a string of at most {limit} characters")
    return value


async def _list_files(ctx: Context, args: dict) -> str:
    files = (await client.call("code_files", project=ctx.project_id))["files"]
    lines = [f"{f['path']} ({f['bytes']} B, {f['language']})" for f in files[:400]]
    return "\n".join(lines) or "(empty project)"


async def _search(ctx: Context, args: dict) -> str:
    query = _text(args, "query", QUERY_LIMIT)
    hits = (await client.call("code_search", project=ctx.project_id, query=query, limit=40))["hits"]
    return "\n".join(f"{h['path']}:{h['line']}: {h['text']}" for h in hits) or "(no match)"


async def _read(ctx: Context, args: dict) -> str:
    body = workspace.read(ctx.folder, _text(args, "path", PATH_LIMIT), 20000)
    return body or "(file not found or empty)"


async def _write(ctx: Context, args: dict) -> str:
    path = _text(args, "path", PATH_LIMIT)
    content = _text(args, "content", CONTENT_LIMIT, required=False)
    workspace.write(ctx.folder, path, content)
    if path not in ctx.written:
        ctx.written.append(path)
    return f"written {path} ({len(content.encode())} bytes)"


async def _check(ctx: Context, args: dict) -> str:
    name = _text(args, "check", 40)
    entry = _text(args, "entry", PATH_LIMIT, required=False)
    try:
        code, output = await checks.run(name, workspace.folder(ctx.folder), entry)
    except DevError as exc:
        return f"check not run: {exc}"
    ctx.checks.append({"check": name, "entry": entry, "exit_code": code, "output": output[-1500:]})
    return f"exit code {code}\n{output[-OBSERVATION:]}"


async def _forge(ctx: Context, args: dict) -> str:
    if not feature.forge_enabled():
        return "error: creating tools is disabled in the settings"
    if ctx.forge_attempts >= FORGES_PER_TASK:
        return f"error: at most {FORGES_PER_TASK} new tools per task"
    ctx.forge_attempts += 1
    try:
        tool, tokens = await smith.forge(args, {"project": ctx.project_id, "task": ctx.task})
    except ForgeRejected as exc:
        return f"error: tool not created ({exc})"
    ctx.forged.append(tool.name)
    ctx.tokens += tokens
    return f"created {tool.call_name}: {tool.description} args={json.dumps(tool.args, ensure_ascii=False)}"


async def _forged(ctx: Context, call_name: str, args: dict) -> str:
    tool = registry.by_call_name(call_name)
    if tool is None:
        return f"error: unknown tool, use one of {', '.join(names())}"
    outcome = await sandbox.execute(tool.code, args)
    registry.record(tool.name, bool(outcome.get("ok")), str(outcome.get("error", "")))
    if not outcome.get("ok"):
        return f"error: {outcome.get('error')}"
    return json.dumps(outcome.get("result"), ensure_ascii=False, default=str)


TOOLS: dict[str, Tool] = {tool.name: tool for tool in (
    Tool("list_files", "List every file of the project with size and language.", {}, "read", _list_files),
    Tool("search_code", "Search the project code for words; returns file:line matches.", {"query": "words to find"}, "read", _search),
    Tool("read_file", "Read a project file (UTF-8, first 20000 characters).", {"path": "relative/path.ext"}, "read", _read),
    Tool("write_file", "Create or replace a project file with the full content.", {"path": "relative/path.ext", "content": "full file content"}, "write", _write),
    Tool("run_check", "Run a check in an offline sandbox: " + ", ".join(checks.names()) + ". 'entry' is the file for *_run checks.",
         {"check": "python_tests", "entry": "optional file"}, "execute", _check),
    Tool("forge_tool", "Create a new reusable pure-Python tool when none of the existing ones fits; it is tested in a "
         "sandbox and then callable as x_<name> by every agent.",
         {"name": "lowercase_identifier", "purpose": "what it must compute", "example": "an example input and output"},
         "forge", _forge),
)}


def names() -> list[str]:
    return [*TOOLS, *(t.call_name for t in registry.active())]


def manifest() -> list[dict]:
    builtin = [{"name": t.name, "description": t.description, "args": t.args} for t in TOOLS.values()
               if t.capability != "forge" or feature.forge_enabled()]
    return builtin + [{"name": t.call_name, "description": t.description, "args": t.args} for t in registry.active()]


async def call(ctx: Context, name, args) -> str:
    if not isinstance(args, dict):
        return "error: args must be an object"
    tool = TOOLS.get(name) if isinstance(name, str) else None
    try:
        if tool is None:
            return (await _forged(ctx, name, args))[:OBSERVATION]
        return (await tool.run(ctx, args))[:OBSERVATION]
    except ToolError as exc:
        return f"error: {exc}"
    except workspace.WorkspaceError as exc:
        return f"error: {exc}"
    except AgencyRejected as exc:
        return f"error: engine refused ({exc.code})"
    except sandbox.SandboxUnavailable as exc:
        return f"error: {exc}"
