import time
from dataclasses import dataclass, field

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
    person_history: dict[str, dict[int, dict[str, int]]] = field(default_factory=dict)

    def record_interaction(self, hour: int, widget_kind: str, person_slug: str | None = None) -> None:
        h = max(0, min(hour, 23))
        counts = self.history.setdefault(h, {})
        counts[widget_kind] = counts.get(widget_kind, 0) + 1
        if person_slug:
            slug = str(person_slug).strip().lower()
            p_hist = self.person_history.setdefault(slug, {i: {} for i in range(24)})
            p_counts = p_hist.setdefault(h, {})
            p_counts[widget_kind] = p_counts.get(widget_kind, 0) + 1

    def top_habit_for_hour(self, hour: int, person_slug: str | None = None) -> str | None:
        h = max(0, min(hour, 23))
        if person_slug:
            slug = str(person_slug).strip().lower()
            p_counts = self.person_history.get(slug, {}).get(h, {})
            if p_counts:
                return max(p_counts.items(), key=lambda x: x[1])[0]
        counts = self.history.get(h, {})
        if not counts:
            return None
        return max(counts.items(), key=lambda x: x[1])[0]


_HABIT_TRACKER = CircadianHabitTracker()


def get_habit_tracker() -> CircadianHabitTracker:
    return _HABIT_TRACKER


def compute_current_phase(
    current_hour: int | None = None,
    wake_time: str | None = None,
    sleep_time: str | None = None,
) -> str:
    hour = time.localtime().tm_hour if current_hour is None else current_hour
    wake_h = 6
    if wake_time and ":" in str(wake_time):
        try:
            wake_h = int(str(wake_time).split(":")[0])
        except ValueError:
            pass
    sleep_h = 23
    if sleep_time and ":" in str(sleep_time):
        try:
            sleep_h = int(str(sleep_time).split(":")[0])
        except ValueError:
            pass

    eff_sleep_h = sleep_h if sleep_h >= wake_h else sleep_h + 24
    eff_hour = hour if hour >= wake_h else hour + 24

    morning_end = wake_h + 3
    market_end = wake_h + 6
    evening_start = max(market_end, eff_sleep_h - 4)

    if wake_h <= eff_hour < morning_end:
        return PHASE_MORNING
    elif morning_end <= eff_hour < market_end:
        return PHASE_MARKET
    elif market_end <= eff_hour < evening_start:
        return PHASE_PROJECTS
    elif evening_start <= eff_hour < eff_sleep_h:
        return PHASE_EVENING
    return PHASE_NIGHT


def resolve_circadian_context(
    current_hour: int | None = None,
    user_present: bool = True,
    custom_schedule: dict | None = None,
    person_slug: str | None = None,
    co_present_slugs: list[str] | None = None,
) -> dict:
    hour = time.localtime().tm_hour if current_hour is None else current_hour

    active_slug = person_slug
    if not active_slug:
        try:
            from state import store
            visible = store.presence.get("people") or []
            known = [p for p in visible if isinstance(p, dict) and p.get("known") and p.get("slug")]
            if known:
                active_slug = known[0]["slug"]
        except Exception:
            pass

    profile = None
    if active_slug:
        try:
            from agenti.people import people
            profile = people.load(active_slug)
        except Exception:
            pass

    wake_time = profile.get("wake_time") if profile else None
    sleep_time = profile.get("sleep_time") if profile else None

    phase = compute_current_phase(hour, wake_time, sleep_time)
    base_widgets = list(DEFAULT_PHASE_WIDGETS.get(phase, []))

    learned_habit = _HABIT_TRACKER.top_habit_for_hour(hour, active_slug)
    if learned_habit:
        base_widgets.insert(0, {
            "id": f"widget_habit_{learned_habit}",
            "type": "learned_habit",
            "title": f"Abitudine Consolidata: {learned_habit.replace('_', ' ').title()}",
            "urgency": "high",
        })

    person_passions = []
    person_tastes = {}
    person_habits = {}

    if profile:
        person_name = profile.get("first_name") or profile.get("name") or active_slug
        person_passions = list(profile.get("hobbies") or []) + list(profile.get("sports") or [])
        person_tastes = {
            "movies": profile.get("movies") or [],
            "music": profile.get("music") or [],
            "coffee": profile.get("coffee") or "",
            "food_likes": profile.get("food_likes") or [],
            "drinks": profile.get("drinks") or [],
        }
        person_habits = {
            "wake_time": wake_time,
            "sleep_time": sleep_time,
            "daily_habits": profile.get("daily_habits") or [],
            "quiet_hours": profile.get("quiet_hours") or "",
        }

        if phase == PHASE_MORNING and profile.get("coffee"):
            base_widgets.append({
                "id": "widget_personal_coffee",
                "type": "coffee_routine",
                "title": f"Caffè per {person_name}: {profile.get('coffee')}",
                "urgency": "normal",
            })

        if phase == PHASE_EVENING and profile.get("movies"):
            movies_str = ", ".join(profile.get("movies")[:2])
            base_widgets.append({
                "id": "widget_personal_cinema",
                "type": "cinema_recommendation",
                "title": f"Film & Serie Consigliati per {person_name} ({movies_str})",
                "urgency": "normal",
            })

        if profile.get("hobbies") and phase in (PHASE_PROJECTS, PHASE_EVENING):
            hobby_str = ", ".join(profile.get("hobbies")[:2])
            base_widgets.append({
                "id": "widget_personal_passion",
                "type": "passion_tracker",
                "title": f"Passioni & Tempo Libero ({hobby_str})",
                "urgency": "low",
            })

        greeting = f"Buongiorno {person_name}! Contesto circadiano attivo: {phase.replace('_', ' ').title()}" if phase == PHASE_MORNING else f"Ciao {person_name}! Contesto: {phase.replace('_', ' ').title()}"
    else:
        greeting = f"Contesto circadiano attivo: {phase.replace('_', ' ').title()}"

    privacy_masked = False
    co_present = list(co_present_slugs or [])
    if co_present:
        try:
            from agenti.people import people
            co_profiles = [people.load(s) for s in co_present if s]
            if any(cp and cp.get("role") in ("guest", "staff") for cp in co_profiles if cp) or "ospite" in co_present:
                privacy_masked = True
        except Exception:
            privacy_masked = True

    if privacy_masked:
        masked_widgets = []
        for w in base_widgets:
            if w.get("type") in ("market_ticker", "vitals_card", "security_status", "kanban_board"):
                masked_widgets.append({
                    **w,
                    "title": f"{w.get('title', '').split(':')[0]} (Discrezione Attiva per Ospiti)",
                    "privacy_masked": True,
                })
            else:
                masked_widgets.append(w)
        base_widgets = masked_widgets

    return {
        "hour": hour,
        "phase": phase,
        "user_present": user_present,
        "butler_mode": "proactive_morphing",
        "active_circadian_widgets": base_widgets,
        "learned_preference": learned_habit,
        "circadian_greeting": greeting,
        "person_slug": active_slug,
        "person_name": (profile.get("name") if profile else active_slug) if active_slug else None,
        "person_passions": person_passions,
        "person_tastes": person_tastes,
        "person_habits": person_habits,
        "privacy_co_presence_masked": privacy_masked,
        "co_present_slugs": co_present,
    }
