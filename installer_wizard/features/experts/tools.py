import re
import shutil
import unicodedata
from datetime import date

from features.actions.common import sh
from features.agent.registry import tool
from features.experts import live

OWNER = "experts"
UNIT_RE = re.compile(r"^[A-Za-z0-9@._:-]{1,80}$")
LEVELS = ("emerg", "alert", "crit", "err", "warning", "notice", "info")
GIB = 1024 ** 3


def _flat(text: str) -> str:
    return unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower().strip()


def _unit(name: str) -> str:
    value = str(name or "").strip()
    if not UNIT_RE.fullmatch(value) or value.startswith("-"):
        raise ValueError("nome del servizio non valido")
    return value


@tool("debian_status", "stato reale del server Debian: sistema, kernel, uptime, carico, memoria, disco, temperatura, servizi falliti e aggiornamenti",
      {}, agent=OWNER)
async def debian_status() -> str:
    d = await live.debian()
    mem, disk = d["memory"], d["disk"]
    lines = [f"sistema: {d['os']} · kernel {d['kernel']} · host {d['host']}",
             f"acceso da {d['uptime_s'] // 3600} h {(d['uptime_s'] % 3600) // 60} min",
             f"carico: {' '.join(map(str, d['load'])) or 'n/d'} su {d['cpus']} CPU",
             f"memoria: {mem['used'] / GIB:.1f} di {mem['total'] / GIB:.1f} GiB",
             f"disco /: {disk['used'] / GIB:.1f} di {disk['total'] / GIB:.1f} GiB"]
    if d["temperature"] is not None:
        lines.append(f"temperatura massima: {d['temperature']} °C")
    failed = d["failed_units"]
    lines.append("servizi falliti: " + ("n/d (systemd assente)" if failed is None else ", ".join(failed) or "nessuno"))
    updates = d["updates"]
    lines.append("aggiornamenti: " + ("n/d (apt assente)" if updates is None else
                                      f"{updates['count']} disponibili, {updates['security']} di sicurezza"))
    return "\n".join(lines)


@tool("debian_logs", "ultime righe del registro di sistema (journalctl) filtrate per gravità e, se indicato, per servizio",
      {"unit": "servizio systemd (facoltativo)", "level": "err, warning, notice o info", "lines": "numero di righe (1-200)"}, agent=OWNER)
async def debian_logs(unit: str = "", level: str = "err", lines: int = 40) -> str:
    if not shutil.which("journalctl"):
        return "journalctl non disponibile su questo sistema"
    level = level if level in LEVELS else "err"
    count = max(1, min(200, int(lines or 40)))
    cmd = ["journalctl", "--no-pager", "-o", "short-iso", "-p", level, "-n", str(count)]
    if unit:
        cmd += ["-u", _unit(unit)]
    code, out = await sh(*cmd, timeout=20)
    return f"codice di uscita {code}\n{out[-5000:] or 'nessuna riga'}"


@tool("debian_service", "stato dettagliato di un servizio systemd (sola lettura): attivo, errori recenti, dipendenze",
      {"unit": "nome del servizio, per esempio ssh o nginx"}, agent=OWNER)
async def debian_service(unit: str) -> str:
    if not shutil.which("systemctl"):
        return "systemctl non disponibile su questo sistema"
    code, out = await sh("systemctl", "status", _unit(unit), "--no-pager", "-n", "20", timeout=15)
    return f"codice di uscita {code}\n{out[-5000:]}"


@tool("apt_upgradable", "pacchetti Debian aggiornabili, con quanti sono aggiornamenti di sicurezza", {}, agent=OWNER)
async def apt_upgradable() -> str:
    data = await live.upgradable()
    if data is None:
        return "apt non disponibile su questo sistema"
    if not data["count"]:
        return "il sistema è aggiornato"
    return f"{data['count']} pacchetti aggiornabili ({data['security']} di sicurezza): " + ", ".join(data["packages"])


