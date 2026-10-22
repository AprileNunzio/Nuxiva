import asyncio
import logging
import re
import time

from state import store as state

from features.brain import llm
from features.experts import routing, service as expert_service
from features.experts.store import experts
from features.devstudio import workspace as dev_workspace
from features.projects import director, publish
from features.projects.model import ACTIVE, Project, ProjectError, Step, create as new_project, note, steps_from, with_modelling
from features.projects.store import projects
from features.team.board import board

log = logging.getLogger("nuxiva.projects")
TICK_SECONDS = 5
PLAN_TOKENS = 2800
PARALLEL = 2
CODING = re.compile(r"\b(sito|siti|app|applicazion\w*|api|php|python|react|javascript|node|software|programm\w*|backend|frontend|website|web\s*app|gestionale|widget)\b", re.I)
CONTEXT_STEPS = 3
CONTEXT_CHARS = 400
LANG_NAMES = {"it": "italiano", "en": "English", "es": "español", "fr": "français"}


def start(goal: str, lang: str, title: str = "") -> Project:
    project = projects.add(new_project(goal, lang, title))
    board.post("progetti", "tutti", f"Nuovo progetto: {project.title}", "progetto")
    state.event("INFO", f"Progetto {project.id} avviato", "projects")
    publish.push(project)
    return project


def pause(project_id: str) -> Project:
    project = projects.get(project_id)
    if project.status not in ACTIVE:
        raise ProjectError("Il progetto non è in corso")
    project.status = "paused"
    projects.save(project)
    publish.push(project)
    return project


def resume(project_id: str) -> Project:
    project = projects.get(project_id)
    if project.status != "paused":
        raise ProjectError("Il progetto non è in pausa")
    project.status = "running" if project.steps else "planning"
    project.error = ""
    projects.save(project)
    publish.push(project)
    return project


def cancel(project_id: str) -> Project:
    project = projects.get(project_id)
    if project.status in ("done", "cancelled"):
        raise ProjectError("Il progetto è già concluso")
    project.status = "cancelled"
    projects.save(project)
    publish.push(project)
    return project


def delete(project_id: str) -> None:
    projects.get(project_id)
    projects.remove(project_id)
    publish.drop(project_id)


def retry(project_id: str) -> Project:
    project = projects.get(project_id)
    if project.status not in ("failed", "paused"):
        raise ProjectError("Il progetto non ha passi da ripetere")
    for step in project.steps:
        if step.status in ("failed", "waiting"):
            step.status, step.error = "pending", ""
    project.status, project.error = "running", ""
    projects.save(project)
    publish.push(project)
    return project


def workspace_name(project: Project) -> str:
    if not CODING.search(project.goal):
        return ""
    try:
        base = dev_workspace.slug(project.title)[:30].rstrip("-")
        return dev_workspace.slug(f"{base}-{project.id[1:5]}")
    except dev_workspace.DevError:
        return dev_workspace.slug(f"progetto-{project.id[1:7]}")


async def plan(project: Project) -> None:
    prompt = (
        f"Scomponi questo progetto in passi concreti, ordinati e verificabili (da 4 a 30, secondo la complessità), ciascuno eseguibile da un esperto.\n"
        f"Per ogni passo indica il criterio di accettazione e da quali passi precedenti dipende (numeri, 1 è il primo); i passi indipendenti possono procedere in parallelo.\n"
        f"Includi sempre un passo finale di verifica complessiva. Rispondi in {LANG_NAMES[project.lang]} con JSON: "
        f"{{\"steps\": [{{\"text\": \"...\", \"acceptance\": \"...\", \"depends\": [1]}}]}}\n"
        f"Progetto: {project.goal}"
    )
    try:
        data = await llm.generate(prompt, as_json=True, max_tokens=PLAN_TOKENS, temperature=0.2, component="projects")
        project.steps = steps_from(data.get("steps") if isinstance(data, dict) else data)
        if project.kind == "3d":
            project.steps = with_modelling(project.steps, project.lang)
    except llm.BrainUnavailable as exc:
        project.error = str(exc)[:300]
        projects.save(project)
        publish.push(project)
        return
    except ProjectError as exc:
        project.status, project.error = "failed", str(exc)
        projects.save(project)
        publish.push(project)
        return
    project.status, project.error = "running", ""
    project.workspace = project.workspace or workspace_name(project)
    note(project, "piano", f"{len(project.steps)} passi")
    projects.save(project)
    board.post("progetti", f"project:{project.id}", f"Piano pronto: {len(project.steps)} passi", "progetto")
    publish.push(project)


async def assign(step: Step, project: Project) -> None:
    expert = routing.best(experts.all(), step.text)
    if expert is None:
        from features.experts import autonomy
        expert = await autonomy.create_for(f"{step.text}. {project.goal}"[:400], project.lang)
        if expert:
            note(project, "squadra", f"nuovo esperto «{expert.role}» per: {step.text}")
    step.expert_id = expert.id if expert else ""
    step.expert_role = expert.role if expert else ""


def context(project: Project) -> str:
    done = [s for s in project.steps if s.status == "done"][-CONTEXT_STEPS:]
    return "\n".join(f"- {s.text}: {s.result[:CONTEXT_CHARS]}" for s in done)


