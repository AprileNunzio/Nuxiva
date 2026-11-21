import re

from agenti.desktop.desk import desk
from agenti.models3d import generator, library, voice
from state import store
from tasks import background

VERB = (r"(?!\w*at[oaie]\b)(?:cre[aiou]\w*|fa(?:i|mmi|resti|rebbe|re|rmi)|fammi|disegn\w*|modell\w*|gener\w*|progett\w*|costru\w*"
        r"|stamp\w*|realizz\w*|prepar\w*)")
CREATE = re.compile(r"\b" + VERB + r"\b(?:\s+(?:mi|me|ci|per\s+me|pure|subito|gentilmente|per\s+favore))*\s*"
                    r"(?:(?:una|uno|un|il|la|lo|dei|delle)\s+|un')?"
                    r"(modello\s+(3d\s+)?(di|del|della|dello)\s+(?:(?:una|uno|un)\s+|un')?)?(?P<what>.+?)\s*"
                    r"\b(in\s+3\s*d|3\s*d|tridimensional[ei]|in\s+tre\s+dimensioni)\b", re.I)
CREATE_MODEL = re.compile(r"\b" + VERB + r"\b(?:\s+(?:mi|me|ci))*\s+(un|il)\s+modello\s+(3d|tridimensionale)\s+(di|del|della)\s+"
                          r"(?:(?:una|uno|un)\s+|un')?(?P<what>.+)$", re.I)
SHOW = re.compile(r"\b(mostra|mostrami|apri|aprimi|fammi vedere|visualizza|riapri)\b\s*(il|la|lo|l')?\s*"
                  r"(modello|file|oggetto)?\s*(3d\s+)?(?P<what>.*)$", re.I)
CLOSE = re.compile(r"\b(chiudi|nascondi|togli)\b.*\b(modello|visualizzatore|3d|oggetto)\b", re.I)
LIST = re.compile(r"\b(quali|che)\s+modelli\s+(3d\s+)?(hai|ci sono|abbiamo)\b|\belenca\b.*\bmodelli\b", re.I)
HOLOGRAM = re.compile(r"\b(?:mostr\w*|cre\w*|gener\w*|proiett\w*)\s+(?:mi\s+)?(?:l\s*['’]?\s*|un\s+)?ologramma\s+(?:3d\s+)?(?:di|del|della|dello)\s+(?:(?:una|uno|un)\s+|un['’]?)?(?P<what>.+?)[.?!]*$", re.I)
UPGRADE_PBR = re.compile(r"\b(?:ora\s+)?(?:rendil[oa]|fall[oa]|trasformal[oa]|passa\s+a)\s+.*\b(?:realistic[oa]|fotorealistic[oa]|pbr|sfumatur\w*|gta)\b", re.I)
UPGRADE_3D = re.compile(r"\b(?:ora\s+)?(?:rendil[oa]|fall[oa]|trasformal[oa])\s+(?:in\s+)?(?:3\s*d|tridimensional[ei]|solid[oa])\b", re.I)


async def _build(subject: str) -> None:
    try:
        meta = await generator.create(subject)
    except Exception as exc:
        store.event("WARN", f"Generazione 3D di «{subject}» non riuscita: {exc}", "models3d")
        desk.show("notice", {"title": "Modello 3D", "text": f"Non sono riuscito a progettare «{subject}»."}, ttl=20)
        return
    store.event("INFO", f"Modello 3D creato: {meta['title']} ({len(meta.get('parts', []))} parti)", "models3d")
    library.show(meta, f"Ecco {meta['title']} in 3D. Puoi ruotarlo e scaricarlo in GLB, STL o OBJ.")


async def answer(text: str) -> tuple[str, dict]:
    if h := HOLOGRAM.search(text):
        from agenti.hands import spatial_hud
        subject = h.group("what").strip()
        await spatial_hud.spatial_hud_generate_object(subject, "particles")
        return f"Ecco l'ologramma particellare di {subject} sullo Spatial HUD.", {"mode": "face"}
    if UPGRADE_PBR.search(text):
        from agenti.hands import spatial_hud
        await spatial_hud.spatial_hud_set_fidelity("photoreal_pbr")
        return "Rendering evoluto a fotorealismo PBR con sfumature, riflessi clearcoat e illuminazione fisica.", {"mode": "face"}
    if UPGRADE_3D.search(text):
        from agenti.hands import spatial_hud
        await spatial_hud.spatial_hud_set_fidelity("mesh_3d")
        return "Ologramma convertito in geometria 3D solida.", {"mode": "face"}
    try:
        return voice.answer(text)
    except LookupError:
        pass
    m = CREATE_MODEL.search(text) or CREATE.search(text)
    if m:
        subject = re.sub(r"[.?!]+$", "", m.group("what")).strip()
        if subject:
            background(_build(subject))
            return f"Sto progettando {subject} in 3D: te lo mostro appena è pronto.", {"mode": "face"}
    if CLOSE.search(text):
        desk.hide("viewer_3d")
        return "Chiuso.", {"mode": "face"}
    if LIST.search(text):
        names = [m["title"] for m in library.listing()[:8]]
        if not names:
            return "Non ho ancora nessun modello 3D: chiedimi di crearne uno, per esempio «creami un martello in 3D».", {"mode": "face"}
        return "Ho questi modelli 3D: " + ", ".join(names) + ".", {"mode": "face"}
    s = SHOW.search(text)
    if s and re.search(r"\b(3d|modell|file|oggett)", text, re.I):
        meta = library.find(s.group("what") or "") or (library.listing() or [None])[0]
        if meta:
            library.show(meta)
            return f"Ecco {meta['title']}.", {"mode": "face"}
    raise LookupError

