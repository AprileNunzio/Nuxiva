import logging

log = logging.getLogger("nuxiva.chat.duplex_feed")


def _voice():
    from agenti.voices import duplex_voice
    return duplex_voice


async def begin(device: str):
    voice = _voice()
    session = voice.session_for(device) if voice.enabled() else None
    if session is None:
        return None
    try:
        return await session.begin()
    except (ValueError, RuntimeError) as exc:
        log.warning("Voce duplex non avviata per la risposta: %s", exc)
        return None


def token(feed, event: dict) -> None:
    if feed is not None and isinstance(event, dict) and event.get("type") == "token" and isinstance(event.get("t"), str):
        feed.put(event["t"])


def close(feed) -> None:
    if feed is not None:
        feed.close()
