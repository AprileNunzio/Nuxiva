import time

from features.people import people
from features.people.wellbeing import prompts, protocol, safety, store
from features.people.wellbeing.scoring import meter

SAVE_BASELINE_EVERY = 120.0
HISTORY_TURNS = 12
_saved: dict[str, float] = {}


async def llm(prompt: str, system: str, as_json: bool = False, max_tokens: int = 450):
    from features.brain.llm import generate
    return await generate(prompt, system=system, as_json=as_json, max_tokens=max_tokens, temperature=0.5, kind="chat")


def ingest(slug: str, raw: dict, now: float | None = None) -> dict | None:
    now = now or time.time()
    if not isinstance(raw, dict):
        return None
    allowed = store.consent(slug)
    if allowed and slug not in _saved:
        saved = store.load_baseline(slug)
        if saved and not meter.baseline(slug).warm:
            meter.load(slug, saved)
        _saved[slug] = now
    reading = meter.ingest(slug, raw, now)
    if allowed and not reading["calibrating"]:
        store.add_reading(slug, reading, now)
        if now - _saved.get(slug, 0.0) >= SAVE_BASELINE_EVERY:
            store.save_baseline(slug, meter.baseline(slug).export())
            _saved[slug] = now
    return reading


def live(slug: str, now: float | None = None) -> dict | None:
    return meter.live(slug, now or time.time())


def _name(slug: str) -> str:
    profile = people.load(slug) or {}
    return str(profile.get("nickname") or profile.get("name") or slug).split()[0]


def _context(slug: str) -> str:
    past = [s for s in store.sessions(slug, 4) if s["ended"]][:3]
    lines = []
    for s in reversed(past):
        digest = store.summary(s["id"]) or {}
        lines.append(f"- {time.strftime('%d/%m', time.localtime(s['started']))}: {digest.get('summary', '')[:300]}")
    now_state = live(slug)
    if now_state:
        lines.append(f"Segnale del volto in questo momento (stima non clinica): area {now_state['area']}, attivazione {now_state['arousal']}/100.")
    return "\n".join(lines) or "Nessun incontro precedente."


def _system(session: dict, slug: str) -> str:
    lang = prompts.LANG_NAMES.get(session["lang"], "English")
    return (f"{prompts.RULES}\nRispondi sempre in {lang}. Persona: {_name(slug)}.\n{prompts.STAGE_GOALS[session['stage']]}\n"
            f"{prompts.PHASE_GOALS[session['phase']]}\nContesto:\n{_context(slug)}")


def _fallback(phase: str, lang: str, name: str, index: int) -> str:
    options = prompts.FALLBACK[phase].get(lang) or prompts.FALLBACK[phase]["en"]
    return options[min(index, len(options) - 1) if phase != "central" else index % len(options)].format(name=name)


def _transcript(sid: str) -> str:
    rows = store.turns(sid)[-HISTORY_TURNS:]
    return "\n".join(f"{'Persona' if r['role'] == 'user' else 'Tu'}: {r['text']}" for r in rows)


async def _reply(session: dict, slug: str, user_turns: int) -> str:
    from features.brain.llm import BrainUnavailable
    try:
        text = await llm(f"Conversazione finora:\n{_transcript(session['id'])}\n\nScrivi la tua prossima risposta.", _system(session, slug))
        text = str(text).strip()
        if text:
            return text
    except BrainUnavailable:
        pass
    return _fallback(session["phase"], session["lang"], _name(slug), user_turns)


def _refresh_phase(session: dict, user_turns: int, now: float) -> dict:
    phase = protocol.phase_for(session["started"], session["central_at"], user_turns, now, bool(session["closing"]))
    fields = {"phase": phase}
    if phase == "central" and session["central_at"] is None:
        fields["central_at"] = now
    if phase != session["phase"] or "central_at" in fields:
        store.update_session(session["id"], **fields)
    return store.session(session["id"])


def state(slug: str, now: float | None = None) -> dict:
    now = now or time.time()
    plan = store.plan(slug)
    active = store.open_session(slug)
    return {"consent": store.consent(slug), "plan": {**plan, "due": protocol.due(plan["next_at"], now)}, "live": live(slug, now),
            "session": _public(active, slug) if active else None}


def _public(session: dict, slug: str) -> dict:
    return {"id": session["id"], "stage": session["stage"], "phase": session["phase"], "started": session["started"],
            "central_at": session["central_at"], "turns": store.turns(session["id"]), "slug": slug}


