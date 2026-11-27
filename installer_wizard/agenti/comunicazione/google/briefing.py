import hashlib
from datetime import datetime, timedelta, timezone

from agenti.chat.checkin.contract import fact

TIMEOUT = 3.0
MAIL_TERMS = ["email", "mail", "posta", "correo", "courrier"]
AGENDA_TERMS = ["agenda", "impegni", "calendario", "appuntamenti", "calendar", "agenda"]


def _context(service: str):
    from agenti.google.commands import _context as context
    from agenti.google.constants import NotLinked
    try:
        return context(service, True)
    except (LookupError, NotLinked):
        return None


async def _mail() -> list[dict]:
    ctx = _context("gmail")
    if ctx is None:
        return []
    unread = await ctx.session.unread_threads(-1)
    if unread < 0:
        return []
    if not unread:
        return [fact("mail_none", "email", "ok", 25, 600, "mail_none", terms=MAIL_TERMS)]
    return [fact("mail_unread", "email", "notice", 50 if unread < 10 else 55, 600, "mail_unread", {"n": unread},
                 terms=MAIL_TERMS)]


async def _agenda() -> list[dict]:
    ctx = _context("calendar")
    if ctx is None:
        return []
    now = datetime.now(timezone.utc)
    out = []
    for e in (await ctx.session.events(now, now + timedelta(hours=12), 3))[:2]:
        try:
            at = datetime.fromisoformat(str(e["start"]).replace("Z", "+00:00")).timestamp()
        except ValueError:
            at = None
        when = datetime.fromtimestamp(at).strftime("%H:%M") if at and not e.get("all_day") else ""
        title = str(e.get("title") or "")[:80]
        key = "agenda_" + hashlib.sha256(title.encode("utf-8")).hexdigest()[:8]
        out.append(fact(key, "agenda", "agenda", 60, 900, "agenda", {"title": title, "time": when}, starts_at=at,
                        terms=AGENDA_TERMS))
    return out


async def facts() -> list[dict]:
    return await _mail() + await _agenda()
