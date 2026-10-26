from functools import partial

from features.agent.registry import tool
from features.devstudio import builder, plan as plans, publish, runner, starters, workspace
from features.devstudio.workspace import DevError

dev_tool = partial(tool, agent="devstudio")


def _failed(exc: Exception) -> str:
    return f"ERRORE: {exc}"


@dev_tool("dev_new", "crea un nuovo progetto software con una struttura di partenza funzionante (sito statico, sito PHP modulare, app Python da riga di comando, "
          "servizio FastAPI, app Node, app React con Vite) nella cartella condivisa del codice",
          {"name": "nome del progetto (lettere minuscole, numeri, trattini)", "kind": "static_site, php_site, python_cli, fastapi_service, node_cli o react_vite"})
async def dev_new(name: str, kind: str = "static_site") -> str:
    kind = str(kind or "static_site").strip().lower()
    if kind not in starters.KINDS:
        return _failed(DevError(f"tipo sconosciuto, scegli tra: {', '.join(starters.KINDS)}"))
    try:
        folder = workspace.project_dir(name, must_exist=False)
        if folder.exists():
            return _failed(DevError(f"il progetto «{folder.name}» esiste già: usa dev_tree e dev_write per modificarlo"))
        folder.mkdir(parents=True)
        for relative, content in starters.scaffold(kind, folder.name).items():
            workspace.write(folder, relative, content)
    except DevError as exc:
        return _failed(exc)
    return f"progetto {folder.name} creato ({kind}) con {len(workspace.files(folder))} file; usa dev_tree per vederli"


@dev_tool("dev_tree", "elenca i file di un progetto software, oppure i progetti esistenti se non indichi il nome", {"project": "nome del progetto (facoltativo)"})
async def dev_tree(project: str = "") -> str:
    if not str(project or "").strip():
        return "\n".join(workspace.names()) or "nessun progetto: creane uno con dev_new"
    try:
        return "\n".join(workspace.tree(workspace.project_dir(project))) or "progetto vuoto"
    except DevError as exc:
        return _failed(exc)


@dev_tool("dev_read", "legge un file di un progetto software", {"project": "nome del progetto", "path": "percorso relativo del file"})
async def dev_read(project: str, path: str) -> str:
    try:
        return workspace.read(workspace.project_dir(project), path)
    except DevError as exc:
        return _failed(exc)


@dev_tool("dev_write", "scrive o sostituisce un file in un progetto software (solo dentro il progetto, mai fuori)",
          {"project": "nome del progetto", "path": "percorso relativo del file", "content": "contenuto completo del file"})
async def dev_write(project: str, path: str, content: str) -> str:
    try:
        folder = workspace.project_dir(project)
        target = workspace.write(folder, path, content)
    except DevError as exc:
        return _failed(exc)
    return f"scritto {target.relative_to(folder).as_posix()} ({target.stat().st_size} B)"


@dev_tool("dev_run", "esegue in isolamento, senza rete e con limiti di tempo e risorse, un controllo del progetto: python_tests, python_compile, node_tests, "
          "python_run o node_run (con il file da avviare); restituisce uscita e output reali",
          {"project": "nome del progetto", "check": "python_tests, python_compile, node_tests, python_run o node_run", "entry": "file da avviare (solo per *_run)"},
          confirm=True)
async def dev_run(project: str, check: str, entry: str = "") -> str:
    try:
        folder = workspace.project_dir(project)
        code, output = await runner.run(str(check).strip().lower(), folder, str(entry or ""))
    except DevError as exc:
        return _failed(exc)
    verdict = "riuscito" if code == 0 else f"fallito (codice {code})"
    return f"{check}: {verdict}\n{output.strip() or '(nessun output)'}"


@dev_tool("dev_publish", "pubblica un sito del progetto (con index.html) sulla rete di casa e restituisce l'indirizzo", {"project": "nome del progetto"})
async def dev_publish(project: str) -> str:
    try:
        return f"pubblicato: {publish.publish(project)}"
    except DevError as exc:
        return _failed(exc)


@dev_tool("dev_plan", "progetta un progetto complesso: crea il piano completo dei file (struttura per funzionalità, sicurezza, lingue) e lo salva per riprenderlo anche dopo giorni",
          {"project": "nome di un progetto già creato con dev_new", "goal": "cosa deve fare il sito o l'app, con tutti i requisiti", "stack": "tecnologie volute, per esempio php e javascript (facoltativo)"})
async def dev_plan(project: str, goal: str, stack: str = "") -> str:
    try:
        plan = await builder.make_plan(project, goal, stack)
    except DevError as exc:
        return _failed(exc)
    return f"piano salvato: {len(plan.items)} file ({plan.stack}); usa dev_build per scriverli\n" + "\n".join(f"- {i.path}: {i.purpose}" for i in plan.items)


@dev_tool("dev_build", "scrive i prossimi file del piano, uno alla volta con tutto il contesto, rispettando le regole di qualità; richiamalo finché non restano file in attesa",
          {"project": "nome del progetto", "count": "quanti file scrivere ora, da 1 a 4"})
async def dev_build(project: str, count: int = 3) -> str:
    try:
        plan, report = await builder.build_next(project, int(count or 3))
    except (DevError, ValueError) as exc:
        return _failed(exc)
    counts = plan.counts()
    return "\n".join(report) + f"\nstato: {counts['done']} scritti, {counts['pending']} in attesa, {counts['failed']} da rivedere"


@dev_tool("dev_status", "mostra a che punto è un progetto: file scritti, in attesa e da rivedere; serve per riprendere il lavoro dopo giorni", {"project": "nome del progetto"})
async def dev_status(project: str) -> str:
    try:
        plan = plans.load(project)
    except DevError as exc:
        return _failed(exc)
    counts = plan.counts()
    rows = [f"{i.status}: {i.path}" + (f" ({i.note})" if i.note else "") for i in plan.items]
    return f"{plan.project} · {plan.stack} · {counts['done']} scritti, {counts['pending']} in attesa, {counts['failed']} da rivedere\nobiettivo: {plan.goal[:300]}\n" + "\n".join(rows)
