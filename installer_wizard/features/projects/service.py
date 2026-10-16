import asyncio
import logging
import time

from state import store as state

from features.brain import llm
from features.experts import routing, service as expert_service
from features.experts.store import experts
from features.projects import publish
from features.projects.model import ACTIVE, Project, ProjectError, Step, create as new_project, steps_from
from features.projects.store import projects
from features.team.board import board

log = logging.getLogger("nuxiva.projects")
TICK_SECONDS = 5
PLAN_TOKENS = 700
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


async def plan(project: Project) -> None:
    prompt = (
        f"Scomponi questo progetto in 3-8 passi concreti, ordinati e verificabili, ciascuno eseguibile da un esperto.\n"
        f"Rispondi in {LANG_NAMES[project.lang]} con JSON: {{\"steps\": [{{\"text\": \"...\"}}]}}\n"
        f"Progetto: {project.goal}"
    )
    try:
        data = await llm.generate(prompt, as_json=True, max_tokens=PLAN_TOKENS, temperature=0.2, component="projects")
        project.steps = steps_from(data.get("steps") if isinstance(data, dict) else data)
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
    projects.save(project)
    board.post("progetti", f"project:{project.id}", f"Piano pronto: {len(project.steps)} passi", "progetto")
    publish.push(project)


def assign(step: Step) -> None:
    expert = routing.best(experts.all(), step.text)
    step.expert_id = expert.id if expert else ""
    step.expert_role = expert.role if expert else ""


def context(project: Project) -> str:
    done = [s for s in project.steps if s.status == "done"][-CONTEXT_STEPS:]
    return "\n".join(f"- {s.text}: {s.result[:CONTEXT_CHARS]}" for s in done)


def brief(project: Project, step: Step) -> str:
    previous = context(project)
    return (f"Progetto: {project.goal}\n" + (f"Già fatto:\n{previous}\n" if previous else "")
            + f"Esegui solo questo passo e riporta il risultato concreto: {step.text}")


async def execute(project: Project, step: Step) -> None:
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
    step.status, step.error, step.finished = "done", "", time.time()


async def advance(project: Project) -> None:
    step = next((s for s in project.steps if s.status == "pending"), None)
    if step is None:
        waiting = [s for s in project.steps if s.status == "waiting"]
        failed = [s for s in project.steps if s.status == "failed"]
        if waiting:
            project.status = "paused"
        elif failed:
            project.status, project.error = "failed", failed[0].error
        else:
            project.status = "done"
            board.post("progetti", "tutti", f"Progetto concluso: {project.title}", "progetto")
        projects.save(project)
        publish.push(project)
        return
    if not step.expert_id:
        assign(step)
    step.status, step.started = "running", time.time()
    publish.push(project)
    try:
        await execute(project, step)
    except (llm.BrainUnavailable, expert_service.ExpertError) as exc:
        step.status, step.error = "failed", str(exc)[:300]
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
            elif project.status == "running":
                await advance(project)
    finally:
        current.reset(token)


async def run() -> None:
    while True:
        try:
            await tick()
        except Exception:
            log.exception("Ciclo dei progetti interrotto")
        await asyncio.sleep(TICK_SECONDS)
