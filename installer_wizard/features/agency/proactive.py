from dataclasses import asdict, dataclass
import os
import shutil
import time

from features.agency.text import clean


@dataclass(frozen=True)
class TelemetrySnapshot:
    timestamp: float
    cpu_count: int
    load_avg: tuple[float, float, float]
    disk_total_gb: float
    disk_free_gb: float
    disk_used_percent: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ProactiveInsight:
    id: str
    kind: str
    title: str
    detail: str
    action: str
    urgency: str

    def to_dict(self) -> dict:
        return asdict(self)


def sample_telemetry() -> TelemetrySnapshot:
    cpu_count = os.cpu_count() or 1
    try:
        load = os.getloadavg()
    except (AttributeError, OSError):
        load = (0.0, 0.0, 0.0)
    try:
        usage = shutil.disk_usage("/")
        total_gb = round(usage.total / (1024 ** 3), 2)
        free_gb = round(usage.free / (1024 ** 3), 2)
        used_pct = round((usage.used / usage.total) * 100.0, 1)
    except OSError:
        total_gb, free_gb, used_pct = 100.0, 50.0, 50.0
    return TelemetrySnapshot(
        timestamp=time.time(),
        cpu_count=cpu_count,
        load_avg=(round(load[0], 2), round(load[1], 2), round(load[2], 2)),
        disk_total_gb=total_gb,
        disk_free_gb=free_gb,
        disk_used_percent=used_pct,
    )


def analyze_insights(tasks: list[dict], questions: list[dict], telemetry: TelemetrySnapshot) -> list[ProactiveInsight]:
    insights = []
    if telemetry.disk_used_percent > 90.0:
        insights.append(ProactiveInsight(
            id="ins_disk_pressure",
            kind="alert",
            title="Spazio su disco critico",
            detail=f"Utilizzo disco a {telemetry.disk_used_percent}%. Consigliata bonifica cache.",
            action="clean_cache",
            urgency="critical",
        ))
    open_q = [q for q in questions if isinstance(q, dict) and str(q.get("status") or "open") == "open"]
    if open_q:
        insights.append(ProactiveInsight(
            id="ins_blocked_questions",
            kind="supervision",
            title="Domande aperte nel DAG",
            detail=f"Ci sono {len(open_q)} quesiti decisionali in attesa dell'utente.",
            action="review_questions",
            urgency="high",
        ))
    stalled = [t for t in tasks if isinstance(t, dict) and t.get("status") == "running" and int(t.get("attempts") or 0) >= 2]
    if stalled:
        insights.append(ProactiveInsight(
            id="ins_stalled_tasks",
            kind="optimization",
            title="Task con tentativi multipli",
            detail=f"{len(stalled)} task hanno richiesto rework o presentano frizioni nei test.",
            action="inspect_drawers",
            urgency="normal",
        ))
    reviews = [t for t in tasks if isinstance(t, dict) and t.get("status") == "review"]
    if reviews:
        insights.append(ProactiveInsight(
            id="ins_ready_for_review",
            kind="progress",
            title="Attività pronte per il rilascio",
            detail=f"{len(reviews)} attività completate attendono la validazione del CEO.",
            action="approve_kanban",
            urgency="normal",
        ))
    if not insights:
        insights.append(ProactiveInsight(
            id="ins_healthy",
            kind="progress",
            title="Ecosistema ottimizzato",
            detail="Tutti i reparti operano a regime senza colli di bottiglia rilevati.",
            action="observe",
            urgency="normal",
        ))
    return insights


def generate_briefing(lang: str, title: str, counts: dict, insights: list[ProactiveInsight]) -> str:
    total = int(counts.get("total") or 0)
    done = int(counts.get("done") or 0)
    running = int(counts.get("running") or 0)
    review = int(counts.get("review") or 0)
    pct = int((done / total * 100) if total > 0 else 0)

    if lang == "en":
        greeting = "Nunzio, here is your executive briefing from NunzioTech Agency."
        progress = f"Project '{clean(title, 40)}' is at {pct}% progress with {done} of {total} tasks completed."
        status = f"{running} agents active, {review} tasks awaiting review."
        urgents = [ins.detail for ins in insights if ins.urgency in ("critical", "high")]
        urg_msg = f" Attention required: {' '.join(urgents)}" if urgents else " All systems and cognitive workloads are performing optimally."
        return f"{greeting} {progress} {status}{urg_msg}"

    greeting = "Nunzio, ecco il quadro operativo da NunzioTech Agency."
    progress = f"Il progetto '{clean(title, 40)}' è al {pct}% di avanzamento ({done} su {total} attività completate)."
    status = f"{running} agenti attivi, {review} attività in revisione."
    urgents = [ins.detail for ins in insights if ins.urgency in ("critical", "high")]
    urg_msg = f" Attenzione: {' '.join(urgents)}" if urgents else " Il carico cognitivo e le risorse di sistema sono perfettamente stabili."
    return f"{greeting} {progress} {status}{urg_msg}"
