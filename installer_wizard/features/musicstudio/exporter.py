import json

from features.musicstudio import library, schema as S, store
from features.shares import archive


def save(project: dict, wav: bytes) -> dict:
    root = archive.folder("produzioni")
    name = f"{archive.clean(project['title'] or project['prompt'], 'canzone')[:50]}-{project['id']}"
    target = root / name
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{archive.clean(project['title'] or 'mix', 'mix')[:50]}.wav").write_bytes(wav)
    (target / "progetto.json").write_text(json.dumps(project, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if project["lyrics"]["text"]:
        body = project["lyrics"]["text"] + "".join(f"\n\n--- {lang} ---\n{text}" for lang, text in project["lyrics"]["translations"].items())
        (target / "testo.txt").write_text(body, encoding="utf-8")
    audio = store.audio_dir(project["id"])
    used = {c["vocal"]["asset"] for t in project["tracks"] for c in t["clips"] if c.get("vocal") and c["vocal"]["asset"]}
    if used:
        (target / "voci").mkdir(exist_ok=True)
        for asset in used:
            if S.ID_RE.fullmatch(asset.split(".")[0]) and (audio / asset).is_file():
                (target / "voci" / asset).write_bytes((audio / asset).read_bytes())
    try:
        shelf = library.publish(project, wav)
    except OSError:
        shelf = ""
    return {"folder": name, "library": shelf}
