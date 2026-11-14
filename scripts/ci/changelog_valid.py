import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME = re.compile(r"^([0-9]{8})([0-9]{6})-[a-z0-9]+(?:-[a-z0-9]+)*\.json$")
DATE = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$")
LANGS = ("it", "en", "fr", "es")
MAX_FILE = 16 * 1024
MAX_TITLE = 140
MAX_ITEM = 320
MAX_ITEMS = 24
INVISIBLE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f​-‏‪-‮⁦-⁩﻿]")


def texts(value: object, limit: int) -> str | None:
    if not isinstance(value, dict) or set(value) != set(LANGS):
        return "lingue it/en/fr/es obbligatorie / it/en/fr/es languages required"
    for lang in LANGS:
        text = value[lang]
        if not isinstance(text, str) or not text.strip():
            return f"testo vuoto in {lang} / empty text in {lang}"
        if len(text) > limit:
            return f"{lang}: {len(text)} caratteri, limite {limit} / {len(text)} characters, limit {limit}"
        if INVISIBLE.search(text):
            return f"{lang}: caratteri di controllo o invisibili / control or invisible characters"
    return None


def check(path: Path) -> str | None:
    match = NAME.match(path.name)
    if not match:
        return "nome non valido / invalid name"
    raw = path.read_bytes()
    if len(raw) > MAX_FILE:
        return "file oltre 16 KB / file over 16 KB"
    try:
        note = json.loads(raw)
    except ValueError:
        return "JSON non valido / invalid JSON"
    required = {"schema", "date", "title"}
    if not isinstance(note, dict) or not required <= set(note) or not set(note) <= required | {"features", "fixes"}:
        return "campi ammessi: schema,date,title,features,fixes / allowed fields: schema,date,title,features,fixes"
    if note["schema"] != 1:
        return "schema diverso da 1 / schema other than 1"
    date = note["date"]
    if not isinstance(date, str) or not DATE.match(date) or date.replace("-", "") != match.group(1):
        return f"date '{date}' deve essere AAAA-MM-GG uguale al prefisso del nome / date must be YYYY-MM-DD equal to the name prefix"
    problem = texts(note["title"], MAX_TITLE)
    if problem:
        return f"title: {problem}"
    sections = (note.get("features", []), note.get("fixes", []))
    if not all(isinstance(section, list) and len(section) <= MAX_ITEMS for section in sections):
        return "features e fixes devono essere liste di al massimo 24 voci / features and fixes must be lists of at most 24 entries"
    if not any(sections):
        return "nessuna voce / no entries"
    for name, section in zip(("features", "fixes"), sections):
        for index, item in enumerate(section):
            problem = texts(item, MAX_ITEM)
            if problem:
                return f"{name}[{index}]: {problem}"
    return None


def main() -> int:
    broken = 0
    for path in sorted((ROOT / "changelog").glob("*.json")):
        problem = check(path)
        if problem:
            broken += 1
            print(f"::error file=changelog/{path.name}::{problem}")
    if broken:
        return 1
    print("Note di rilascio valide / Release notes valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
