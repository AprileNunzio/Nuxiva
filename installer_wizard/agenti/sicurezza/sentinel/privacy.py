import hashlib
import re
import secrets
import time

from agenti.people import private_store
from agenti.people.private_store import SealedFile
from agenti.sentinel import record
from agenti.sentinel.memory_people import forget as forget_memory, who_for

SLUG = re.compile(r"^[a-z0-9_.-]{1,64}$")


def _voiceprints():
    try:
        from agenti.ear.voiceprint import Voiceprints
        return Voiceprints()
    except Exception:
        return None


def _ear_journal():
    try:
        from agenti.ear.journal import journal
        return journal
    except Exception:
        return None


def _nvr_export(slug: str) -> dict:
    try:
        from agenti.nvr.privacy import export_person as nvr_export
        from agenti.nvr.transcripts import store
    except ImportError:
        return {}
    try:
        return nvr_export(slug, store)
    except (OSError, ValueError) as exc:
        return {"error": str(exc)[:120]}


def _nvr_erase(slug: str) -> dict:
    try:
        from agenti.nvr.privacy import erase_person as nvr_erase
        from agenti.nvr.search_index import index
    except ImportError:
        return {}
    try:
        return nvr_erase(slug, index.transcripts, index)
    except (OSError, ValueError) as exc:
        return {"error": str(exc)[:120]}


def privacy_overview() -> dict:
    from agenti.people import people
    from agenti.people.people import PEOPLE_DIR
    from agenti.sentinel.memory import memory
    from agenti.sentinel.vault import days

    vp = _voiceprints()
    profiles = []
    for p in people.all_profiles(light=False):
        slug = p.get("slug")
        if not slug:
            continue
        sealed = SealedFile(PEOPLE_DIR / f"{slug}.private", private_store.KEY_FILE)
        private = sealed.load() if sealed.data_path.exists() else {}
        who = who_for(slug, p)
        try:
            mem = memory.profile(who) if who else {}
        except Exception:
            mem = {}
        profiles.append({
            "slug": slug,
            "name": p.get("name") or slug,
            "role": p.get("role") or "member",
            "consent": p.get("consent", True),
            "consent_voice": p.get("consent_voice", True),
            "has_voiceprint": bool(vp and vp.count(slug) > 0),
            "has_face_traits": bool(private.get("face_traits")),
            "has_gait_traits": bool(private.get("gait_traits")),
            "sightings_count": int(mem.get("sightings_count", 0)),
            "last_seen": mem.get("last_seen"),
        })

    ej = _ear_journal()
    try:
        audio_stats = ej.stats() if ej else {}
    except Exception:
        audio_stats = {}
    return {
        "profiles": profiles,
        "vault_days": len(days()),
        "audio_journal": audio_stats,
    }


def export_person(slug: str) -> dict:
    if not SLUG.match(slug):
        raise ValueError("invalid_slug")
    from agenti.people import people
    from agenti.people.people import PEOPLE_DIR
    from agenti.sentinel.memory import memory

    profile = people.load(slug)
    if profile is None:
        raise ValueError("person_not_found")

    sealed = SealedFile(PEOPLE_DIR / f"{slug}.private", private_store.KEY_FILE)
    private = sealed.load() if sealed.data_path.exists() else {}

    who = who_for(slug, profile)
    try:
        mem_profile = memory.profile(who) if who else {}
        sightings = memory.search({"who": who, "limit": 500}) if who else []
    except Exception:
        mem_profile = {}
        sightings = []

    record.record("sentinel.read", record.NUXIVA, "sentinel.sentinel.gdpr_export",
                  {"slug": slug}, "sensitive", "sentinel")

    return {
        "slug": slug,
        "exported_at": time.time(),
        "gdpr_article": "Article 20 - Right to data portability",
        "profile": profile,
        "private_biometrics": private,
        "sentinel_profile": mem_profile,
        "sightings": sightings,
        "recordings": _nvr_export(slug),
    }


def shred_person(slug: str) -> dict:
    if not SLUG.match(slug):
        raise ValueError("invalid_slug")
    from agenti.people.people import PEOPLE_DIR
    from agenti.people.private_store import remove as remove_private

    sightings_removed = forget_memory(slug)

    vp = _voiceprints()
    voice_removed = False
    if vp:
        vp.forget(slug)
        voice_removed = True

    ej = _ear_journal()
    journal_anonymized = 0
    if ej:
        try:
            journal_anonymized = ej.anonymize_speaker(slug)
        except Exception:
            journal_anonymized = 0

    remove_private(PEOPLE_DIR, slug)
    recordings = _nvr_erase(slug)

    now = time.time()
    token = secrets.token_hex(8)
    receipt = hashlib.sha256(f"{slug}:{now}:{sightings_removed}:{token}".encode()).hexdigest()[:32]

    record.record("sentinel.read", record.NUXIVA, "sentinel.sentinel.gdpr_shred",
                  {"slug": slug, "count": sightings_removed, "receipt": receipt}, "sensitive", "sentinel")

    return {
        "ok": True,
        "slug": slug,
        "receipt": receipt,
        "shredded_at": now,
        "sightings_removed": sightings_removed,
        "voiceprint_removed": voice_removed,
        "journal_anonymized": journal_anonymized,
        "recordings": recordings,
    }
