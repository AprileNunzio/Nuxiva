import re
import shutil
import unicodedata
from datetime import date

from features.actions.common import sh
from features.agent.registry import tool
from features.experts import admin, live

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
    rows = [f"- {e.id}: {e.role} — {e.specialty}" + ("" if e.enabled else " [spento]") for e in experts.all()]
    return "\n".join(rows) or "nessun esperto: se ne può creare uno con expert_create"


@tool("expert_ask", "passa una domanda all'esperto giusto e restituisce la sua risposta verificata con i suoi strumenti",
      {"expert": "id o nome dell'esperto", "question": "domanda completa"}, agent=OWNER)
async def expert_ask(expert: str, question: str) -> str:
    from features.experts import service
    target = service.resolve(expert)
    reply = await service.ask(target.id, question, "it", origin="nuxiva")
    return f"{target.role}: {reply['text']}"


@tool("expert_create", "crea un nuovo esperto da un modello (debian, football) oppure da ruolo e specialità; gli esperti non hanno nomi di persona",
      {"template": "debian o football (facoltativo)", "role": "ruolo", "specialty": "specialità"}, agent=OWNER)
async def expert_create(template: str = "", role: str = "", specialty: str = "") -> str:
    from features.experts import service
    body = {"template": template} if template else {"role": role, "specialty": specialty}
    expert = service.create(body, "it", "nuxiva")
    return f"esperto creato: {expert.role} ({expert.id})"


@tool("apt_install", "installa uno o più pacchetti Debian con apt (non interattivo, mantiene i file di configurazione esistenti)",
      {"packages": "nomi dei pacchetti separati da spazio"}, agent=OWNER, confirm=True, precheck=admin.check_apt)
async def apt_install(packages: str) -> str:
    return await admin.apt_install(packages)


@tool("apt_remove", "rimuove pacchetti Debian, con purge opzionale per eliminare anche la configurazione",
      {"packages": "nomi dei pacchetti separati da spazio", "purge": "true per eliminare anche la configurazione"},
      agent=OWNER, confirm=True, precheck=admin.check_apt)
async def apt_remove(packages: str, purge: bool = False) -> str:
    return await admin.apt_install(packages, remove=True, purge=bool(purge))


@tool("apt_maintain", "manutenzione di apt: update, upgrade, full-upgrade, autoremove, clean oppure fix (ripara dipendenze rotte)",
      {"action": "update, upgrade, full-upgrade, autoremove, clean o fix"}, agent=OWNER, confirm=True, precheck=admin.check_apt)
async def apt_maintain(action: str) -> str:
    return await admin.apt_maintain(action)


@tool("apt_search", "cerca pacchetti Debian per nome o descrizione", {"query": "testo da cercare"}, agent=OWNER)
async def apt_search(query: str) -> str:
    return await admin.apt_find(query)


@tool("service_control", "controlla un servizio systemd: start, stop, restart, reload, enable, disable, mask, unmask, reset-failed",
      {"unit": "nome del servizio", "action": "start, stop, restart, reload, try-restart, enable, disable, enable --now, disable --now, mask, unmask o reset-failed"},
      agent=OWNER, confirm=True, precheck=admin.check_service)
async def service_control(unit: str, action: str) -> str:
    return await admin.service(unit, action)


@tool("power_control", "riavvia, spegne, ferma o sospende il server (con ritardo in minuti) oppure annulla uno spegnimento programmato",
      {"action": "reboot, poweroff, halt, suspend o cancel", "minutes": "minuti di attesa, da 1 a 1440 (1 se omesso)"},
      agent=OWNER, confirm=True, precheck=admin.check_power)
async def power_control(action: str, minutes: int = 1) -> str:
    return await admin.power(action, minutes)


@tool("ssh_exec", "esegue un comando su un altro computer via SSH con la chiave di Nuxiva (senza password, host nuovi accettati alla prima connessione)",
      {"host": "nome o indirizzo del computer", "command": "comando da eseguire", "user": "utente (root se omesso)",
       "port": "porta (22 se omessa)", "timeout": "secondi massimi (120 se omesso)"},
      agent=OWNER, confirm=admin.risky, precheck=admin.check_ssh)
async def ssh_exec(host: str, command: str, user: str = "root", port: int = 22, timeout: int = 120) -> str:
    return await admin.ssh(host, command, user, port, timeout)


@tool("ssh_public_key", "mostra la chiave pubblica SSH di Nuxiva da autorizzare sui computer da raggiungere (la crea se manca)",
      {}, agent=OWNER)
async def ssh_public_key() -> str:
    return await admin.ssh_public_key()


@tool("debian_shell", "esegue qualsiasi comando bash come amministratore sul server, senza limiti di tipo (fino a 1 ora); i comandi di sola lettura partono subito, gli altri chiedono conferma",
      {"command": "comando bash", "timeout": "secondi massimi (300 se omesso)", "workdir": "cartella di lavoro (facoltativa)"},
      agent=OWNER, confirm=admin.risky)
async def debian_shell(command: str, timeout: int = 300, workdir: str = "") -> str:
    return await admin.shell(command, timeout, workdir)


@tool("system_file_read", "legge un file di testo del sistema (percorso assoluto)", {"path": "percorso assoluto", "limit": "byte massimi"},
      agent=OWNER, precheck=admin.check_path)
async def system_file_read(path: str, limit: int = 20000) -> str:
    return admin.read_file(path, limit)


@tool("system_file_write", "scrive un file di testo del sistema (percorso assoluto), conservando una copia .bak dell'originale e i suoi permessi",
      {"path": "percorso assoluto", "content": "contenuto completo del file", "mode": "permessi ottali facoltativi, per esempio 644"},
      agent=OWNER, confirm=True, precheck=admin.check_path)
async def system_file_write(path: str, content: str, mode: str = "") -> str:
    return admin.write_file(path, content, mode)


@tool("debian_processes", "processi in esecuzione ordinati per uso di CPU o memoria", {"sort": "cpu o mem", "limit": "quanti (1-60)"}, agent=OWNER)
async def debian_processes(sort: str = "cpu", limit: int = 15) -> str:
    return await admin.processes(sort, limit)


@tool("process_kill", "invia un segnale a un processo (TERM, KILL, HUP, INT, STOP, CONT, USR1, USR2, QUIT)",
      {"pid": "numero del processo", "signal": "segnale (TERM se omesso)"}, agent=OWNER, confirm=True)
async def process_kill(pid: int, signal: str = "TERM") -> str:
    return await admin.kill(pid, signal)


@tool("debian_network", "interfacce, rotte e porte in ascolto del server", {}, agent=OWNER)
async def debian_network() -> str:
    return await admin.network()