def _match_line(m: dict) -> str:
    h, a = m["home"], m["away"]
    score = f"{h['score']}-{a['score']}" if m["state"] != "pre" else "vs"
    when = m["clock"] if m["state"] == "in" else ("finale" if m["state"] == "post" else m["start"])
    goals = "; ".join(f"{g['minute']} {g['player']}" for g in m["events"] if g["kind"] == "goal")
    return f"- {m['league_name']}: {h['name']} {score} {a['name']} ({when})" + (f" · gol: {goals}" if goals else "")


@tool("football_scores", "risultati e partite di calcio di un campionato in un giorno (in diretta, finite o in programma)",
      {"league": "codice campionato, per esempio ita.1, uefa.champions, eng.1", "day": "data AAAA-MM-GG (facoltativa, oggi se vuota)"},
      agent=OWNER)
async def football_scores(league: str = "ita.1", day: str = "") -> str:
    from features.sports import football
    when = date.fromisoformat(day) if day else None
    matches = await football.scoreboard(football.check_league(league), when)
    return "\n".join(_match_line(m) for m in matches) or "nessuna partita in quel giorno"


@tool("football_table", "classifica aggiornata di un campionato di calcio", {"league": "codice campionato, per esempio ita.1"}, agent=OWNER)
async def football_table(league: str = "ita.1") -> str:
    from features.sports import football
    rows = await football.standings(football.check_league(league))
    return "\n".join(f"{r['rank']}. {r['name']} {r['points']} pt (G{r['played']} V{r['won']} N{r['drawn']} P{r['lost']} DR{r['diff']:+d})"
                     for r in rows) or "classifica non disponibile"


@tool("football_team", "ultimi risultati e prossime partite di una squadra di calcio", {"team": "nome della squadra", "league": "codice campionato (facoltativo, ita.1 se vuoto)"},
      agent=OWNER)
async def football_team(team: str, league: str = "ita.1") -> str:
    from features.sports import football
    code = football.check_league(league or "ita.1")
    wanted = _flat(team)
    if len(wanted) < 2:
        raise ValueError("nome della squadra non valido")
    found = next((t for t in await football.teams(code) if wanted in _flat(t["name"]) or wanted in _flat(t["short"])), None)
    if not found:
        return f"squadra «{team}» non trovata in {code}"
    results = (await football.team_results(code, found["id"]))[-3:]
    fixtures = football.upcoming(await football.team_fixtures(code, found["id"]))[:3]
    lines = [f"{found['name']}", "ultimi risultati:"] + [_match_line(m) for m in results]
    lines += ["prossime partite:"] + [_match_line(m) for m in fixtures]
    return "\n".join(lines)


@tool("expert_list", "elenca gli esperti della squadra con nome, ruolo e specialità", {}, agent=OWNER)
async def expert_list() -> str:
    from features.experts.store import experts
    rows = [f"- {e.id}: {e.name}, {e.role} — {e.specialty}" + ("" if e.enabled else " [spento]") for e in experts.all()]
    return "\n".join(rows) or "nessun esperto: se ne può creare uno con expert_create"


@tool("expert_ask", "passa una domanda all'esperto giusto e restituisce la sua risposta verificata con i suoi strumenti",
      {"expert": "id o nome dell'esperto", "question": "domanda completa"}, agent=OWNER)
async def expert_ask(expert: str, question: str) -> str:
    from features.experts import service
    target = service.resolve(expert)
    reply = await service.ask(target.id, question, "it", origin="nuxiva")
    return f"{target.name} ({target.role}): {reply['text']}"


@tool("expert_create", "crea un nuovo esperto da un modello (debian, football) oppure da nome, ruolo e specialità",
      {"template": "debian o football (facoltativo)", "name": "nome", "role": "ruolo", "specialty": "specialità"}, agent=OWNER)
async def expert_create(template: str = "", name: str = "", role: str = "", specialty: str = "") -> str:
    from features.experts import service
    body = {"template": template} if template else {"name": name, "role": role, "specialty": specialty}
    expert = service.create(body, "it", "nuxiva")
    return f"esperto creato: {expert.name}, {expert.role} ({expert.id})"
