import re

from features.autonomous_worker.application.deliberator import deliberator
from features.autonomous_worker.application.specialist_forge import forge
from features.autonomous_worker.domain.exceptions import AutonomousWorkerError
from features.autonomous_worker.domain.models import MissionStatus
from features.autonomous_worker.infrastructure.store import mission_store
from features.autonomous_worker.presentation.desk_notifier import notifier
from features.experts.routing import flat

MISSION_TRIGGER = re.compile(
    r"\b(crea|avvia|inizia|costruisci|sviluppa|realizza|programma|analizza|progetta|pianifica)\b.*"
    r"\b(missione|progetto|sito|software|app|applicazione|sistema|piattaforma|analisi|strategia|architettura|audit|modello|contratto)\b",
    re.I,
)

STATUS_TRIGGER = re.compile(r"\b(stato|avanzamento|come va|situazione)\b.*\b(mission[ei]|progett[oi])\b", re.I)


async def answer(text: str, lang: str = "it") -> tuple[str, dict]:
    body = flat(text)

    if STATUS_TRIGGER.search(body):
        active = mission_store.active()
        if not active:
            return "Nessuna missione autonoma attualmente in corso.", {"mode": "face"}
        summaries = [f"«{m.title}»: {m.progress}% ({len([t for t in m.all_tasks() if t.status == 'done'])}/{len(m.all_tasks())} task)" for m in active]
        return f"Missioni attive: {'; '.join(summaries)}.", {"mode": "focus", "widget": "mission_tracker"}

    if MISSION_TRIGGER.search(text) or len(text.strip().split()) >= 6:
        try:
            mission = await deliberator.deliberate(goal=text, lang=lang)
            forge.assemble_team(mission)
            mission_store.save(mission)
            notifier.push_mission(mission)

            if mission.status == MissionStatus.QUESTION and mission.questions:
                q = mission.questions[0]
                speech = (
                    f"Il CEO ha strutturato la missione «{mission.title}» con una squadra di {len(mission.specialists)} specialisti. "
                    f"Prima di procedere al 100%, è richiesta una scelta: {q.question}"
                )
            else:
                speech = (
                    f"Il CEO ha avviato la missione autonoma «{mission.title}». La squadra di {len(mission.specialists)} specialisti "
                    f"sta operando in background con verifiche continue. Puoi seguire l'avanzamento e la chat degli esperti sul widget della schermata."
                )

            return speech, {"mode": "focus", "widget": "mission_tracker", "mission_id": mission.id}
        except AutonomousWorkerError as exc:
            return f"Errore nell'inizializzazione della missione: {exc}", {"mode": "face"}

    raise LookupError("autonomous_worker")
