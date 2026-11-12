import re

from features.desktop.desk import desk
from features.diorama import export, service, spec as S, store
from tasks import background

NOUN = r"(?:diorama|diorami|plastico|modellino\s+in\s+miniatura|scena\s+in\s+miniatura)"
CREATE_VERB = (r"(?:cre[aiou]\w*|costru\w*|realizz\w*|fa(?:i|mmi|re|rmi)|fammi|genera\w*|progett\w*|disegn\w*|prepar\w*|inventa\w*|componi\w*|compon\w*)")
CREATE = re.compile(rf"\b{CREATE_VERB}\b(?:\s+(?:mi|me|ci|per\s+me|pure|subito|per\s+favore))*\s+(?:(?:un|uno|una|il|lo|la|l')\s*)?{NOUN}\b(?P<what>.*)$", re.I)
SHOW = re.compile(rf"\b(?:mostra\w*|apri\w*|riapri\w*|rivedi|fammi\s+vedere|visualizza)\b.*\b{NOUN}\b(?P<what>.*)$", re.I)
VISUAL = re.compile(r"^\W*(?:(?:per\s+favore|dai|su|jarvis)\s+)*(?:mostr\w*|(?:fa|fai|fammi|facci|voglio)\s+vedere|fammi\s+un\s+vedere)\s+(?:(?:mi|ci)\s+)?"
                    r"(?:(?:un|uno|una|il|lo|la|l')\s*|(?:dei|delle|degli)\s+)(?P<what>[^\W\d_][^.?!]{1,70})\W*$", re.I)
NOT_VISUAL = re.compile(r"\b(?:modell\w*|3\s*d|file|foto\w*|video|immagin\w*|camera|telecamer\w*|meteo|film|canale|app|applicazion\w*|finestr\w*|widget|"
                        r"schermat\w*|pannell\w*|log|elenco|lista|documento|document\w*|mappa|partit\w*|risultat\w*|orologio|ora|data|calendario|"
                        r"messaggi\w*|email|mail|canzon\w*|musica|diorama|diorami|grafico|tabella|password|conto|volto|faccia|avatar|ologramma|"
                        r"sorgente|codice|errore|errori|stato|sistema|dispositiv\w*|stanza|casa|giardino\s+di\s+casa)\b", re.I)
LIST = re.compile(rf"\b(?:quali|che|elenca)\b.*\b{NOUN}\b", re.I)
CLOSE = re.compile(rf"\b(?:chiudi|nascondi|togli|esci\s+da\w*)\b.*\b{NOUN}\b", re.I)
EDIT = re.compile(r"\b(?:aggiung\w*|inserisc\w*|togli|rimuov\w*|elimin\w*|cancell\w*|sposta\w*|muov\w*|ruota\w*|ingrandisc\w*|rimpicciolisc\w*|colora\w*|cambia\w*|trasforma\w*|rendi|metti|pianta\w*|sostituisc\w*|raddoppia|dimezza|allunga\w*|allarga\w*|accorcia\w*|fai|fammi|aggiorna\w*)\b", re.I)
FOREIGN = re.compile(r"\b(?:luce|luci|musica|volume|temperatura|accendi|spegni|tv|televisione|sveglia|timer|canale|film|canzone|telefon\w*|messaggio|email|mail|meteo|termostato|sistema|riavvia)\b", re.I)
LIGHTS = (
    (re.compile(r"\b(?:tramonto|ora\s+d.?\s*oro|golden|alba|controluce)\b", re.I), "golden_hour"),
    (re.compile(r"\b(?:ora\s+blu|crepuscolo|imbrunire|sera)\b", re.I), "blue_hour"),
    (re.compile(r"\b(?:notte|notturn\w*|di\s+notte|luna)\b", re.I), "night"),
    (re.compile(r"\b(?:mezzogiorno|pieno\s+giorno|sole\s+pieno|di\s+giorno|sole\s+alto)\b", re.I), "noon"),
    (re.compile(r"\b(?:nuvolos\w*|coperto|nuvole|grigio|nebbi\w*\s+diffus\w*)\b", re.I), "overcast"),
)
LENSES = (
    (re.compile(r"\bmacro\b", re.I), "macro"),
    (re.compile(r"\btilt[\s-]?shift\b|\beffetto\s+miniatura\b", re.I), "tilt_shift"),
    (re.compile(r"\b50\s*(?:mm|millimetri)\b|\bobiettivo\s+normale\b|\bstandard\b", re.I), "standard_50mm"),
)
LOOK_VERB = re.compile(r"\b(?:fai|metti|passa|passiamo|cambia|imposta|rendi|vedi|mostra|usa|voglio|portami|con|a)\b", re.I)
SHARPER = re.compile(r"\b(?:pi[uù]\s+nitid\w*|meno\s+sfocat\w*|meno\s+sfocatura|nitido|togli\s+(?:la\s+)?sfocatura)\b", re.I)
BLURRIER = re.compile(r"\b(?:pi[uù]\s+sfocat\w*|pi[uù]\s+sfocatura|sfoca\s+(?:di\s+pi[uù]|molto)|aumenta\s+(?:la\s+)?sfocatura)\b", re.I)
MISTIER = re.compile(r"\b(?:pi[uù]\s+(?:nebbia|foschia)|aggiungi\s+(?:della\s+)?(?:nebbia|foschia))\b", re.I)
CLEARER = re.compile(r"\b(?:meno\s+(?:nebbia|foschia)|togli\s+(?:la\s+)?(?:nebbia|foschia)|aria\s+limpida)\b", re.I)
TOP = re.compile(r"\b(?:dall.?\s*alto|vista\s+(?:aerea|dall.?\s*alto)|pi[uù]\s+in\s+alto|da\s+sopra)\b", re.I)
LOW = re.compile(r"\b(?:livello\s+(?:degli\s+)?occhi|pi[uù]\s+in\s+basso|rasoterra|dal\s+basso|vista\s+bassa)\b", re.I)
STOP = re.compile(r"\b(?:ferma|smetti|blocca|non\s+far)\w*\b.*\b(?:rotazione|girare|ruotare|orbita)\b|\bferma\s+la\s+camera\b", re.I)
GO = re.compile(r"\b(?:riavvia|fai\s+girare|riprendi|attiva)\b.*\b(?:rotazione|orbita|camera|giro)\b", re.I)
SPEAK = {"golden_hour": "Ora d'oro.", "blue_hour": "Ora blu.", "night": "Notte.", "noon": "Mezzogiorno.", "overcast": "Cielo coperto."}
LENS_SPEAK = {"macro": "Obiettivo macro.", "tilt_shift": "Effetto tilt-shift.", "standard_50mm": "Obiettivo 50 millimetri."}


