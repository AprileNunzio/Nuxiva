import os
import re
import time
from typing import List, Set

CACHE_TTL = 60.0
_CACHE = {"at": 0.0, "words": []}
STOPWORDS = frozenset({
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una",
    "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
    "e", "o", "ed", "od", "del", "dello", "della", "dei", "degli", "delle",
    "al", "allo", "alla", "ai", "agli", "alle",
    "dal", "dallo", "dalla", "dai", "dagli", "dalle",
    "nel", "nello", "nella", "nei", "negli", "nelle",
    "sul", "sullo", "sulla", "sui", "sugli", "sulle",
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "by", "for", "with",
    "stato", "stato_di", "sensore", "pulsante", "interruttore"
})
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9'-]{2,30}")


def _assistant_name() -> str:
    try:
        from identity import assistant_name
        return assistant_name()
    except Exception:
        name = os.environ.get("NUXIVA_ASSISTANT_NAME", "").strip()
        return name.capitalize() if name else "Nuxiva"


def _clean_term(raw: str) -> str:
    text = " ".join(str(raw or "").replace("_", " ").split()).strip(" .:,;-_'\"")
    return text if 2 <= len(text) <= 40 else ""


def _extract_words(phrase: str) -> List[str]:
    cleaned = _clean_term(phrase)
    if not cleaned:
        return []
    out = []
    tokens = WORD_RE.findall(cleaned)
    if len(tokens) > 1 and len(cleaned) <= 35:
        out.append(cleaned)
    for tok in tokens:
        lower = tok.lower()
        if lower not in STOPWORDS and not lower.isdigit() and len(tok) >= 3:
            out.append(tok.capitalize() if tok.islower() else tok)
    return out


def _get_brain_catalog():
    try:
        from features.home_assistant.home import brain
        return getattr(brain, "catalog", None)
    except Exception:
        return None


def _get_places_store():
    try:
        from features.places.store import store
        return store
    except Exception:
        return None


def _get_learner():
    try:
        from learner import learner
        return learner
    except Exception:
        try:
            from features.ear.learner import learner
            return learner
        except Exception:
            return None


def _collect_family_names() -> List[str]:
    names: List[str] = []
    learner_obj = _get_learner()
    if learner_obj is not None:
        try:
            base = learner_obj.hotwords()
            items = base if isinstance(base, (list, tuple, set)) else str(base or "").split()
            for token in items:
                cleaned = _clean_term(token)
                if cleaned and cleaned.lower() not in STOPWORDS:
                    names.append(cleaned.capitalize() if cleaned.islower() else cleaned)
        except Exception:
            pass
    return names


def _collect_home_assistant_terms() -> List[str]:
    terms: List[str] = []
    catalog = _get_brain_catalog()
    if catalog is not None:
        try:
            for entity in getattr(catalog, "entities", {}).values():
                name = entity.get("name") or entity.get("device_name") or ""
                for word in _extract_words(name):
                    terms.append(word)
            for area in getattr(catalog, "areas", {}).values():
                area_name = area.get("name") or ""
                for word in _extract_words(area_name):
                    terms.append(word)
            for floor in getattr(catalog, "floors", {}).values():
                floor_name = floor.get("name") or ""
                for word in _extract_words(floor_name):
                    terms.append(word)
        except Exception:
            pass
    return terms


def _collect_places_terms() -> List[str]:
    terms: List[str] = []
    store_obj = _get_places_store()
    if store_obj is not None:
        try:
            rooms = getattr(store_obj, "rooms", {})
            room_list = rooms.values() if isinstance(rooms, dict) else rooms
            for room in room_list:
                name = room.get("name", "") if isinstance(room, dict) else getattr(room, "name", "")
                for word in _extract_words(name):
                    terms.append(word)
                aliases = room.get("aliases", []) if isinstance(room, dict) else getattr(room, "aliases", [])
                for alias in aliases or []:
                    for word in _extract_words(alias):
                        terms.append(word)
            floors = getattr(store_obj, "floors", {})
            floor_list = floors.values() if isinstance(floors, dict) else floors
            for floor in floor_list:
                name = floor.get("name", "") if isinstance(floor, dict) else getattr(floor, "name", "")
                for word in _extract_words(name):
                    terms.append(word)
        except Exception:
            pass
    return terms


def home_vocabulary_list(lang_or_limit=None, limit: int = 50) -> List[str]:
    actual_limit = limit
    if isinstance(lang_or_limit, int):
        actual_limit = lang_or_limit
    now = time.time()
    if _CACHE["words"] and (now - _CACHE["at"] < CACHE_TTL):
        return list(_CACHE["words"][:actual_limit])

    seen: Set[str] = set()
    result: List[str] = []

    name = _assistant_name()
    if name:
        seen.add(name.lower())
        result.append(name)

    for item in _collect_family_names() + _collect_home_assistant_terms() + _collect_places_terms():
        key = item.lower()
        if key not in seen and len(result) < actual_limit * 2:
            seen.add(key)
            result.append(item)

    _CACHE["at"] = now
    _CACHE["words"] = result
    return result[:actual_limit]


def home_vocabulary_string(limit: int = 40) -> str:
    words = home_vocabulary_list(limit=limit)
    return ", ".join(words)


def hotwords_string(lang: str = "it") -> str:
    words = home_vocabulary_list(limit=50)
    return " ".join(words)


def deepgram_keywords(limit: int = 25) -> List[str]:
    return home_vocabulary_list(limit=limit)


def gemini_prompt(lang: str = "it") -> str:
    vocab = home_vocabulary_string(limit=50)
    if not vocab:
        if lang == "en":
            return "Transcribe exactly and word for word what is said in this audio. Return ONLY the literal transcription, without commentary or quotation marks."
        return "Trascrivi esattamente e parola per parola cosa viene detto in questo audio. Restituisci SOLO ed ESCLUSIVAMENTE la trascrizione letterale, senza commenti né virgolette."
    if lang == "en":
        return f"Transcribe exactly and word for word what is said in this audio. Return ONLY the literal transcription, without commentary or quotation marks. Helpful home vocabulary (devices, rooms, scenes, people): {vocab}."
    return f"Trascrivi esattamente e parola per parola cosa viene detto in questo audio. Restituisci SOLO ed ESCLUSIVAMENTE la trascrizione letterale, senza commenti né virgolette. Vocaboli e termini utili del contesto domestico (dispositivi, stanze, scene, persone): {vocab}."


def openai_prompt(lang: str = "it") -> str:
    vocab = home_vocabulary_string(limit=35)
    name = _assistant_name()
    if not vocab:
        return f"Ehi, {name}."
    return f"Ehi, {name}. Vocaboli: {vocab}."[:350]


def invalidate_cache() -> None:
    _CACHE["at"] = 0.0
    _CACHE["words"] = []
