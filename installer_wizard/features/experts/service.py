import json
import time

from identity import assistant_name
from state import store

from features.agent import registry
from features.agent.paths import level
from features.authz import gate
from features.devstudio.rules import RULES
from features.experts import skills, templates
from features.experts.model import MAX_TOOLS, Expert, ExpertError, build, clean, slug
from features.experts.store import experts
from features.team.board import ACTING, board

MAX_STEPS = 8
BUILD_STEPS = 18
BUILD_GUIDE = (
    "\nProgetti complessi: con dev_new crea il progetto, con dev_plan salva il piano completo dei file, poi chiama dev_build ripetutamente "
    "finché non restano file in attesa (dev_status mostra lo stato e serve per riprendere un progetto esistente: non ricominciare mai da capo). "
    "Non scrivere un sito intero con un solo dev_write. Direttive obbligatorie per ogni codice:\n"
)
PENDING_TTL = 300
HISTORY_TURNS = 8
QUESTION_LIMIT = 2000
LANG_NAMES = {"it": "italiano", "en": "English", "es": "español", "fr": "français"}
FAILED = ("ERRORE", "NEGATO")
SKILL_STEP = "skill:"
_pending: dict[str, dict] = {}


class ExpertBusy(RuntimeError):
    pass


def board_key(expert_id: str) -> str:
    return f"expert:{expert_id}"


def known_tools() -> set[str]:
    return set(registry.TOOLS)


def reflect(expert: Expert) -> None:
    from features.fleet import mirror
    try:
        mirror.add(expert)
    except Exception as exc:
        store.event("WARN", f"Esperto {expert.id} non riportato nella flotta: {type(exc).__name__}", "experts")


def create(body: dict, lang: str, author: str) -> Expert:
    if not isinstance(body, dict):
        raise ExpertError("Richiesta non valida")
    template = str(body.get("template") or "")
    if template:
        try:
            raw = templates.blueprint(template, lang, "")
        except KeyError:
            raise ExpertError("Modello di esperto sconosciuto")
        raw.update({k: body[k] for k in ("instructions",) if body.get(k)})
    else:
        raw = {k: body.get(k) for k in ("role", "specialty", "knowledge", "tools", "skills", "instructions", "icon", "color")}
    raw["id"] = experts.free_id(slug(clean(raw.get("role"), 40) or "esperto"))
    expert = experts.put(build(raw, known_tools()), create=True)
    board.post(board_key(expert.id), "tutti", f"{expert.role} si unisce alla squadra", "creazione")
    store.event("INFO", f"Esperto {expert.id} creato da {author}", "experts")
    reflect(expert)
    return expert


BUILD_TOOLS = ("dev_plan", "dev_build", "dev_status")


def grant_build_tools() -> int:
    granted = 0
    for expert in experts.all():
        if "dev_write" in expert.tools and not all(t in expert.tools for t in BUILD_TOOLS):
            merged = list(dict.fromkeys(expert.tools + list(BUILD_TOOLS)))[:MAX_TOOLS]
            experts.put(build({**expert.to_dict(), "tools": merged}, known_tools()), create=False)
            granted += 1
    return granted


def seed_defaults(lang: str) -> list[str]:
    granted = grant_build_tools()
    if granted:
        store.event("INFO", f"{granted} esperti di programmazione hanno ora gli strumenti per i progetti complessi", "experts")
    done = experts.seeded()
    present = {e.template for e in experts.all() if e.template}
    created: list[str] = []
    for template in templates.ids():
        if template in done or template in present:
            done.add(template)
            continue
        raw = templates.blueprint(template, lang, experts.free_id(template))
        try:
            experts.put(build(raw, known_tools()), create=True)
        except ExpertError as exc:
            store.event("WARN", f"Esperto predefinito {template} non aggiunto: {exc}", "experts")
            continue
        done.add(template)
        created.append(template)
    experts.mark_seeded(done)
    if created:
        store.event("INFO", f"{len(created)} esperti predefiniti aggiunti alla squadra", "experts")
    return created


def update(expert_id: str, body: dict) -> Expert:
    current = experts.get(expert_id).to_dict()
    editable = ("role", "specialty", "knowledge", "tools", "skills", "instructions", "icon", "color", "enabled")
    current.update({k: body[k] for k in editable if k in body})
    return experts.put(build(current, known_tools()), create=False)


def delete(expert_id: str) -> None:
    experts.remove(expert_id)
    _pending.pop(expert_id, None)


def resolve(text: str) -> Expert:
    wanted = clean(text, 60).lower()
    rows = experts.all()
    for expert in rows:
        if wanted in (expert.id, expert.role.lower()):
            return expert
    for expert in rows:
        if wanted and (wanted in expert.role.lower() or wanted in expert.specialty.lower() or wanted == expert.template):
            return expert
    raise KeyError(text)


def _usable(names: list[str]) -> list[dict]:
    open_tools = {t["name"] for t in registry.available(level())}
    return [registry.TOOLS[n] for n in names if n in open_tools and gate.within_role(n)]


