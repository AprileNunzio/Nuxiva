import time
from dataclasses import dataclass, field
from typing import Any

from agenti.agency.episodic_graph import episodic_graph
from agenti.people import people


@dataclass
class HabitObservation:
    person_slug: str
    habit_key: str
    observed_value: Any
    user_feedback: str
    timestamp: float = field(default_factory=time.time)


class ContinuousHabitReinforcementGovernor:
    def __init__(self) -> None:
        self.habit_confidence: dict[str, dict[str, float]] = {}
        self.observations: list[HabitObservation] = []

    def record_feedback(self, person_slug: str, habit_key: str, value: Any, feedback: str) -> dict[str, Any]:
        obs = HabitObservation(
            person_slug=person_slug,
            habit_key=habit_key,
            observed_value=value,
            user_feedback=feedback.lower().strip(),
        )
        self.observations.append(obs)

        user_scores = self.habit_confidence.setdefault(person_slug, {})
        current = user_scores.get(habit_key, 0.5)

        if obs.user_feedback in ("confirm", "accepted", "positive", "appreciated"):
            current = min(1.0, current + 0.15)
        elif obs.user_feedback in ("rejected", "wrong", "negative", "reverted"):
            current = max(0.0, current - 0.25)
        elif obs.user_feedback in ("tweaked", "adjusted"):
            current = min(1.0, max(0.2, current + 0.05))

        user_scores[habit_key] = round(current, 3)

        if current >= 0.85:
            people.update(person_slug, {habit_key: value})
            episodic_graph.record_episode(
                person_slug=person_slug,
                event_name=f"habit_consolidated_{habit_key}",
                emotion_state="satisfied",
                context_payload={"habit_key": habit_key, "value": value, "confidence": current},
            )

        return {
            "status": "recorded",
            "person_slug": person_slug,
            "habit_key": habit_key,
            "confidence": current,
            "is_autonomous": current >= 0.85,
        }

    def get_confidence(self, person_slug: str, habit_key: str) -> float:
        return self.habit_confidence.get(person_slug, {}).get(habit_key, 0.5)

    def is_autonomous_ready(self, person_slug: str, habit_key: str) -> bool:
        return self.get_confidence(person_slug, habit_key) >= 0.85


habit_governor = ContinuousHabitReinforcementGovernor()
