from functools import partial

from features.agent.registry import tool
from features.devstudio import publish, runner, starters, workspace
from features.devstudio.workspace import DevError

dev_tool = partial(tool, agent="devstudio")


def _failed(exc: Exception) -> str:
    return f"ERRORE: {exc}"


@dev_tool("dev_new", "crea un nuovo progetto software con una struttura di partenza funzionante (sito statico, app Python da riga di comando, "
          "servizio FastAPI, app Node, app React con Vite) nella cartella condivisa del codice",
          {"name": "nome del progetto (lettere minuscole, numeri, trattini)", "kind": "static_site, python_cli, fastapi_service, node_cli o react_vite"})
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
