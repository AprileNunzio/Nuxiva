import re

from features.brain.llm import BrainUnavailable, generate

from features.devstudio import plan as plans
from features.devstudio import workspace
from features.devstudio.rules import COMMENT_MARKERS, RULES
from features.devstudio.workspace import DevError

MAX_LINES = 450
HARD_LINES = 500
CONTEXT_FILES = 6
CONTEXT_CHARS = 7000
FILE_TOKENS = 7000
PLAN_TOKENS = 3500
FENCE = re.compile(r"^```[A-Za-z0-9+_-]*\s*\n|\n```\s*$")
SYSTEM = ("Sei un Software Architect e Team Lead estremamente severo. Rispetta sempre queste direttive:\n" + RULES)

PLAN_PROMPT = """Progetta l'intero progetto richiesto come elenco ordinato di file, dalle fondamenta (configurazione, sicurezza, lingue, modelli) alle pagine.
Richiesta: {goal}
Stack: {stack}

Regole del piano:
- un file per responsabilità, nessun file oltre {lines} righe, quindi spezza le parti grandi in più file;
- ogni pagina o modulo in una propria cartella con vista, logica, stile e testi di traduzione (it ed en);
- includi gestione globale degli errori, sicurezza (CSRF, intestazioni, validazione), file di lingua, README breve e i punti di ingresso;
- al massimo {limit} file, percorsi relativi semplici (lettere, numeri, punto, trattino, sottolineatura).
Rispondi solo con JSON: {{"stack": "stack scelto", "files": [{{"path": "cartella/file.ext", "purpose": "cosa contiene, in una frase"}}]}}"""

FILE_PROMPT = """Progetto: {goal}
Stack: {stack}

Piano completo dei file:
{plan}

File già scritti che puoi usare come riferimento (coerenza di nomi, funzioni e chiavi):
{context}

Scrivi ora SOLO il contenuto completo del file «{path}» ({purpose}).
Nessuna spiegazione, nessun recinto markdown, nessun commento nel codice, massimo {lines} righe.{extra}"""


def _strip(text: str) -> str:
    return FENCE.sub("", str(text or "").strip()).strip("\n") + "\n"


def _commented(path: str, text: str) -> bool:
    markers = COMMENT_MARKERS.get("." + path.rsplit(".", 1)[-1].lower())
    if not markers:
        return False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#!") or stripped.startswith("<?php") or stripped.startswith("#[") or stripped.startswith("<!DOCTYPE"):
            continue
        if any(stripped.startswith(m) for m in markers):
            return True
    return False


def _context(folder, done: list[str]) -> str:
    parts, used = [], 0
    for relative in done[-CONTEXT_FILES:]:
        try:
            body = workspace.read(folder, relative)
        except DevError:
            continue
        chunk = f"--- {relative}\n" + "\n".join(body.splitlines()[:50])
        if used + len(chunk) > CONTEXT_CHARS:
            break
        parts.append(chunk)
        used += len(chunk)
    return "\n".join(parts) or "(nessuno)"


async def _write(plan: plans.Plan, item: plans.Item, folder) -> str:
    done = [i.path for i in plan.items if i.status == "done"]
    listing = "\n".join(f"- {i.path}: {i.purpose}" for i in plan.items)
    extra = ""
    for attempt in range(2):
        prompt = FILE_PROMPT.format(goal=plan.goal, stack=plan.stack, plan=listing, context=_context(folder, done),
                                    path=item.path, purpose=item.purpose, lines=MAX_LINES, extra=extra)
        text = _strip(await generate(prompt, max_tokens=FILE_TOKENS, temperature=0.15, kind="deep", system=SYSTEM, timeout=300))
        lines = len(text.splitlines())
        if lines <= HARD_LINES and not _commented(item.path, text):
            return text
        extra = (f" Il tentativo precedente era di {lines} righe: accorcia sotto {MAX_LINES}." if lines > HARD_LINES
                 else " Il tentativo precedente conteneva commenti: rimuovili tutti.")
    if lines > HARD_LINES:
        raise DevError(f"{item.path}: oltre {HARD_LINES} righe anche dopo il secondo tentativo, va diviso in più file nel piano")
    return text


async def make_plan(project: str, goal: str, stack: str) -> plans.Plan:
    workspace.project_dir(project)
    goal = str(goal or "").strip()
    if len(goal) < 10:
        raise DevError("descrivi meglio cosa vuoi costruire (almeno una frase)")
    prompt = PLAN_PROMPT.format(goal=goal[:plans.GOAL_LIMIT], stack=stack or "scegli lo stack più adatto", lines=MAX_LINES,
                                limit=plans.MAX_PLAN_FILES)
    try:
        raw = await generate(prompt, as_json=True, max_tokens=PLAN_TOKENS, temperature=0.2, kind="deep", system=SYSTEM, timeout=300)
    except BrainUnavailable as exc:
        raise DevError(f"il modello non è raggiungibile: {exc}") from exc
    if not isinstance(raw, dict):
        raise DevError("il modello non ha restituito un piano valido")
    plan = plans.build(project, goal, str(raw.get("stack") or stack), raw.get("files"))
    plans.save(plan)
    return plan


async def build_next(project: str, count: int) -> tuple[plans.Plan, list[str]]:
    plan = plans.load(project)
    folder = workspace.project_dir(project)
    report = []
    for item in plan.pending()[: max(1, min(int(count), 4))]:
        try:
            text = await _write(plan, item, folder)
            workspace.write(folder, item.path, text)
        except BrainUnavailable as exc:
            plans.save(plan)
            raise DevError(f"il modello non è raggiungibile: {exc}") from exc
        except DevError as exc:
            item.status, item.note = "failed", str(exc)[:200]
            report.append(f"NON scritto {item.path}: {exc}")
        else:
            item.status, item.note = "done", ""
            report.append(f"scritto {item.path} ({len(text.splitlines())} righe)")
        plans.save(plan)
    return plan, report
