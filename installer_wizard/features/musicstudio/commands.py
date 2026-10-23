import re

from features.desktop.desk import desk
from features.musicstudio import lyrics as lyr, schema as S, service, store, voicebank

CREATE = re.compile(r"\b(?:cre\w+|compon\w+|fa(?:mmi|i)|scriv\w+|produc\w+|produ\w+|invent\w+|gener\w+|realizz\w+)\b(?:\s+(?:mi|ci|per\s+me))*\s+(?:(?:una|un|uno|il|la|dei|delle)\s+)?"
                    r"(?:nuov[ao]\s+)?(?:canzone|brano|pezzo\s+musicale|base\s+musicale|base|beat|strumentale|jingle|colonna\s+sonora)\b(?P<what>.*)$", re.I)
OPEN = re.compile(r"\b(?:apri|aprimi|riapri|mostra\w*)\b.*\b(?:studio\s+musicale|progetto\s+musicale|canzone|brano)\b(?P<what>.*)$", re.I)
LIST = re.compile(r"\b(?:quali|che|elenca)\b.*\b(?:canzoni|brani|progetti\s+musicali)\b.*\b(?:ho|hai|abbiamo|ci\s+sono|creat\w+)\b", re.I)
LAYER = re.compile(r"\baggiung\w*\b\s+(?:(?:una|un|uno|dei|delle|la|il|l')\s*)?(?P<what>batteria|basso|accordi|pad|arpeggio|arpeggiatore|melodia|synth|lead|effetti\s+speciali|riser)\b", re.I)
VOCAL = re.compile(r"\b(?:aggiung\w*|metti|inserisci|fai\s+cantare|canta)\b.*\b(?:voce|cantato|testo|cantante)\b", re.I)
TRANSLATE = re.compile(r"\btradu\w+\b.*\b(?:canzone|testo|brano)\b.*\b(?:in|nella\s+lingua)\s+(?P<lang>\w+)", re.I)
TEMPO = re.compile(r"\b(?:tempo|bpm|velocit\w+)\b.*?(\d{2,3})\b|\b(?P<rel>pi[uù]\s+veloce|pi[uù]\s+lent\w+)\b", re.I)
EFFECT = re.compile(r"\baggiung\w*\b\s+(?:(?:un|uno|una|il|la|l')\s*)?(?P<fx>riverbero|eco|delay|distorsione|saturazione|chorus|compressore|phaser|equalizzatore|filtro)\b(?:\s+(?:al|alla|allo|sul|sulla|a)\s+(?:la\s+)?(?P<target>\w+))?", re.I)
ROLE_WORDS = {"batteria": "drums", "basso": "bass", "accordi": "chords", "pad": "pad", "arpeggio": "arp", "arpeggiatore": "arp", "melodia": "lead", "synth": "lead", "lead": "lead",
              "effetti speciali": "fx", "riser": "fx", "voce": "vocal"}
FX_WORDS = {"riverbero": "reverb", "eco": "delay", "delay": "delay", "distorsione": "distortion", "saturazione": "distortion", "chorus": "chorus", "compressore": "compressor",
            "phaser": "phaser", "equalizzatore": "eq3", "filtro": "filter"}
LANG_WORDS = {"inglese": "en", "francese": "fr", "spagnolo": "es", "tedesco": "de", "portoghese": "pt", "giapponese": "ja", "olandese": "nl", "polacco": "pl", "russo": "ru", "italiano": "it"}
REVOICE = re.compile(r"\b(?:usa|metti|cambia|canta)\w*\b.*\bvoce\s+(?:di\s+|della\s+|del\s+)?(?P<who>[a-zà-ù]+)\b", re.I)
state = {"active": ""}


def active() -> str:
    if state["active"]:
        try:
            store.load(state["active"])
            return state["active"]
        except KeyError:
            state["active"] = ""
    rows = store.listing()
    return rows[0]["id"] if rows else ""


def _announce(project: dict, text: str) -> None:
    desk.show("notice", {"title": "Studio Musicale", "text": text}, ttl=20)


