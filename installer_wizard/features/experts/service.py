import json
import time

from identity import assistant_name
from state import store

from features.agent import registry
from features.agent.paths import level
from features.authz import gate
from features.experts import templates
from features.experts.model import Expert, ExpertError, build, clean, slug
from features.experts.store import experts
from features.team.board import ACTING, board

MAX_STEPS = 6
PENDING_TTL = 300
HISTORY_TURNS = 8
QUESTION_LIMIT = 2000
LANG_NAMES = {"it": "italiano", "en": "English", "es": "español", "fr": "français"}
FAILED = ("ERRORE", "NEGATO")
_pending: dict[str, dict] = {}


class ExpertBusy(RuntimeError):
    pass


def board_key(expert_id: str) -> str:
    return f"expert:{expert_id}"


def known_tools() -> set[str]:
    return set(registry.TOOLS)


def create(body: dict, lang: str, author: str) -> Expert:
    if not isinstance(body, dict):
        raise ExpertError("Richiesta non valida")
    template = str(body.get("template") or "")
    if template:
        try:
            raw = templates.blueprint(template, lang, "")
        except KeyError:
            raise ExpertError("Modello di esperto sconosciuto")
        raw.update({k: body[k] for k in ("name", "instructions") if body.get(k)})
    else:
        raw = {k: body.get(k) for k in ("name", "role", "specialty", "knowledge", "tools", "instructions", "icon", "color")}
    raw["id"] = experts.free_id(slug(clean(raw.get("name"), 40) or "esperto"))
    expert = experts.put(build(raw, known_tools()), create=True)
    board.post(board_key(expert.id), "tutti", f"{expert.name} si unisce alla squadra come {expert.role}", "creazione")
    store.event("INFO", f"Esperto {expert.id} creato da {author}", "experts")
    return expert


def update(expert_id: str, body: dict) -> Expert:
    current = experts.get(expert_id).to_dict()
    editable = ("name", "role", "specialty", "knowledge", "tools", "instructions", "icon", "color", "enabled")
    current.update({k: body[k] for k in editable if k in body})
    return experts.put(build(current, known_tools()), create=False)


def delete(expert_id: str) -> None:
    experts.remove(expert_id)
    _pending.pop(expert_id, None)


def resolve(text: str) -> Expert:
    wanted = clean(text, 60).lower()
    rows = experts.all()
    for expert in rows:
        if wanted in (expert.id, expert.name.lower()):
            return expert
    for expert in rows:
        if wanted and (wanted in expert.role.lower() or wanted in expert.specialty.lower() or wanted == expert.template):
            return expert
    raise KeyError(text)


def _allowed(expert: Expert) -> list[dict]:
    open_tools = {t["name"] for t in registry.available(level())}
    return [registry.TOOLS[n] for n in expert.tools if n in open_tools and gate.within_role(n)]


def _system(expert: Expert, lang: str, tools: list[dict]) -> str:
    listed = "\n".join(f"- {t['name']}({', '.join(f'{k}: {v}' for k, v in t['args'].items())}): {t['description']}" for t in tools)
    knowledge = "\n".join(f"- {k}" for k in expert.knowledge)
    owner_rules = f"\nIstruzioni del proprietario: {expert.instructions}" if expert.instructions else ""
    return (
        f"Sei {expert.name}, {expert.role}, membro della squadra di esperti di {assistant_name()}.\n"
        f"Specialità: {expert.specialty}.\nConoscenze:\n{knowledge or '- generali del tuo ruolo'}{owner_rules}\n\n"
        f"Strumenti che puoi usare (solo questi):\n{listed or '- nessuno: rispondi con le tue conoscenze'}\n\n"
        "Rispondi SEMPRE e SOLO con un oggetto JSON, uno di questi due:\n"
        '{"tool": "nome_strumento", "args": {...}} per usare UNO strumento e vederne l\'esito;\n'
        '{"answer": "risposta finale"} quando hai finito.\n'
        f"Regole: la risposta finale va scritta in {LANG_NAMES.get(lang, 'italiano')}, da esperto, chiara e concreta; "
        "usa gli strumenti per ogni dato che può cambiare nel tempo; non inventare esiti né numeri; "
        "se uno strumento fallisce dillo e proponi un'alternativa; se la domanda è fuori dalla tua specialità dillo."
    )


