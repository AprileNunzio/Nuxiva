from features.sentinel.record import person, record


def record_voice(phrase: str, speaker_slug: str | None = None, recognized: bool = True,
                 place: str | None = None, device: str = "kiosk") -> str | None:
    text = str(phrase or "").strip()
    if not text:
        return None
    is_known = bool(recognized and speaker_slug and speaker_slug.lower() not in ("utente", "unknown", "anonimo"))
    kind = "voice.recognized" if is_known else "voice.unknown"
    subject = person(speaker_slug) if is_known else {"type": "voice", "id": "unknown"}
    key = f"sentinel.{kind}"
    params = {
        "person": speaker_slug if is_known else "sconosciuto",
        "phrase": text[:120],
        "device": device[:40],
    }
    return record(
        kind=kind,
        subject=subject,
        key=key,
        params=params,
        sensitivity="personal",
        source="voice",
        place=place,
    )
