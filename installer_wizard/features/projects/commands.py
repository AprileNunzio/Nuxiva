import re

from features.experts.routing import flat
from features.projects import service
from features.projects.model import ProjectError
from features.projects.store import projects

FACE = {"mode": "face"}
START = re.compile(r"\b(avvia|crea|apri|inizia|comincia|lancia)\s+(un\s+|il\s+|nuovo\s+)*(nuovo\s+)?progetto\b[\s:,-]*(?:per\s+|di\s+|che\s+)?(.*)")
STATUS = re.compile(r"\b(stato|a che punto|avanzamento|come va)\b.*\bprogett[oi]\b|\bprogetti\s+in\s+corso\b")


def _line(project) -> str:
    return f"«{project.title}»: {project.progress}% ({len([s for s in project.steps if s.status == 'done'])}/{len(project.steps) or '?'} passi)"


async def answer(text: str, lang: str = "it") -> tuple[str, dict]:
    body = flat(text)
    match = START.search(body)
    if match:
        goal = match.group(4).strip()
        original = text[len(text) - len(goal):] if goal and text.lower().endswith(goal.lower()) else text
        try:
            project = service.start(original if len(original) >= 8 else text, lang)
        except ProjectError as exc:
            return str(exc), FACE
        return (f"Ho avviato il progetto «{project.title}»: preparo il piano e assegno i passi agli esperti. "
                "Ne vedi l'avanzamento nel widget."), FACE
    if STATUS.search(body):
        active = [p for p in projects.all() if p.status in ("planning", "running", "paused")]
        if not active:
            return "Non ci sono progetti in corso.", FACE
        return "Progetti in corso: " + "; ".join(_line(p) for p in active) + ".", FACE
    raise LookupError("projects")