async def start(slug: str, lang: str, mood_before=None, now: float | None = None) -> dict:
    now = now or time.time()
    if not store.consent(slug):
        raise PermissionError("consenso mancante")
    existing = store.open_session(slug)
    if existing:
        return {**_public(existing, slug), "resumed": True}
    plan = store.plan(slug)
    if plan["concluded"]:
        store.save_plan(slug, "consolidation", None, False)
        plan = store.plan(slug)
    mood = int(mood_before) if isinstance(mood_before, (int, float)) and 0 <= int(mood_before) <= 10 else None
    session = store.new_session(slug, plan["stage"], safety.lang_of(lang), mood, now)
    greeting = await _reply(session, slug, 0)
    store.add_turn(session["id"], "assistant", "opening", greeting, now)
    return {**_public(store.session(session["id"]), slug), "resumed": False}


async def turn(slug: str, sid: str, text: str, now: float | None = None) -> dict:
    now = now or time.time()
    session = store.session(sid)
    if not session or session["slug"] != slug or session["ended"]:
        raise LookupError("seduta non trovata")
    text = " ".join(str(text or "").split())[:store.MAX_TEXT]
    if not text:
        raise ValueError("messaggio vuoto")
    store.add_turn(sid, "user", session["phase"], text, now)
    if safety.detect(text):
        store.update_session(sid, risk=session["risk"] + 1)
        answer = safety.response(session["lang"])
        store.add_turn(sid, "assistant", session["phase"], answer, now)
        return {"reply": answer, "phase": session["phase"], "crisis": True, "nearing_end": False}
    user_turns = sum(1 for t in store.turns(sid) if t["role"] == "user")
    session = _refresh_phase(session, user_turns, now)
    answer = await _reply(session, slug, user_turns)
    store.add_turn(sid, "assistant", session["phase"], answer, now)
    return {"reply": answer, "phase": session["phase"], "crisis": False, "nearing_end": protocol.nearing_end(session["central_at"], now)}


def _digest(sid: str, turns: list[dict]) -> dict:
    said = [t["text"] for t in turns if t["role"] == "user"]
    return {"summary": " ".join(said)[:400], "themes": [], "emotions": [], "reported": said[:3], "strengths": [], "homework": [], "for_professional": []}


async def _summarise(session: dict, slug: str) -> dict:
    from features.brain.llm import BrainUnavailable
    turns = store.turns(session["id"])
    system = f"{prompts.RULES}\nRispondi in {prompts.LANG_NAMES.get(session['lang'], 'English')}."
    try:
        data = await llm(f"Conversazione:\n{_transcript(session['id'])}\n\n{prompts.SUMMARY_SCHEMA}", system, as_json=True, max_tokens=700)
    except BrainUnavailable:
        data = None
    base = _digest(session["id"], turns)
    if not isinstance(data, dict):
        return base
    clean = dict(base)
    for key in ("summary",):
        clean[key] = str(data.get(key, base[key]))[:900]
    for key in ("themes", "emotions", "reported", "strengths", "homework", "for_professional"):
        value = data.get(key)
        clean[key] = [str(v)[:200] for v in value[:6]] if isinstance(value, list) else base[key]
    return clean


def _improving(slug: str, stage: str) -> bool:
    rows = [s for s in reversed(store.sessions(slug)) if s["stage"] == stage and s["ended"] and s["mood_after"] is not None]
    if len(rows) < 6:
        return False
    first = sum(s["mood_after"] for s in rows[:3]) / 3
    last = sum(s["mood_after"] for s in rows[-3:]) / 3
    return last >= first + 1


async def close(slug: str, sid: str, mood_after=None, now: float | None = None) -> dict:
    now = now or time.time()
    session = store.session(sid)
    if not session or session["slug"] != slug:
        raise LookupError("seduta non trovata")
    if session["ended"]:
        return {"summary": store.summary(sid), "plan": store.plan(slug)}
    store.update_session(sid, closing=1, phase="closing")
    session = store.session(sid)
    digest = await _summarise(session, slug)
    store.save_summary(sid, digest)
    rating = int(mood_after) if isinstance(mood_after, (int, float)) and 0 <= int(mood_after) <= 10 else None
    store.update_session(sid, ended=now, mood_after=rating)
    plan = store.plan(slug)
    done = sum(1 for s in store.sessions(slug) if s["stage"] == plan["stage"] and s["ended"])
    stage, concluded = protocol.advance(plan["stage"], done, _improving(slug, plan["stage"]))
    in_stage = done if stage == plan["stage"] else 0
    store.save_plan(slug, stage, None if concluded else protocol.schedule(stage, in_stage, now), concluded)
    return {"summary": digest, "plan": store.plan(slug)}


def forget(slug: str) -> None:
    meter.forget(slug)
    _saved.pop(slug, None)
    store.erase(slug)
