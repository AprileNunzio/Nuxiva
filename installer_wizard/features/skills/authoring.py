import re
from features.skills.library import CATEGORIES, check_code, library

NAME_LIMIT = 60
TEXT_LIMIT = 500
CODE_LIMIT = 20000
PATTERN_LIMIT = 200
GENERIC_PROBES = ("ciao come stai", "")


class AuthoringError(ValueError):
    pass


def _text(value, limit: int, field: str) -> str:
    text = str(value or "").strip()
    if not text or len(text) > limit:
        raise AuthoringError(f"{field} mancante o troppo lungo")
    return text


def _patterns(raw) -> list[str]:
    if not isinstance(raw, list) or not 1 <= len(raw) <= 4:
        raise AuthoringError("servono da 1 a 4 modelli di riconoscimento")
    found = []
    for item in raw:
        pattern = _text(item, PATTERN_LIMIT, "modello")
        try:
            re.compile(pattern, re.I)
        except re.error as exc:
            raise AuthoringError(f"modello non valido: {exc}")
        found.append(pattern)
    return found


def clean_spec(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise AuthoringError("richiesta non valida")
    category = raw.get("category") if raw.get("category") in CATEGORIES else "altro"
    code = _text(raw.get("code"), CODE_LIMIT, "codice")
    try:
        check_code(code)
    except (SyntaxError, ValueError) as exc:
        raise AuthoringError(str(exc))
    examples = [str(e).strip()[:120] for e in (raw.get("examples") or []) if str(e).strip()][:5]
    return {"name": _text(raw.get("name"), NAME_LIMIT, "nome"), "category": category,
            "description": str(raw.get("description") or "").strip()[:200], "patterns": _patterns(raw.get("patterns")),
            "examples": examples, "code": code}


async def create(raw: dict, probe: str) -> str:
    spec = clean_spec(raw)
    text = _text(probe, TEXT_LIMIT, "frase di prova")
    try:
        key = await library._install(spec, text, source="user")
    except ValueError as exc:
        raise AuthoringError(str(exc))
    if not key:
        raise AuthoringError("algoritmo non creato")
    return key


async def replace_code(key: str, code: str) -> None:
    item = library.skills.get(key)
    if item is None:
        raise KeyError(key)
    if item["source"] == "system":
        raise AuthoringError("Gli algoritmi di sistema non si modificano")
    code = _text(code, CODE_LIMIT, "codice")
    try:
        check_code(code)
    except (SyntaxError, ValueError) as exc:
        raise AuthoringError(str(exc))
    probe = str((item.get("test") or {}).get("input") or (item.get("examples") or [""])[0])
    if not probe:
        raise AuthoringError("nessuna frase di prova per verificare il codice")
    path = item["path"]
    previous = path.read_text(encoding="utf-8")
    path.write_text(code, encoding="utf-8")
    out = await library.worker.call(path, probe)
    if not out.get("ok"):
        path.write_text(previous, encoding="utf-8")
        raise AuthoringError(f"prova fallita: {out.get('error') or 'nessun risultato'}")
    library.signature = ""
    library.scan()


async def generate(description: str) -> str:
    if not library.enabled() or not library.may_generate():
        raise AuthoringError("la creazione automatica e' disattivata")
    text = _text(description, TEXT_LIMIT, "descrizione")
    from features.brain.llm import BrainUnavailable, generate as ask
    last = "nessuna risposta utile"
    for temperature in (0.2, 0.45):
        try:
            spec = await ask(library.prompt_for(text), as_json=True, max_tokens=1400, temperature=temperature, kind="deep", prefer=[])
            key = await library._install(spec, text, source="ai")
            if key:
                return key
        except BrainUnavailable:
            raise AuthoringError("nessun modello disponibile per scrivere l'algoritmo")
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            last = str(exc)[:160]
    raise AuthoringError(f"creazione non riuscita: {last}")


