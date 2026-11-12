import itertools
import re
from typing import Any, Mapping, Sequence

MAX_VARIANTS = 128
PREFIXES = ("", "per favore ", "ehi nuxiva ", "nuxiva ", "please ", "hey nuxiva ")
SUFFIXES = ("", " per favore", " grazie", " please", " adesso", " now")
PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_]*)\}")


def _fillings(utterance: str, schema: Sequence[Mapping[str, Any]]) -> list[str]:
    names = PLACEHOLDER.findall(utterance)
    if not names:
        return [utterance]
    options = {item["name"]: [str(v) for v in item.get("allowed_values") or []] for item in schema}
    if any(not options.get(name) for name in names):
        return []
    filled = []
    for combo in itertools.product(*(options[name] for name in names)):
        text = utterance
        for name, value in zip(names, combo):
            text = text.replace("{" + name + "}", value, 1)
        filled.append(text)
    return filled


def expand(utterances: Sequence[str], schema: Sequence[Mapping[str, Any]]) -> tuple[list[str], int]:
    originals: list[str] = []
    for utterance in utterances:
        for text in _fillings(utterance, schema):
            if text not in originals:
                originals.append(text)
    seen = set(originals)
    synthetic: list[str] = []
    for base in originals:
        for prefix, suffix in itertools.product(PREFIXES, SUFFIXES):
            variant = f"{prefix}{base}{suffix}".strip()
            if variant in seen or len(seen) >= MAX_VARIANTS:
                continue
            seen.add(variant)
            synthetic.append(variant)
    return originals + synthetic, len(synthetic)