def active() -> str | None:
    for item in reversed(list(desk.instances.values())):
        if item.get("id") == "diorama" and S.ID_RE.fullmatch(str((item.get("data") or {}).get("id", ""))):
            return item["data"]["id"]
    return None


def present(did: str, immersive: bool = True, ttl: float = 0) -> None:
    key = f"diorama:{did}"
    desk.show("diorama", {"id": did}, key=key, priority=88 if immersive else 40, ttl=ttl)
    if immersive:
        desk.fullscreen(key, True)


def _clean(subject: str) -> str:
    return re.sub(r"^\s*(?:di|del|della|dello|dei|delle|con|su|:)\s+", "", subject.strip().strip(".?!"), flags=re.I).strip()


def _look(did: str, text: str) -> str | None:
    record = store.load(did)
    look = record["look"]
    patch: dict = {}
    spoken = ""
    for pattern, value in LIGHTS:
        if pattern.search(text) and LOOK_VERB.search(text):
            patch["light"], spoken = value, SPEAK[value]
            break
    for pattern, value in LENSES:
        if pattern.search(text):
            patch["lens"], spoken = value, LENS_SPEAK[value]
            break
    if BLURRIER.search(text):
        patch["blur"], spoken = min(1.0, look["blur"] + 0.2), "Più sfocatura."
    elif SHARPER.search(text):
        patch["blur"], spoken = max(0.0, look["blur"] - 0.2), "Più nitido."
    if MISTIER.search(text):
        patch["mist"], spoken = min(0.5, look["mist"] + 0.1), "Più foschia."
    elif CLEARER.search(text):
        patch["mist"], spoken = max(0.0, look["mist"] - 0.1), "Aria più limpida."
    if TOP.search(text):
        patch["angle"], spoken = min(85.0, look["angle"] + 22), "Inquadratura più alta."
    elif LOW.search(text):
        patch["angle"], spoken = max(10.0, look["angle"] - 18), "Inquadratura più bassa."
    if STOP.search(text):
        patch["orbit"], spoken = False, "Camera ferma."
    elif GO.search(text):
        patch["orbit"], spoken = True, "Camera in rotazione."
    if not patch:
        return None
    record["look"] = S.clean_look({**look, **patch})
    record["revision"] += 1
    store.save(record)
    export.save(did)
    return spoken


async def _refine(did: str, text: str) -> None:
    try:
        await service.refine(did, text)
    except S.SpecError:
        return


async def answer(text: str) -> tuple[str, dict]:
    face = {"mode": "face"}
    if CLOSE.search(text):
        did = active()
        if did:
            desk.dismiss(f"diorama:{did}")
        return "Chiuso.", face
    if LIST.search(text):
        names = [row["title"] or "senza titolo" for row in store.listing()[:8]]
        if not names:
            return "Non ho ancora nessun diorama: chiedimi per esempio «crea un diorama di una stazione giapponese con i ciliegi».", face
        return "Ho questi diorami: " + ", ".join(names) + ".", face
    m = CREATE.search(text)
    if m:
        subject = _clean(m.group("what")) or text
        try:
            record = service.create(subject)
        except S.SpecError as exc:
            return ("Descrivimi meglio la scena." if str(exc) == "prompt_short" else "Ho raggiunto il numero massimo di diorami: elimina qualcosa e riprova."), face
        present(record["id"])
        return "Comincio a costruirlo: lo vedrai nascere pezzo per pezzo.", face
    v = VISUAL.match(text)
    if v and not NOT_VISUAL.search(text) and not FOREIGN.search(text):
        subject = _clean(v.group("what"))
        if len(subject) >= 3:
            try:
                record = service.create(subject)
            except S.SpecError:
                raise LookupError
            present(record["id"])
            return (f"Ecco {record['title'] or subject}." if record["items"] else f"Lo costruisco: {subject}."), face
    s = SHOW.search(text)
    if s:
        rows = store.listing()
        what = _clean(s.group("what")).lower()
        row = next((r for r in rows if what and what in (r["title"] or "").lower()), rows[0] if rows else None)
        if not row:
            return "Non ho ancora nessun diorama da mostrarti.", face
        present(row["id"])
        return f"Ecco {row['title'] or 'il diorama'}.", face
    did = active()
    if not did:
        raise LookupError
    try:
        spoken = _look(did, text)
    except KeyError:
        raise LookupError
    if spoken:
        return spoken, face
    if EDIT.search(text) and not FOREIGN.search(text) and service.status(did)["state"] != "building":
        background(_refine(did, text))
        return "Va bene, lo modifico.", face
    if service.status(did)["state"] == "building" and EDIT.search(text) and not FOREIGN.search(text):
        return "Sto ancora costruendo: aspetta un attimo e poi dimmi cosa cambiare.", face
    raise LookupError
