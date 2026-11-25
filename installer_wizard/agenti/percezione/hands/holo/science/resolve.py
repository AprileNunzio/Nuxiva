import logging
from collections import OrderedDict

import httpx

from agenti.hands.holo.catalog import fetch
from agenti.hands.holo.science import build, sources

log = logging.getLogger("nuxiva.hands.holo.science")
ERRORS = (httpx.HTTPError, fetch.FetchError, ValueError, TimeoutError, OSError, UnicodeError)
PROTEINS = {"hemoglobin": "4HHB", "haemoglobin": "4HHB", "insulin": "4INS", "myoglobin": "1MBN", "lysozyme": "1LYZ",
            "green fluorescent protein": "1EMA", "gfp": "1EMA", "antibody": "1IGT", "immunoglobulin": "1IGT"}
PROTEIN_WORDS = ("protein", "enzyme", "proteins", "enzymes")
MOLECULE_WORDS = ("molecule", "molecules", "molecular", "compound", "chemical")
FILLER = ("structure", "model", "the", "of", "a", "an", "3d", "in", "show", "me", "how", "is", "made", "what", "looks", "like")
MIN_ATOMS_UNASKED = 3
CACHE = OrderedDict()
CACHE_SIZE = 48
MISSING = ("holo_http_404", "holo_no_protein", "holo_no_molecule", "holo_bad_name", "holo_bad_model", "holo_too_large")
CREDITS = {"pubchem": ("PubChem (NIH)", "Public domain"), "rcsb": ("RCSB Protein Data Bank", "CC0 1.0")}


def _words(english: str) -> list[str]:
    return [w for w in "".join(c if c.isalnum() or c in " -" else " " for c in english.lower()).split() if w]


def classify(english: str, local_words: dict) -> tuple[str, str, bool]:
    from agenti.hands.holo.commands import norm
    words = _words(english)
    local = norm(local_words.get("subject", ""))
    protein = any(w in PROTEIN_WORDS for w in words) or any(f" {w} " in local for w in local_words.get("protein", []))
    molecule = any(w in MOLECULE_WORDS for w in words) or any(f" {w} " in local for w in local_words.get("molecule", []))
    name = " ".join(w for w in words if w not in PROTEIN_WORDS + MOLECULE_WORDS + FILLER)
    if name in PROTEINS:
        return "protein", name, True
    return ("protein" if protein else "molecule"), name, protein or molecule


def _remember(key: str, value: dict | None) -> dict | None:
    CACHE[key] = value
    CACHE.move_to_end(key)
    while len(CACHE) > CACHE_SIZE:
        CACHE.popitem(last=False)
    return value


def _credited(scene: dict, source: str, page: str, name: str) -> dict:
    author, license_name = CREDITS[source]
    scene["credit"] = {"name": name, "author": author, "license": license_name, "page": page}
    return scene


async def _protein(name: str, title: str, notify) -> dict:
    notify("science_searching", source="RCSB PDB")
    pdb_id = PROTEINS.get(name) or await sources.rcsb_search(name)
    text, page = await sources.rcsb(pdb_id)
    notify("science_found", name=pdb_id, source="RCSB PDB")
    return _credited(build.scene("pdb", text, title), "rcsb", page, pdb_id)


async def _molecule(name: str, title: str, asked: bool, notify) -> dict | None:
    notify("science_searching", source="PubChem")
    text, page = await sources.pubchem(name)
    scene = build.scene("sdf", text, title)
    atoms = sum(1 for p in scene["parts"] if p["name"].startswith("atom_"))
    if atoms < MIN_ATOMS_UNASKED and not asked:
        return None
    notify("science_found", name=name, source="PubChem")
    return _credited(scene, "pubchem", page, name)


async def find(subject: str, english: str, local_words: dict, notify=lambda key, **params: None) -> dict | None:
    kind, name, asked = classify(english or subject, {**local_words, "subject": subject})
    if len(name) < 2:
        return None
    key = f"{kind}:{name}"
    if key in CACHE:
        return CACHE[key]
    try:
        if kind == "protein":
            found = await _protein(name, subject, notify)
        else:
            found = await _molecule(name, subject, asked, notify)
    except ERRORS as exc:
        log.info("struttura scientifica di «%s» non trovata: %s", subject, exc)
        if asked:
            notify("science_missing", name=name)
        missing = str(exc) in MISSING
        return _remember(key, None) if missing else None
    return _remember(key, found)
