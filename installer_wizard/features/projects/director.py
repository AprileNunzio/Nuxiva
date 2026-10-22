from dataclasses import dataclass, field

from features.brain import llm
from features.experts.model import clean
from features.projects.model import LIMITS, MAX_STEPS, Project, Step, note, steps_from

MAX_ROUNDS = 2
MAX_FINAL = 3
MAX_GAPS = 6
REVIEW_TOKENS = 700
FINAL_TOKENS = 1200
RESULT_CHARS = 1800
SYSTEM = ("Sei il CEO del progetto: severo, concreto, orientato al risultato. Giudichi solo sulle prove ricevute, mai sulle promesse. "
          "Se il lavoro non soddisfa i criteri di accettazione lo fai rifare con indicazioni precise; se manca qualcosa di importante "
          "aggiungi passi. Rispondi solo con JSON.")


@dataclass
class Verdict:
    approved: bool
    feedback: str = ""
    extra: list = field(default_factory=list)


def evidence(project: Project) -> str:
    if not project.workspace:
        return ""
    from features.devstudio import plan as plans
    from features.devstudio import workspace
    try:
        folder = workspace.project_dir(project.workspace)
    except workspace.DevError:
        return f"Cartella di sviluppo «{project.workspace}»: non ancora creata."
    parts = [f"Cartella di sviluppo «{project.workspace}»: {len(workspace.files(folder))} file scritti."]
    try:
        counts = plans.load(project.workspace).counts()
        parts.append(f"Piano dei file: {counts['done']} scritti, {counts['pending']} in attesa, {counts['failed']} da rivedere.")
    except workspace.DevError:
        parts.append("Nessun piano dei file salvato.")
    return " ".join(parts)


async def _ask(prompt: str, tokens: int):
    reply = await llm.generate(prompt, as_json=True, max_tokens=tokens, temperature=0.1, system=SYSTEM, component="projects")
    return reply if isinstance(reply, dict) else {}


def _verdict(raw: dict) -> Verdict:
    kind = str(raw.get("verdict") or "approve").lower()
    feedback = clean(raw.get("feedback"), LIMITS["feedback"])
    extra = raw.get("extra_steps") if isinstance(raw.get("extra_steps"), list) else []
    return Verdict(kind != "rework" or not feedback, feedback, extra[:MAX_GAPS])


async def review_step(project: Project, step: Step) -> None:
    proof = evidence(project)
    prompt = (f"Progetto: {project.goal}\nPasso: {step.text}\nCriteri di accettazione: {step.acceptance or 'il passo è svolto per intero e con qualità'}\n"
              f"Risultato consegnato dall'esperto:\n{step.result[:RESULT_CHARS]}\n" + (f"Prove oggettive: {proof}\n" if proof else "")
              + 'Rispondi con {"verdict": "approve" o "rework", "feedback": "cosa rifare, preciso", "extra_steps": [{"text": "...", "acceptance": "..."}]}.')
    verdict = _verdict(await _ask(prompt, REVIEW_TOKENS))
    if verdict.approved or step.round >= MAX_ROUNDS:
        step.status, step.feedback = "done", ""
        step.error = "" if verdict.approved else "approvato con riserva dopo i rifacimenti"
        note(project, "approvato" if verdict.approved else "riserva", f"{step.id} {step.text}")
        return
    step.status, step.round, step.feedback = "pending", step.round + 1, verdict.feedback
    note(project, "rifacimento", f"{step.id}: {verdict.feedback}")


def _append(project: Project, rows: list) -> int:
    room = MAX_STEPS - len(project.steps)
    added = 0
    for item in steps_from(rows)[:max(room, 0)] if rows else []:
        if item.text in [s.text for s in project.steps]:
            continue
        project.steps.append(Step(f"s{len(project.steps) + 1}", item.text, acceptance=item.acceptance))
        added += 1
    return added


async def final_review(project: Project) -> bool:
    done = "\n".join(f"- {s.text}: {s.result[:240]}" for s in project.steps if s.status == "done")
    proof = evidence(project)
    prompt = (f"Progetto: {project.goal}\nIndicazioni del proprietario: {'; '.join(project.directives) or 'nessuna'}\n"
              f"Passi completati:\n{done}\n" + (f"Prove oggettive: {proof}\n" if proof else "")
              + 'Il progetto soddisfa davvero l\'obiettivo? Rispondi con {"complete": true o false, "gaps": [{"text": "passo da aggiungere", '
                '"acceptance": "criterio"}]}. Elenca solo lacune reali.')
    raw = await _ask(prompt, FINAL_TOKENS)
    gaps = raw.get("gaps") if isinstance(raw.get("gaps"), list) else []
    if raw.get("complete", True) or not gaps:
        note(project, "chiusura", "revisione finale superata")
        return True
    try:
        added = _append(project, gaps)
    except ValueError:
        added = 0
    note(project, "potenziamento", f"{added} passi aggiunti dalla revisione finale")
    return added == 0