def brief(project: Project, step: Step) -> str:
    previous = context(project)
    parts = [f"Progetto: {project.goal}"]
    if project.directives:
        parts.append("Indicazioni del proprietario:\n" + "\n".join(f"- {d}" for d in project.directives))
    if project.workspace:
        parts.append(f"Progetto di sviluppo: «{project.workspace}». Se non esiste crealo con dev_new; se esiste riprendilo con dev_status e "
                     "continua dal piano, senza ricominciare. Per lavori grandi usa dev_plan e dev_build.")
    if previous:
        parts.append(f"Già fatto:\n{previous}")
    if step.acceptance:
        parts.append(f"Criterio di accettazione: {step.acceptance}")
    if step.feedback:
        parts.append(f"Il CEO ha respinto il lavoro precedente. Correggi esattamente questo: {step.feedback}")
    parts.append(f"Esegui solo questo passo e riporta il risultato concreto: {step.text}")
    return "\n".join(parts)


async def model_in_studio(project: Project, step: Step) -> None:
    from features.models3d import generator, studio
    meta = await generator.create(project.goal)
    project.model_id = meta["id"]
    studio.open_studio(meta["id"], f"Ecco {meta['title']}: puoi modificarlo nello studio 3D.")
    step.result = f"{meta['title']}: {len(meta.get('parts', []))} parti"
    step.status, step.error, step.finished = "done", "", time.time()


async def execute(project: Project, step: Step) -> None:
    if step.action == "model3d":
        await model_in_studio(project, step)
        return
    prompt = brief(project, step)
    if step.expert_id:
        try:
            out = await expert_service.ask(step.expert_id, prompt, project.lang, origin="progetti")
        except expert_service.ExpertBusy:
            step.status = "pending"
            return
        if out.get("pending"):
            step.status = "waiting"
            step.error = out["pending"]["tool"]
            return
        step.result = out["text"]
    else:
        step.result = str(await llm.generate(prompt, max_tokens=900, temperature=0.3, component="projects"))
    step.status, step.error = "review", ""


def ready(project: Project) -> list[Step]:
    done = {s.id for s in project.steps if s.status == "done"}
    known = {s.id for s in project.steps}
    return [s for s in project.steps if s.status == "pending" and all(d in done or d not in known for d in s.depends)]


def retry_after_failure(step: Step, reason: str) -> None:
    if step.round < director.MAX_ROUNDS:
        step.status, step.round, step.feedback = "pending", step.round + 1, f"il tentativo precedente è fallito: {reason}"
    else:
        step.status = "failed"
    step.error = reason


async def work(project: Project, step: Step) -> None:
    if step.status != "review":
        try:
            if not step.expert_id:
                await assign(step, project)
            step.status, step.started = "running", time.time()
            await execute(project, step)
        except (llm.BrainUnavailable, expert_service.ExpertError, ValueError) as exc:
            retry_after_failure(step, str(exc)[:300])
            return
    if step.status != "review":
        return
    try:
        await director.review_step(project, step)
    except llm.BrainUnavailable as exc:
        step.error = str(exc)[:300]
        return
    except ValueError as exc:
        step.status, step.error = "done", f"revisione non conclusiva: {str(exc)[:200]}"
    if step.status == "done":
        step.finished = time.time()


async def conclude(project: Project) -> None:
    for step in project.steps:
        if step.status == "pending":
            step.status, step.error = "failed", "dipendenza non soddisfatta"
    waiting = [s for s in project.steps if s.status == "waiting"]
    failed = [s for s in project.steps if s.status == "failed"]
    if waiting:
        project.status = "paused"
    elif failed:
        project.status, project.error = "failed", failed[0].error
    elif project.final_rounds >= director.MAX_FINAL:
        project.status = "done"
    else:
        try:
            project.final_rounds += 1
            complete = await director.final_review(project)
        except llm.BrainUnavailable as exc:
            project.final_rounds -= 1
            project.error = str(exc)[:300]
            return
        project.status = "done" if complete else "running"
    if project.status == "done":
        note(project, "chiuso", project.title)
        board.post("progetti", "tutti", f"Progetto concluso: {project.title}", "progetto")


async def advance(project: Project) -> None:
    batch = [s for s in project.steps if s.status == "review"] + ready(project)
    batch = batch[:max(PARALLEL, sum(1 for s in project.steps if s.status == "review"))]
    if not batch:
        await conclude(project)
    else:
        for step in batch:
            if step.status == "pending":
                step.status, step.started = "running", time.time()
        publish.push(project)
        await asyncio.gather(*(work(project, step) for step in batch))
    projects.save(project)
    publish.push(project)


async def tick() -> None:
    from features.authz import resolve
    from features.authz.principal import act_as, current
    token = act_as(resolve.for_session())
    try:
        for project in projects.all():
            if project.status == "planning":
                await plan(project)
        await asyncio.gather(*(advance(p) for p in projects.all() if p.status == "running"))
    finally:
        current.reset(token)


async def run() -> None:
    while True:
        try:
            await tick()
        except Exception:
            log.exception("Ciclo dei progetti interrotto")
        await asyncio.sleep(TICK_SECONDS)
