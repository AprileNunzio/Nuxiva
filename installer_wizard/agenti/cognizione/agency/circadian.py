import time
from dataclasses import asdict, dataclass, field

PHASE_MORNING = "morning_health"
PHASE_MARKET = "market_finance"
PHASE_PROJECTS = "project_execution"
PHASE_EVENING = "evening_leisure"
PHASE_NIGHT = "night_rest"

DEFAULT_PHASE_WIDGETS = {
    PHASE_MORNING: [
        {"id": "widget_sleep_vitals", "type": "vitals_card", "title": "Parametri Vitali, Sonno Profondo & HRV", "urgency": "high"},
        {"id": "widget_morning_weather", "type": "weather_radar", "title": "Meteo del Giorno & Qualità dell'Aria", "urgency": "normal"},
    ],
    PHASE_MARKET: [
        {"id": "widget_stock_ticker", "type": "market_ticker", "title": "Borsa Valori, S&P 500, FTSE MIB & Crypto", "urgency": "high"},
        {"id": "widget_financial_news", "type": "news_feed", "title": "Rassegna Stampa Economico-Finanziaria", "urgency": "normal"},
    ],
    PHASE_PROJECTS: [
        {"id": "widget_project_kanban", "type": "kanban_board", "title": "Avanzamento Progetti & Consegne Clienti", "urgency": "high"},
        {"id": "widget_team_velocity", "type": "burndown_chart", "title": "Velocità di Esecuzione Reparti", "urgency": "normal"},
    ],
    PHASE_EVENING: [
        {"id": "widget_tv_guide", "type": "media_guide", "title": "Guida TV Prima Serata & Film Consigliati", "urgency": "high"},
        {"id": "widget_home_relax", "type": "scene_controller", "title": "Scenario Domotico Relax Serale", "urgency": "normal"},
    ],
    PHASE_NIGHT: [
        {"id": "widget_night_guard", "type": "security_status", "title": "Sorveglianza Notturna & Modalità Riposo", "urgency": "low"},
    ],
}


@dataclass
class CircadianHabitTracker:
    history: dict[int, dict[str, int]] = field(default_factory=lambda: {h: {} for h in range(24)})

    def record_interaction(self, hour: int, widget_kind: str) -> None:
        h = max(0, min(hour, 23))
        counts = self.history.setdefault(h, {})
        counts[widget_kind] = counts.get(widget_kind, 0) + 1

    def top_habit_for_hour(self, hour: int) -> str | None:
        counts = self.history.get(hour, {})
        if not counts:
            return None
        return max(counts.items(), key=lambda x: x[1])[0]


_HABIT_TRACKER = CircadianHabitTracker()


def get_habit_tracker() -> CircadianHabitTracker:
    return _HABIT_TRACKER


def compute_current_phase(current_hour: int | None = None) -> str:
    hour = time.localtime().tm_hour if current_hour is None else current_hour
    if 6 <= hour < 9:
        return PHASE_MORNING
    elif 9 <= hour < 12:
        return PHASE_MARKET
    elif 12 <= hour < 20:
        return PHASE_PROJECTS
    elif 20 <= hour < 24:
        return PHASE_EVENING
    return PHASE_NIGHT


def resolve_circadian_context(
    current_hour: int | None = None,
    user_present: bool = True,
    custom_schedule: dict | None = None,
) -> dict:
    hour = time.localtime().tm_hour if current_hour is None else current_hour
    phase = compute_current_phase(hour)
    base_widgets = list(DEFAULT_PHASE_WIDGETS.get(phase, []))
    learned_habit = _HABIT_TRACKER.top_habit_for_hour(hour)
    if learned_habit:
        base_widgets.insert(0, {
            "id": f"widget_habit_{learned_habit}",
            "type": "learned_habit",
            "title": f"Abitudine Consolidata: {learned_habit.replace('_', ' ').title()}",
            "urgency": "high",
        })
    return {
        "hour": hour,
        "phase": phase,
        "user_present": user_present,
        "butler_mode": "proactive_morphing",
        "active_circadian_widgets": base_widgets,
        "learned_preference": learned_habit,
        "circadian_greeting": f"Contesto circadiano attivo: {phase.replace('_', ' ').title()}",
    }
