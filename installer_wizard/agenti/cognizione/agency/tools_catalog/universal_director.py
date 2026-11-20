import json

from agenti.agency.tools import Context, Tool, _text
from agenti.agency.universal_resolver import universal_resolver


async def _universal_autonomous_resolve(ctx: Context, args: dict) -> str:
    query = _text(args, "request", 1000)
    out_dir = str(args.get("workspace_dir") or "/tmp/nuxiva_resolutions").strip()

    plan = universal_resolver.resolve_any_request(query, workspace_dir=out_dir)
    res = plan.to_dict()

    if hasattr(ctx, "written"):
        for art in res.get("generated_artifacts", []):
            p = art.get("artifact_path")
            if p and p not in ctx.written:
                ctx.written.append(p)

    return json.dumps(res, ensure_ascii=False)


TOOLS = {
    "universal_autonomous_resolve": Tool(
        name="universal_autonomous_resolve",
        description="Risolve autonomamente qualsiasi richiesta al mondo (CAD 3D, taglio laser, siti web, audio/video, IoT, software) tramite deduzione ontologica, cascata di acquisizione/generazione a 4 livelli e pair programming.",
        args={"request": "string", "workspace_dir": "optional string"},
        capability="execute",
        run=_universal_autonomous_resolve,
    ),
}
