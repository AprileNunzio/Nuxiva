from typing import Any

from features.automations.bus import bus
from features.autonomous_worker.domain.models import Mission, MissionStatus, TaskStatus
from features.desktop.desk import desk

WIDGET_NAME = "mission_tracker"
TTL_COMPLETED = 7200


class DeskNotifier:
    def push_mission(self, mission: Mission) -> None:
        key = f"mission:{mission.id}"
        ttl = TTL_COMPLETED if mission.status in (MissionStatus.DONE, MissionStatus.FAILED, MissionStatus.CANCELLED) else 0

        active_task = next((t for t in mission.all_tasks() if t.status == TaskStatus.RUNNING), None)
        waiting_task = next((t for t in mission.all_tasks() if t.status == TaskStatus.WAITING), None)
        current = active_task or waiting_task

        all_tasks = mission.all_tasks()
        done_count = sum(1 for t in all_tasks if t.status == TaskStatus.DONE)

        unanswered_questions = [q.to_dict() for q in mission.questions if not q.answered]

        payload: dict[str, Any] = {
            "id": mission.id,
            "title": mission.title,
            "goal": mission.goal,
            "domain": mission.domain,
            "status": mission.status.value if isinstance(mission.status, MissionStatus) else str(mission.status),
            "progress": mission.progress,
            "total_tasks": len(all_tasks),
            "done_tasks": done_count,
            "current_task": current.title if current else "",
            "current_expert": current.specialist_role if current else "",
            "specialists": [s.to_dict() for s in mission.specialists],
            "phases": [p.to_dict() for p in mission.phases],
            "questions": unanswered_questions,
            "recent_collab": [m.to_dict() for m in mission.collab_messages[-8:]],
            "artifacts_count": len(mission.artifacts),
            "error": mission.error,
        }

        desk.show(WIDGET_NAME, payload, key=key, ttl=ttl)

        bus.set_state(f"nuxiva.mission.{mission.id}", payload["status"], payload)
        bus.emit("mission_progress", payload)
        if mission.status == MissionStatus.DONE:
            bus.emit("mission_completed", payload)
        elif mission.status in (MissionStatus.FAILED, MissionStatus.CANCELLED):
            bus.emit("mission_failed", payload)
        if unanswered_questions:
            bus.emit("mission_question", {"mission_id": mission.id, "questions": unanswered_questions})

    def remove_mission(self, mission_id: str) -> None:
        desk.hide(key=f"mission:{mission_id}")
        bus.set_state(f"nuxiva.mission.{mission_id}", "removed", {})


notifier = DeskNotifier()
