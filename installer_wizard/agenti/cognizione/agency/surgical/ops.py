import json
import native_core
from agenti.agency import workspace
from agenti.agency.client import AgencyUnavailable, client

PATH_LIMIT = 240
QUERY_LIMIT = 200
MAX_RANGE_LINES = 800


def _rust_core():
    cls = native_core.symbol("RustAgencyCore")
    if cls is not None:
        try:
            return cls()
        except Exception:
            return None
    return None


def _require_str(args: dict, key: str, limit: int) -> str:
    value = args.get(key, "")
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"argument '{key}' must be a non-empty string of at most {limit} characters")
    return value.strip()


def _require_int(args: dict, key: str, default: int) -> int:
    raw = args.get(key, default)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise ValueError(f"argument '{key}' must be a positive integer")
    return raw


def _format_outline(outline: dict) -> str:
    symbols = outline.get("symbols") or []
    total = outline.get("total_lines", 0)
    lang = outline.get("language", "text")
    header = f"{outline.get('path', '')} ({lang}, {total} lines)"
    if not symbols:
        return f"{header}\n(no structural symbols found)"
    rows = [header]
    for s in symbols[:200]:
        rows.append(f"  [{s['kind']}] {s['name']} (L{s['start_line']}-L{s['end_line']}): {s['signature']}")
    return "\n".join(rows)


async def view_outline(ctx, args: dict) -> str:
    path = _require_str(args, "path", PATH_LIMIT)
    fields = {"project": ctx.project_id, "path": path}
    if ctx.worker:
        fields["worker"] = ctx.worker
        fields["generation"] = ctx.generation
    try:
        res = await client.call("code_outline", **fields)
        return _format_outline(res["outline"])
    except AgencyUnavailable:
        body = workspace.read(ctx.folder, path, workspace.FILE_LIMIT)
        if not body:
            return "(file not found or empty)"
        core = _rust_core()
        if core is not None:
            outline = json.loads(core.outline_source_json(path, body))
            outline["path"] = path
            return _format_outline(outline)
        lines = body.splitlines()
        return f"{path} ({len(lines)} lines)"


async def search_symbols(ctx, args: dict) -> str:
    query = _require_str(args, "query", QUERY_LIMIT)
    fields = {"project": ctx.project_id, "query": query, "limit": 50}
    if ctx.worker:
        fields["worker"] = ctx.worker
        fields["generation"] = ctx.generation
    res = await client.call("code_symbols", **fields)
    symbols = res.get("symbols") or []
    if not symbols:
        return "(no matching symbols)"
    return "\n".join(
        f"{s['path']}:L{s['start_line']}-L{s['end_line']} [{s['kind']}] {s['name']} — {s['signature']}"
        for s in symbols
    )


async def view_range(ctx, args: dict) -> str:
    path = _require_str(args, "path", PATH_LIMIT)
    start_line = _require_int(args, "start_line", 1)
    end_line = _require_int(args, "end_line", min(start_line + 199, start_line + MAX_RANGE_LINES - 1))
    if end_line < start_line or (end_line - start_line + 1) > MAX_RANGE_LINES:
        raise ValueError(f"line range must satisfy start_line <= end_line and span at most {MAX_RANGE_LINES} lines")
    fields = {
        "project": ctx.project_id,
        "path": path,
        "start_line": start_line,
        "end_line": end_line,
    }
    if ctx.worker:
        fields["worker"] = ctx.worker
        fields["generation"] = ctx.generation
    try:
        res = await client.call("code_view_range", **fields)
        view = res["view"]
    except AgencyUnavailable:
        body = workspace.read(ctx.folder, path, workspace.FILE_LIMIT)
        if not body:
            return "(file not found or empty)"
        core = _rust_core()
        if core is not None:
            view = json.loads(core.view_line_range_json(body, start_line, end_line))
            view["path"] = path
        else:
            all_lines = body.splitlines()
            sliced = all_lines[start_line - 1:end_line]
            numbered = "\n".join(f"{start_line + idx}: {line}" for idx, line in enumerate(sliced))
            view = {
                "path": path,
                "start_line": start_line,
                "end_line": start_line + len(sliced) - 1,
                "total_lines": len(all_lines),
                "content": numbered,
            }
    return f"{view.get('path', path)} (L{view['start_line']}-L{view['end_line']} of {view['total_lines']})\n{view['content']}"


def _normalize_chunks(args: dict) -> list[dict]:
    raw_chunks = args.get("chunks")
    if isinstance(raw_chunks, list) and raw_chunks:
        chunks = []
        for item in raw_chunks:
            if not isinstance(item, dict):
                raise ValueError("each chunk must be an object")
            chunks.append({
                "start_line": _require_int(item, "start_line", 1),
                "end_line": _require_int(item, "end_line", 1),
                "target_content": str(item.get("target_content", "")),
                "replacement_content": str(item.get("replacement_content", "")),
                "allow_multiple": bool(item.get("allow_multiple", False)),
            })
        return chunks
    start_line = _require_int(args, "start_line", 1)
    end_line = _require_int(args, "end_line", start_line)
    target = args.get("target_content")
    replacement = args.get("replacement_content")
    if not isinstance(target, str) or not target:
        raise ValueError("argument 'target_content' must be a non-empty string")
    if not isinstance(replacement, str):
        raise ValueError("argument 'replacement_content' must be a string")
    return [{
        "start_line": start_line,
        "end_line": end_line,
        "target_content": target,
        "replacement_content": replacement,
        "allow_multiple": bool(args.get("allow_multiple", False)),
    }]


async def replace_content(ctx, args: dict) -> str:
    path = _require_str(args, "path", PATH_LIMIT)
    chunks = _normalize_chunks(args)
    fields = {
        "project": ctx.project_id,
        "path": path,
        "chunks": chunks,
    }
    if ctx.worker:
        fields["worker"] = ctx.worker
        fields["generation"] = ctx.generation
    try:
        res = await client.call("code_patch", **fields)
        outcome = res["patch"]
    except AgencyUnavailable:
        body = workspace.read(ctx.folder, path, workspace.FILE_LIMIT)
        if not body:
            raise ValueError(f"file '{path}' not found or empty")
        core = _rust_core()
        if core is None:
            raise ValueError("RustAgencyCore required for local surgical patch")
        outcome = json.loads(core.apply_surgical_patches_json(body, json.dumps(chunks)))
        workspace.write(ctx.folder, path, outcome["updated_content"])
    if path not in ctx.written:
        ctx.written.append(path)
    return (
        f"patched {path}: applied {outcome['applied_chunks']} chunk(s), "
        f"lines {outcome['old_lines']} -> {outcome['new_lines']}, sha256={outcome['sha256_after'][:12]}"
    )