def _free_tools(expert: Expert) -> list[str]:
    covered = {t for s in expert.skills for t in skills.tools_of(s)}
    return [t for t in expert.tools if t not in covered]


def scope(expert: Expert, active: str | None) -> list[dict]:
    names = list(_free_tools(expert))
    if active:
        names += [t for t in skills.tools_of(active) if t in expert.tools]
    elif not expert.skills:
        names = list(expert.tools)
    return _usable(list(dict.fromkeys(names)))


def _listing(tools: list[dict]) -> str:
    return "\n".join(f"- {t['name']}({', '.join(f'{k}: {v}' for k, v in t['args'].items())}): {t['description']}" for t in tools)


def _system(expert: Expert, lang: str) -> str:
    knowledge = "\n".join(f"- {k}" for k in expert.knowledge)
    owner_rules = f"\nIstruzioni del proprietario: {expert.instructions}" if expert.instructions else ""
    catalog = "\n".join(f"- {c['id']}: {c['name']} — {c['purpose']}" for c in (skills.card(s, lang) for s in expert.skills))
    moves = ('{"skill": "id_competenza"} per attivare una competenza: carica la sua procedura e i suoi strumenti;\n' if expert.skills else "")
    build = BUILD_GUIDE + RULES if "dev_build" in expert.tools else ""
    return (
        f"Sei l'agente esperto «{expert.role}» della squadra di {assistant_name()}. Non hai un nome di persona.\n"
        f"Specialità: {expert.specialty}.\nConoscenze:\n{knowledge or '- generali del tuo ruolo'}{owner_rules}\n\n"
        + (f"Competenze disponibili (attivane una per usare i suoi strumenti, puoi cambiarla):\n{catalog}\n\n" if catalog else "")
        + "Lavori a ciclo: osserva, ragiona, agisci, verifica l'esito e ripeti finché l'obiettivo è raggiunto.\n"
        "Rispondi SEMPRE e SOLO con un oggetto JSON, uno di questi:\n" + moves
        + '{"tool": "nome_strumento", "args": {...}} per usare UNO strumento della competenza attiva e vederne l\'esito;\n'
        '{"answer": "risposta finale"} quando hai finito.\n'
        f"Regole: la risposta finale va scritta in {LANG_NAMES.get(lang, 'italiano')}, da esperto, chiara e concreta; "
        "usa gli strumenti per ogni dato che può cambiare nel tempo; non inventare esiti né numeri; se uno strumento fallisce "
        "prova un'alternativa o spiega il problema; se la domanda è fuori dalla tua specialità dillo." + build
    )


def _prompt(expert: Expert, question: str, steps: list[dict], active: str | None, lang: str, hint: str | None) -> str:
    past = experts.history(expert.id)[-HISTORY_TURNS:]
    convo = "\n".join(f"{'Utente' if t['role'] == 'user' else 'Esperto'}: {t['text'][:600]}" for t in past)
    done = "\n".join(f"{i + 1}. {s['tool']}({json.dumps(s['args'], ensure_ascii=False)[:300]}) → {s['result'][:1500]}"
                     for i, s in enumerate(steps))
    tools = scope(expert, active)
    parts = [f"Conversazione recente:\n{convo}" if convo else "", f"Obiettivo: {question}"]
    if active:
        parts.append(skills.briefing(active, lang))
    elif hint:
        parts.append(f"Competenza suggerita per questa domanda: {hint}")
    parts.append(f"Strumenti utilizzabili ora:\n{_listing(tools) or '- nessuno: attiva una competenza o rispondi'}")
    parts.append(f"Passi già eseguiti:\n{done}\n\nProssima mossa?" if steps else "Prima mossa?")
    return "\n\n".join(p for p in parts if p)


def _active(steps: list[dict]) -> str | None:
    for s in reversed(steps):
        if s["tool"].startswith(SKILL_STEP) and not s["result"].startswith(FAILED):
            return s["tool"][len(SKILL_STEP):]
    return None


def _show(expert: Expert, question: str, status: str, steps: list[dict], lang: str, answer: str = "") -> None:
    active = _active(steps)
    try:
        from features.desktop.desk import desk
        desk.show("expert_work", {"role": expert.role, "specialty": expert.specialty, "icon": expert.icon, "color": expert.color,
                                  "skill": skills.card(active, lang)["name"] if active else "",
                                  "question": question[:240], "status": status, "answer": answer[:400],
                                  "steps": [{"tool": s["tool"], "ok": not s["result"].startswith(FAILED)} for s in steps][-8:]},
                  key=f"expert:{expert.id}", ttl=90 if status == "done" else 600)
    except (ImportError, AttributeError) as exc:
        store.event("WARN", f"Widget esperto non mostrato: {exc}", "experts")


async def _execute(expert: Expert, name: str, args: dict, steps: list[dict]) -> None:
    from features.team import runner
    key = board_key(expert.id)
    shown = json.dumps(registry.clean_args(name, args), ensure_ascii=False)[:120]
    token = ACTING.set(key)
    board.begin(key, f"{name} {shown}")
    try:
        gate.require_tool(name)
        result = await runner.execute(name, args, key)
    except Exception as exc:
        result = f"ERRORE: {str(exc)[:300]}"
    finally:
        ACTING.reset(token)
    board.end(key)
    board.post(key, "tutti", f"{name}: {result[:140]}", "errore" if result.startswith(FAILED) else "esito")
    steps.append({"tool": name, "args": registry.clean_args(name, args), "result": result})


