import json
import logging

import websockets

import stt
from broadcast import SESSIONS, register, unregister
from link_state import LINK, note_error, save_link

log = logging.getLogger("nuxiva.ear")


async def handle_display(ws, make_session, voiceprints, host_mic) -> None:
    try:
        session = make_session(ws)
    except Exception as exc:
        note_error("avvio della sessione", exc)
        save_link()
        raise
    await session.send(type="ready", model=stt.MODEL_SIZE, instant=session.wake.ready, voiceprint=voiceprints.ready, host_mic=host_mic.is_capturing())
    log.info("Display collegato")
    register(session)
    LINK["clients"] += 1
    save_link()
    try:
        async for message in ws:
            try:
                if isinstance(message, bytes):
                    await session.feed(message)
                else:
                    await session.control(json.loads(message))
            except (ValueError, TypeError) as exc:
                if isinstance(message, bytes):
                    note_error("elaborazione dell'audio", exc)
                else:
                    log.debug("Messaggio di controllo non valido")
            except websockets.ConnectionClosed:
                raise
            except Exception as exc:
                note_error("elaborazione dell'audio" if isinstance(message, bytes) else "comando", exc)
                session.in_speech, session.speech = False, []
                session.live.end()
    except websockets.ConnectionClosed:
        log.debug("Connessione chiusa dal display")
    finally:
        await session.input.close()
        unregister(session)
        LINK["pages"] = [s.page for s in SESSIONS if s.page]
        LINK["clients"] = max(0, LINK["clients"] - 1)
        save_link()
        log.info("Display scollegato")
