import logging

from state import store

from agenti.agency import cognition, critic, director, documents, workspace
from agenti.agency.client import AgencyRejected, AgencyUnavailable, client
from agenti.agency.memory import memory
from agenti.agency.text import clean, folder_name, unique_id
from agenti.agency.words import dictionary, lang_of, word
from agenti.brain.llm import BrainUnavailable

log = logging.getLogger("nuxiva.agency")
GOAL_MIN = 8
GOAL_MAX = 8000
DEFAULT_BUDGET = {"tokens": 4_000_000, "seconds": 7 * 24 * 3600, "parallel": 8}
CONTROLS = ("pause", "resume", "cancel")


class AgencyFailure(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def start(goal: str, lang: str) -> dict:
    lang = lang_of(lang)
    goal = clean(goal, GOAL_MAX)
    if len(goal) < GOAL_MIN:
        raise AgencyFailure("goal")
    language_name = dictionary(lang)["language_name"]
    try:
        blueprint, planning_tokens = await director.think(goal, language_name)
        if not blueprint.tasks:
            raise AgencyFailure("empty_plan")
        reasoning, critic_tokens = await critic.interrogate(goal, blueprint, language_name)
    except BrainUnavailable as exc:
        raise AgencyFailure("brain") from exc
    known_decisions = [f"{d.topic}: {d.choice}" for d in blueprint.decisions]
    socratic = cognition.interrogate_goal(goal, known_decisions)
    specialists = cognition.recruit_specialists(goal, blueprint.architecture)
    project_id = unique_id(blueprint.title)
    folder = f"{folder_name(blueprint.title, project_id)} {project_id[-6:]}"
    try:
        await client.call("project_create", id=project_id, title=blueprint.title, goal=goal,
                          workspace=folder, budget=DEFAULT_BUDGET)
    except AgencyUnavailable as exc:
        raise AgencyFailure("unavailable") from exc
    context = {"goal": goal, "lang": lang, "language_name": language_name, "folder": folder,
               "work_dir": word(lang, "files", "work_dir"), "blueprint": blueprint.to_dict(),
               "reasoning": reasoning.to_dict(), "socratic": socratic, "specialists": specialists,
               "planning_tokens": planning_tokens + critic_tokens}
    memory.save(project_id, context)
    workspace.write(folder, word(lang, "files", "plan_file"), documents.plan(blueprint, goal, lang))
    workspace.write(folder, word(lang, "files", "reasoning_file"), documents.reasoning(reasoning, lang))
    detail = await client.call("project_plan", id=project_id, tasks=[t.spec() for t in blueprint.tasks],
                               decisions=[d.spec() for d in blueprint.decisions],
                               questions=[q.spec() for q in blueprint.questions])
    store.event("INFO", f"Agency project {project_id} planned with {len(blueprint.tasks)} tasks", "agency")
    return detail


async def launch(goal: str, lang: str) -> None:
    try:
        await start(goal, lang)
    except AgencyFailure as exc:
        store.event("WARN", f"Agency project not started: {exc.code}", "agency")
    except (AgencyRejected, AgencyUnavailable, workspace.WorkspaceError, OSError) as exc:
        log.error("Agency project start failed: %s", type(exc).__name__)
        store.event("ERROR", f"Agency project start failed: {type(exc).__name__}", "agency")


async def overview() -> dict:
    capacity = await client.call("capacity")
    projects = await client.call("project_list")
    return {"capacity": capacity, "projects": projects}


async def detail(project_id: str) -> dict:
    data = await client.call("project_get", id=project_id)
    try:
        context = memory.load(project_id)
    except KeyError:
        context = {}
    data["blueprint"] = context.get("blueprint")
    data["reasoning"] = context.get("reasoning")
    data["folder"] = context.get("folder")
    return data


async def control(project_id: str, action: str) -> dict:
    if action not in CONTROLS:
        raise AgencyFailure("invalid")
    return await client.call("project_control", id=project_id, action=action)


async def answer(project_id: str, question: str, option: str | None = None, answer_text: str | None = None) -> dict:
    return await client.call("project_answer", id=project_id, question=question, option=option, answer=answer_text)

