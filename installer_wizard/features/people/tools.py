from features.agent.registry import tool
from features.people import mood as mood_journal
from features.people import people


def _person(name: str) -> dict:
    wanted = people.slugify(str(name or ""))
    profile = people.load(wanted)
    if profile:
        return profile
    lowered = str(name or "").strip().lower()
    for p in people.all_profiles(light=True):
        if lowered and lowered in (people.display_name(p).lower(), str(p.get("nickname") or "").lower(), str(p.get("first_name") or "").lower()):
            return p
    raise ValueError(f"persona «{name}» non trovata in anagrafe")


@tool("person_learn", "memorizza qualcosa di stabile imparato su una persona di casa (gusto, abitudine, fatto della sua vita)",
      {"person": "nome o identificativo della persona", "fact": "cosa hai imparato, in una frase"}, agent="people")
async def person_learn(person: str, fact: str) -> str:
    profile = _person(person)
    if not profile.get("consent", True):
        raise PermissionError(f"{people.display_name(profile)} non ha dato il consenso alla personalizzazione")
    from features.mind.mind import mind
    saved = mind.memory.add(str(fact), kind="persona", score=0.7, who=profile["slug"])
    if not saved:
        raise ValueError("ricordo troppo corto")
    mind.publish()
    return f"memorizzato su {people.display_name(profile)}: {saved['text']}"


@tool("person_mood", "annota lo stato d'animo che una persona ti ha espresso (non dedurlo: solo se lo dice o è evidente da ciò che dice)",
      {"person": "nome o identificativo", "mood": "uno tra " + ", ".join(mood_journal.MOODS), "intensity": "da 1 a 5", "note": "motivo in breve"},
      agent="people")
async def person_mood(person: str, mood: str, intensity: int = 3, note: str = "") -> str:
    profile = _person(person)
    if not profile.get("consent", True):
        raise PermissionError(f"{people.display_name(profile)} non ha dato il consenso alla personalizzazione")
    entry = mood_journal.record(profile["slug"], mood, intensity, note, "assistente")
    return f"annotato: {people.display_name(profile)} si sente {entry['mood']} ({entry['intensity']}/5)"


@tool("person_profile", "riassunto di ciò che sai di una persona: anagrafica essenziale, abitudini e ultimo stato d'animo",
      {"person": "nome o identificativo"}, agent="people")
async def person_profile(person: str) -> str:
    profile = _person(person)
    if not profile.get("consent", True):
        return f"{people.display_name(profile)} non ha dato il consenso: posso dire solo il nome"
    last = mood_journal.latest(profile["slug"])
    feeling = f" Ultimo stato d'animo: {last['mood']} ({last['intensity']}/5)." if last else ""
    return people.context_for([profile["slug"]]) + " " + people.habits(profile)["summary"] + feeling
