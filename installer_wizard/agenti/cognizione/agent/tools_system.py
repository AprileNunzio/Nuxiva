import re

import httpx

from agenti.actions.common import sh
from agenti.agent import web_mcp
from agenti.agent.paths import FILES
from agenti.agent import host_readonly, shell_sandbox
from agenti.agent.registry import tool

DANGER = re.compile(r"\brm\s+-[a-z]*r[a-z]*f?\s+/(\s|$)|\bmkfs|\bdd\s+if=|:\(\)\s*\{|\bshutdown\b|\bpoweroff\b"
                    r"|\bchmod\s+-R\s+777\s+/(\s|$)|>\s*/dev/sd", re.I)


def _risky(args: dict) -> bool:
    return host_readonly.parse(str(args.get("command", ""))) is None


@tool("run_command", "esegue un comando di terminale (bash, 2 minuti al massimo) in un ambiente isolato e ne restituisce l'output; "
      "solo le letture dello stato del server girano sul server", {"command": "comando bash"}, confirm=_risky, full_only=True)
async def run_command(command: str) -> str:
    if DANGER.search(command):
        raise PermissionError("comando distruttivo bloccato: non lo eseguo")
    argv = host_readonly.parse(command)
    if argv is not None:
        code, out = await host_readonly.run(argv)
        return f"codice di uscita {code}\n{out[-5000:]}"
    if shell_sandbox.mode() == "sandbox":
        return await shell_sandbox.run(command)
    FILES.mkdir(parents=True, exist_ok=True)
    code, out = await sh("bash", "-lc", f"cd {FILES} && {command}", timeout=120)
    return f"codice di uscita {code}\n{out[-5000:]}"


@tool("http_get", "scarica il testo di una pagina web o di un'API pubblica", {"url": "indirizzo http(s)"}, consent=web_mcp.consent("http_get"))
async def http_get(url: str) -> str:
    if web_mcp.active():
        return await web_mcp.call("http_get", url=url)
    if not re.match(r"^https?://", url):
        raise ValueError("indirizzo non valido")
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": "Nuxiva/3"})
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return f"HTTP {r.status_code}\n" + re.sub(r"\s+", " ", text).strip()[:5000]
