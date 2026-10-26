from features.experts.model import clean
from features.experts.store import experts
from features.projects import publish
from features.projects.model import LIMITS, MAX_DIRECTIVES, MAX_STEPS, Project, ProjectError, Step, note
from features.projects.store import projects

OPEN = ("planning", "running", "paused", "done", "failed")


def _project(project_id: str) -> Project:
    project = projects.get(project_id)
    if project.status not in OPEN:
        raise ProjectError("Il progetto è stato annullato")
    return project


def _step(project: Project, step_id: str) -> Step:
    found = next((s for s in project.steps if s.id == step_id), None)
    if found is None:
        raise ProjectError("Passo sconosciuto")
    return found


def _commit(project: Project, reopen: bool = True) -> Project:
    if reopen and project.status in ("done", "failed", "paused") and any(s.status == "pending" for s in project.steps):
        project.status, project.error, project.final_rounds = "running", "", 0
    projects.save(project)
    publish.push(project)
    return project


def direct(project_id: str, text: str) -> Project:
    project = _project(project_id)
    clean_text = clean(text, LIMITS["directive"])
    if len(clean_text) < 3:
        raise ProjectError("Scrivi l'indicazione per la squadra")
    if len(project.directives) >= MAX_DIRECTIVES:
        raise ProjectError("Troppe indicazioni: rimuovi quelle superate")
    project.directives.append(clean_text)
    note(project, "indicazione", clean_text)
    return _commit(project, reopen=False)


def add_step(project_id: str, text: str, acceptance: str = "", expert_id: str = "") -> Project:
    project = _project(project_id)
    body = clean(text, LIMITS["text"])
    if len(body) < 3:
        raise ProjectError("Descrivi il passo da aggiungere")
    if len(project.steps) >= MAX_STEPS:
        raise ProjectError(f"Un progetto può avere al massimo {MAX_STEPS} passi")
    step = Step(f"s{max((int(s.id[1:]) for s in project.steps), default=0) + 1}", body, acceptance=clean(acceptance, LIMITS["acceptance"]))
    if expert_id:
        expert = experts.get(expert_id)
        step.expert_id, step.expert_role = expert.id, expert.role
    project.steps.append(step)
    note(project, "passo aggiunto", f"{step.id} {body}")
    return _commit(project)


def remove_step(project_id: str, step_id: str) -> Project:
    project = _project(project_id)
    step = _step(project, step_id)
    if step.status in ("running", "review"):
        raise ProjectError("Il passo è in lavorazione: mettilo in pausa prima di toglierlo")
    project.steps.remove(step)
    for other in project.steps:
        other.depends = [d for d in other.depends if d != step_id]
    note(project, "passo tolto", f"{step_id} {step.text}")
    return _commit(project, reopen=False)


def assign_expert(project_id: str, step_id: str, expert_id: str) -> Project:
    project = _project(project_id)
    step = _step(project, step_id)
    if step.status in ("running", "review", "done"):
        raise ProjectError("Il passo è già in lavorazione o concluso")
    expert = experts.get(expert_id) if expert_id else None
    step.expert_id, step.expert_role = (expert.id, expert.role) if expert else ("", "")
    note(project, "assegnazione", f"{step_id} → {expert.role if expert else 'scelta automatica'}")
    return _commit(project, reopen=False)


def redo(project_id: str, step_id: str, feedback: str) -> Project:
    project = _project(project_id)
    step = _step(project, step_id)
    if step.status in ("running", "review"):
        raise ProjectError("Il passo è in lavorazione")
    step.status, step.round, step.error = "pending", 0, ""
    step.feedback = clean(feedback, LIMITS["feedback"]) or "Rifai il lavoro con più cura e completezza."
    for other in project.steps:
        if step.id in other.depends and other.status == "done":
            other.status, other.feedback = "pending", "Il passo da cui dipendi è stato rifatto: verifica e aggiorna il tuo lavoro."
    note(project, "rifacimento", f"{step_id}: {step.feedback}")
    return _commit(project)


async def add_expert(project_id: str, need: str) -> dict:
    project = _project(project_id)
    from features.experts import autonomy
    expert = await autonomy.create_for(f"{clean(need, 300)}. {project.goal}"[:400], project.lang)
    if expert is None:
        raise ProjectError("Non riesco ad aggiungere un esperto adatto: descrivi meglio che competenza serve")
    note(project, "squadra", f"«{expert.role}» aggiunto al progetto")
    _commit(project, reopen=False)
    return {"id": expert.id, "role": expert.role}