async def answer(text: str) -> tuple[str, dict]:
    face = {"mode": "face"}
    m = CREATE.search(text)
    if m:
        what = S.text(m.group("what"), 400).strip(" :,.") or text
        try:
            project = service.create(f"{what} {('(' + text + ')') if what != text else ''}".strip())
        except S.SpecError as exc:
            return ("Descrivimi meglio la canzone." if str(exc) == "prompt_short" else "Ho raggiunto il numero massimo di progetti musicali."), face
        state["active"] = project["id"]
        _announce(project, f"Sto componendo: {what}. Lo trovi in Applicazioni › Studio Musicale.")
        return "Mi metto al lavoro: scelgo genere, tonalità e strumenti, poi scrivo il testo. Lo trovi nello Studio Musicale.", face
    if LIST.search(text):
        rows = store.listing()
        if not rows:
            return "Non ho ancora nessun progetto musicale: chiedimi per esempio «crea una canzone lo-fi rilassante».", face
        return "Ho questi progetti: " + ", ".join(r["title"] or "senza titolo" for r in rows[:8]) + ".", face
    o = OPEN.search(text)
    if o and not LAYER.search(text):
        what = o.group("what").strip().lower()
        row = next((r for r in store.listing() if what and what in (r["title"] or "").lower()), None) or (store.listing() or [None])[0]
        if not row:
            return "Non ho ancora nessun progetto musicale da aprire.", face
        state["active"] = row["id"]
        _announce({}, f"Progetto «{row['title'] or 'senza titolo'}» pronto nello Studio Musicale.")
        return f"Ho preparato «{row['title'] or 'il progetto'}»: lo trovi nello Studio Musicale.", face
    pid = active()
    if not pid:
        raise LookupError
    t = TRANSLATE.search(text)
    if t:
        lang = LANG_WORDS.get(t.group("lang").lower())
        if not lang:
            return "Non conosco quella lingua per la traduzione.", face
        try:
            await service.translate(pid, lang, True)
        except S.SpecError:
            return "Questa canzone non ha ancora un testo da tradurre.", face
        except (ValueError, RuntimeError):
            return "Non riesco a tradurre adesso: il cervello non è disponibile.", face
        return f"Ho tradotto il testo in {lyr.LANGUAGES.get(lang, lang)} e aggiunto la voce nella nuova lingua.", face
    e = EFFECT.search(text)
    if e:
        target = ROLE_WORDS.get((e.group("target") or "").lower(), "")
        try:
            service.add_effect(pid, FX_WORDS[e.group("fx").lower()], target)
        except S.SpecError:
            return "Quell'effetto non lo conosco.", face
        return f"Ho aggiunto il {e.group('fx').lower()}.", face
    r = REVOICE.search(text)
    if r:
        project = store.load(pid)
        wanted = r.group("who").lower()
        pool = await voicebank.voices(project["lyrics"]["lang"])
        voice = next((x for x in pool if wanted in x["name"].lower()), None)
        track = next((t for t in project["tracks"] if t["role"] == "vocal" and any((c.get("vocal") or {}).get("text") for c in t["clips"])), None)
        if voice and track:
            await service.revoice(pid, track["id"], voice["id"])
            return f"Ora canta {voice['name']}.", face
        if voice is None and wanted not in ("canzone", "brano", "testo", "mia", "sua"):
            return "Non trovo quella voce: puoi crearla nello Studio delle Voci.", face
    v = VOCAL.search(text)
    if v:
        try:
            await service.add_vocals(pid, "", store.load(pid)["lyrics"]["lang"])
        except S.SpecError:
            return "Non c'è ancora un testo: chiedimi di scriverne uno oppure creo una nuova canzone con la voce.", face
        return "Ho aggiunto la voce con il testo della canzone.", face
    layer = LAYER.search(text)
    if layer:
        try:
            service.add_layer(pid, ROLE_WORDS[layer.group("what").lower().replace("  ", " ")])
        except S.SpecError as exc:
            return ("Ho raggiunto il numero massimo di tracce." if str(exc) == "tracks_full" else "Non riesco ad aggiungerlo."), face
        return f"Ho aggiunto {layer.group('what').lower()} in sintonia con il resto.", face
    tempo = TEMPO.search(text)
    if tempo and re.search(r"\b(?:canzone|brano|base|musica|progetto)\b|\bbpm\b", text, re.I):
        current = store.load(pid)["tempo"]
        if tempo.group("rel"):
            value = current * (1.12 if "veloce" in tempo.group("rel").lower() else 0.88)
        else:
            value = float(tempo.group(1))
        service.set_tempo(pid, value)
        return f"Tempo a {round(store.load(pid)['tempo'])} battiti al minuto.", face
    raise LookupError