def _activate(expert: Expert, skill_id: str, steps: list[dict], lang: str) -> None:
    if skill_id not in expert.skills:
        steps.append({"tool": f"{SKILL_STEP}{skill_id[:40]}", "args": {}, "result": "ERRORE: competenza non posseduta da questo esperto"})
        return
    card = skills.card(skill_id, lang)
    board.post(board_key(expert.id), "tutti", f"competenza attivata: {card['name']}", "competenza")
    steps.append({"tool": f"{SKILL_STEP}{skill_id}", "args": {}, "result": f"attivata: {card['name']}"})


async def _loop(expert: Expert, question: str, lang: str, steps: list[dict]) -> dict:
    from features.brain.llm import BrainUnavailable, generate
    system = _system(expert, lang)
    hint = skills.suggest(expert.skills, question)
    for _ in range(BUILD_STEPS if "dev_build" in expert.tools else MAX_STEPS):
        active = _active(steps)
        _show(expert, question, "thinking", steps, lang)
        try:
            move = await generate(_prompt(expert, question, steps, active, lang, hint), as_json=True, max_tokens=900,
                                  temperature=0.15, kind="deep", system=system, timeout=240)
        except BrainUnavailable as exc:
            return {"text": f"Il modello non è raggiungibile ({exc}).", "steps": steps, "error": "brain"}
        move = move if isinstance(move, dict) else {}
        if move.get("skill") and not move.get("tool"):
            _activate(expert, str(move["skill"]), steps, lang)
            continue
        if move.get("answer") or not move.get("tool"):
            return {"text": str(move.get("answer") or "").strip()[:4000], "steps": steps}
        name, args = str(move["tool"]), move.get("args") if isinstance(move.get("args"), dict) else {}
        allowed = {t["name"] for t in scope(expert, active)}
        if name not in allowed:
            reason = "attiva prima la competenza che lo contiene" if name in expert.tools else "strumento non assegnato a questo esperto"
            steps.append({"tool": name, "args": {}, "result": f"ERRORE: {reason}"})
            continue
        if registry.needs_confirm(name, args):
            problem = registry.precheck(name, args)
            if problem:
                steps.append({"tool": name, "args": registry.clean_args(name, args), "result": f"ERRORE: {problem}"})
                continue
            _pending[expert.id] = {"question": question, "lang": lang, "steps": steps, "tool": name, "args": args, "at": time.time()}
            return {"text": "", "steps": steps, "pending": {"tool": name, "args": registry.clean_args(name, args)}}
        _show(expert, question, "working", steps, lang)
        await _execute(expert, name, args, steps)
    done = sum(1 for s in steps if not s["result"].startswith(FAILED) and not s["tool"].startswith(SKILL_STEP))
    return {"text": f"Ho eseguito {done} passi senza arrivare a una risposta completa.", "steps": steps, "error": "steps"}


def _finish(expert: Expert, question: str, out: dict, lang: str) -> dict:
    if out.get("pending"):
        _show(expert, question, "waiting", out["steps"], lang)
        return out
    text = out["text"] or "Nessuna risposta."
    row = experts.remember(expert.id, "expert", text, out["steps"])
    _show(expert, question, "done", out["steps"], lang, text)
    return {**out, "text": text, "turn": row}


async def ask(expert_id: str, question: str, lang: str, origin: str = "console") -> dict:
    expert = experts.get(expert_id)
    if not expert.enabled:
        raise ExpertError("Questo esperto è spento")
    question = clean(question, QUESTION_LIMIT)
    if len(question) < 2:
        raise ExpertError("Domanda vuota")
    if board.current().get(board_key(expert.id)):
        raise ExpertBusy(expert.role)
    lang = templates.lang_of(lang)
    _pending.pop(expert.id, None)
    experts.remember(expert.id, "user", question)
    board.post(origin, board_key(expert.id), question[:200], "domanda")
    return _finish(expert, question, await _loop(expert, question, lang, []), lang)


def pending(expert_id: str) -> dict | None:
    item = _pending.get(expert_id)
    if item and time.time() - item["at"] > PENDING_TTL:
        _pending.pop(expert_id, None)
        return None
    return {"tool": item["tool"], "args": registry.clean_args(item["tool"], item["args"])} if item else None


async def confirm(expert_id: str, yes: bool) -> dict:
    expert = experts.get(expert_id)
    if pending(expert_id) is None:
        raise LookupError(expert_id)
    item = _pending.pop(expert_id)
    steps = item["steps"]
    if not yes:
        steps.append({"tool": item["tool"], "args": registry.clean_args(item["tool"], item["args"]), "result": "NEGATO: rifiutato dal proprietario"})
    else:
        await _execute(expert, item["tool"], item["args"], steps)
    return _finish(expert, item["question"], await _loop(expert, item["question"], item["lang"], steps), item["lang"])
