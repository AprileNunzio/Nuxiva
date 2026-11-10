from dataclasses import asdict, dataclass
import os
import shutil
import time

from features.agency.text import clean
from features.agency.words import word


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


def analyze_insights(tasks: list[dict], questions: list[dict], telemetry: TelemetrySnapshot, lang: str = "it") -> list[ProactiveInsight]:
    insights = []
    if telemetry.disk_used_percent > 90.0:
        insights.append(ProactiveInsight(
            id="ins_disk_pressure",
            kind="alert",
            title=word(lang, "proactive", "ins_disk_title"),
            detail=word(lang, "proactive", "ins_disk_detail").format(pct=telemetry.disk_used_percent),
            action="clean_cache",
            urgency="critical",
        ))
    open_q = [q for q in questions if isinstance(q, dict) and str(q.get("status") or "open") == "open"]
    if open_q:
        insights.append(ProactiveInsight(
            id="ins_blocked_questions",
            kind="supervision",
            title=word(lang, "proactive", "ins_q_title"),
            detail=word(lang, "proactive", "ins_q_detail").format(count=len(open_q)),
            action="review_questions",
            urgency="high",
        ))
    stalled = [t for t in tasks if isinstance(t, dict) and t.get("status") == "running" and int(t.get("attempts") or 0) >= 2]
    if stalled:
        insights.append(ProactiveInsight(
            id="ins_stalled_tasks",
            kind="optimization",
            title=word(lang, "proactive", "ins_stalled_title"),
            detail=word(lang, "proactive", "ins_stalled_detail").format(count=len(stalled)),
            action="inspect_drawers",
            urgency="normal",
        ))
    reviews = [t for t in tasks if isinstance(t, dict) and t.get("status") == "review"]
    if reviews:
        insights.append(ProactiveInsight(
            id="ins_ready_for_review",
            kind="progress",
            title=word(lang, "proactive", "ins_review_title"),
            detail=word(lang, "proactive", "ins_review_detail").format(count=len(reviews)),
            action="approve_kanban",
            urgency="normal",
        ))
    if not insights:
        insights.append(ProactiveInsight(
            id="ins_healthy",
            kind="progress",
            title=word(lang, "proactive", "ins_healthy_title"),
            detail=word(lang, "proactive", "ins_healthy_detail"),
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

    greeting = word(lang, "proactive", "greeting")
    progress = word(lang, "proactive", "progress").format(title=clean(title, 40), pct=pct, done=done, total=total)
    status = word(lang, "proactive", "status").format(running=running, review=review)
    urgents = [ins.detail for ins in insights if ins.urgency in ("critical", "high")]
    attention = word(lang, "proactive", "attention").format(details=" ".join(urgents)) if urgents else word(lang, "proactive", "optimal")
    return f"{greeting} {progress} {status}{attention}"
