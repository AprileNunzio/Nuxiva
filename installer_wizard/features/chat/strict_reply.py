import json
import operator
import re
import unicodedata

from features.chat.code import extract

SORT = re.compile(r"(?:ordina|sort)\s+(?:in ordine alfabetico|alfabeticamente|alphabetically)\s*:?[ \t]*(.{1,1000})", re.I)
ITEM = re.compile(r"[^\W\d_]+(?:[ '-][^\W\d_]+)*")
NUMBER = re.compile(r"(?:quanto fa|what is)\s+(-?\d{1,12})\s*(per|times|[×*+−-])\s*(-?\d{1,12})\s*\?\s*(?:rispondi solo con il numero|reply with only the number)\.?", re.I)
OPERATIONS = {"per": operator.mul, "times": operator.mul, "×": operator.mul, "*": operator.mul,
              "+": operator.add, "−": operator.sub, "-": operator.sub}
JSON_ONLY = re.compile(r"^(?:estrai|rispondi(?:\s+con)?|restituisci|extract|return)\s+(?:solo\s+(?:con\s+)?(?:un\s+)?json|only\s+json)\b", re.I)
CHAT_ONLY = re.compile(r"\b(?:(?:soltanto|solo)\s+in\s+chat|(?:only|just)\s+in\s+chat|non\s+creare\s+(?:alcun\s+)?file|do not create (?:any )?files)\b", re.I)


def deterministic(text: str) -> str | None:
    if match := NUMBER.fullmatch(text.strip()):
        left, operation, right = match.groups()
        return str(OPERATIONS[operation.lower()](int(left), int(right)))
    if match := SORT.fullmatch(text.strip()):
        items = [part.strip() for part in match[1].removesuffix(".").split(",")]
        if len(items) > 1 and all(ITEM.fullmatch(item) for item in items):
            return ", ".join(sorted(items, key=lambda item: unicodedata.normalize("NFKD", item.casefold())))
    return None


def json_reply(reply: str) -> str | None:
    _, blocks = extract(reply)
    candidate = blocks[0]["content"] if len(blocks) == 1 else reply.strip()
    try:
        value = json.loads(candidate)
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (ValueError, RecursionError):
        return None
    return None
