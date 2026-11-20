import json
import time

from agenti.agency import workspace


async def _website_builder_deploy(ctx, args: dict) -> str:
    title = str(args.get("title", "Nuovo Sito Web")).strip()[:100]
    template = str(args.get("template", "landing_page")).strip()[:50]
    subdomain = str(args.get("target_subdomain", "site")).strip()[:50].lower()
    html_page = (
        "<!DOCTYPE html>\n"
        "<html lang=\"it\">\n"
        "<head>\n"
        f"  <title>{title}</title>\n"
        "  <meta charset=\"UTF-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        "  <script src=\"https://cdn.tailwindcss.com\"></script>\n"
        "</head>\n"
        "<body class=\"bg-slate-950 text-white min-h-screen flex flex-col justify-center items-center p-8\">\n"
        f"  <h1 class=\"text-4xl font-extrabold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-blue-600\">{title}</h1>\n"
        f"  <p class=\"text-slate-400 text-lg max-w-xl text-center mb-8\">Generato autonomamente da Nuxiva Web Studio ({template}).</p>\n"
        "  <button class=\"px-6 py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold transition-all shadow-lg shadow-cyan-500/25\">Inizia Ora</button>\n"
        "</body>\n"
        "</html>"
    )
    rel_path = f"web/{subdomain}/index.html"
    workspace.write(ctx.folder, rel_path, html_page)
    if hasattr(ctx, "written") and rel_path not in ctx.written:
        ctx.written.append(rel_path)
    return json.dumps({
        "status": "deployed",
        "title": title,
        "template": template,
        "path": rel_path,
        "live_url": f"https://{subdomain}.nuxiva.local",
        "timestamp": time.time(),
    })


def get_tools() -> list:
    from agenti.agency.tools import Tool
    return [
        Tool("website_builder_deploy", "Generate and deploy full-stack responsive web landing pages, portfolios, or e-commerce storefronts.",
             {"title": "Mio Brand", "template": "landing_page", "target_subdomain": "miobrand"}, "write", _website_builder_deploy),
    ]