def _prompt(expert: Expert, question: str, steps: list[dict]) -> str:
    past = experts.history(expert.id)[-HISTORY_TURNS:]
    convo = "\n".join(f"{'Utente' if t['role'] == 'user' else expert.name}: {t['text'][:600]}" for t in past)
    done = "\n".join(f"{i + 1}. {s['tool']}({json.dumps(s['args'], ensure_ascii=False)[:300]}) → {s['result'][:1500]}"
                     for i, s in enumerate(steps))
    head = f"Conversazione recente:\n{convo}\n\n" if convo else ""
    return head + f"Domanda: {question}\n\n" + (f"Passi già eseguiti:\n{done}\n\nProssima mossa?" if steps else "Prima mossa?")


def _show(expert: Expert, question: str, status: str, steps: list[dict], answer: str = "") -> None:
    try:
        from features.desktop.desk import desk
        desk.show("expert_work", {"name": expert.name, "role": expert.role, "icon": expert.icon, "color": expert.color,
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


async def _loop(expert: Expert, question: str, lang: str, steps: list[dict]) -> dict:
    from features.brain.llm import BrainUnavailable, generate
    tools = _allowed(expert)
    allowed = {t["name"] for t in tools}
    system = _system(expert, lang, tools)
    for _ in range(MAX_STEPS):
        _show(expert, question, "thinking", steps)
        try:
            move = await generate(_prompt(expert, question, steps), as_json=True, max_tokens=900, temperature=0.15,
                                  kind="deep", system=system, timeout=240)
        except BrainUnavailable as exc:
            return {"text": f"{expert.name}: il modello non è raggiungibile ({exc}).", "steps": steps, "error": "brain"}
        move = move if isinstance(move, dict) else {}
        if move.get("answer") or not move.get("tool"):
            return {"text": str(move.get("answer") or "").strip()[:4000], "steps": steps}
        name, args = str(move["tool"]), move.get("args") if isinstance(move.get("args"), dict) else {}
        if name not in allowed:
            steps.append({"tool": name, "args": {}, "result": "ERRORE: strumento non assegnato a questo esperto"})
            continue
        if registry.needs_confirm(name, args):
            problem = registry.precheck(name, args)
            if problem:
                steps.append({"tool": name, "args": registry.clean_args(name, args), "result": f"ERRORE: {problem}"})
                continue
            _pending[expert.id] = {"question": question, "lang": lang, "steps": steps, "tool": name, "args": args, "at": time.time()}
            return {"text": "", "steps": steps, "pending": {"tool": name, "args": registry.clean_args(name, args)}}
        _show(expert, question, "working", steps)
        await _execute(expert, name, args, steps)
    done = sum(1 for s in steps if not s["result"].startswith(FAILED))
    return {"text": f"{expert.name}: ho eseguito {done} passi senza arrivare a una risposta completa.", "steps": steps, "error": "steps"}


def _finish(expert: Expert, question: str, out: dict) -> dict:
    if out.get("pending"):
        _show(expert, question, "waiting", out["steps"])
        return out
    text = out["text"] or f"{expert.name}: nessuna risposta."
    row = experts.remember(expert.id, "expert", text, out["steps"])
    _show(expert, question, "done", out["steps"], text)
    return {**out, "text": text, "turn": row}


async def ask(expert_id: str, question: str, lang: str, origin: str = "console") -> dict:
    expert = experts.get(expert_id)
    if not expert.enabled:
        raise ExpertError("Questo esperto è spento")
    question = clean(question, QUESTION_LIMIT)
    if len(question) < 2:
        raise ExpertError("Domanda vuota")
    if board.current().get(board_key(expert.id)):
        raise ExpertBusy(expert.name)
    lang = templates.lang_of(lang)
    _pending.pop(expert.id, None)
    experts.remember(expert.id, "user", question)
    board.post(origin, board_key(expert.id), question[:200], "domanda")
    return _finish(expert, question, await _loop(expert, question, lang, []))


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
    return _finish(expert, item["question"], await _loop(expert, item["question"], item["lang"], steps))
