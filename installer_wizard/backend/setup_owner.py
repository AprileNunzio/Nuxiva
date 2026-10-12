import json
import re

from fastapi import HTTPException

from features.people import people
from features.voices.languages import LANGS as VOICE_LANGUAGES

FIRST_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ-]{0,39}")
LAST_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ' -]{0,59}")


def clean_names(raw: dict) -> tuple[str, str]:
    first = str(raw.get("name") or "").strip()
    last = " ".join(str(raw.get("last_name") or "").split())
    if not first:
        raise HTTPException(400, "Scrivi il tuo nome: serve per riconoscerti e salutarti")
    if not FIRST_RE.fullmatch(first):
        raise HTTPException(400, "Il nome può contenere solo lettere e trattini, senza spazi")
    if last and not LAST_RE.fullmatch(last):
        raise HTTPException(400, "Il cognome può contenere solo lettere, spazi, apostrofi e trattini")
    return first, last


def clean_voice_language(raw: dict, ui_lang: str) -> str:
    voice = str(raw.get("voice_lang") or ui_lang)
    if voice not in VOICE_LANGUAGES:
        raise HTTPException(400, "Lingua della voce non supportata")
    return voice


def full_name(first: str, last: str) -> str:
    return f"{first} {last}".strip()


def register_owner(first: str, last: str, ui_lang: str, voice_lang: str) -> dict:
    owner = next((p for p in people.all_profiles(light=True) if p.get("role") == "owner"), None)
    name = full_name(first, last)
    profile = people.load(owner["slug"]) if owner else people.ensure(people.slugify(name), name)
    profile.update(first_name=first, last_name=last, role="owner", ui_language=ui_lang, voice_language=voice_lang)
    people.save(profile)
    return profile


async def enroll_face(first: str, last: str, image_base64: str = "") -> dict:
    import base64
    from pathlib import Path
    name = full_name(first, last)
    slug = people.slugify(name)
    people.ensure(slug, name)
    if image_base64:
        try:
            target_dir = Path("/var/lib/nuxiva/people") / slug / "faces"
            target_dir.mkdir(parents=True, exist_ok=True)
            raw_bytes = base64.b64decode(str(image_base64).split(",")[-1])
            (target_dir / "sample_0.jpg").write_bytes(raw_bytes)
        except Exception:
            pass
    try:
        from features.vision.proxy import vision_proxy
        payload = {"name": name}
        if image_base64:
            payload["image"] = image_base64
        resp = await vision_proxy("/people", "POST", payload, timeout=10)
        data = json.loads(resp.body or b"{}")
        if resp.status_code == 200:
            return {"slug": data.get("slug", slug), "samples": int(data.get("samples", 1))}
    except Exception:
        pass
    return {"slug": slug, "samples": 1 if image_base64 else 0}
