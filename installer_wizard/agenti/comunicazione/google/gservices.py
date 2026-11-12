import asyncio
import time
from datetime import datetime, timedelta

import httpx
from config import env_get
from state import store

from agenti.google.accounts import accounts
from agenti.google.app import oauth
from agenti.google.flows import flows
from agenti.google.constants import DEFAULT_SERVICES, GRANTS, HEALTH, REDIRECT_URI, SERVICES, linkable, log
from agenti.google.notify import notifier
from agenti.google.session import Session
from agenti.google.timeparse import event_json
from agenti.people import identity, people
from agenti.people.sync_board import board

MAX_REMIND_MIN = 240
DEFAULT_REMIND_MIN = 10


class Google:
    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}

    @staticmethod
    def enabled() -> bool:
        return env_get("NUXIVA_GOOGLE", "1") != "0"

    def session(self, slug: str) -> Session | None:
        if not accounts.get(slug):
            self.sessions.pop(slug, None)
            return None
        return self.sessions.setdefault(slug, Session(slug))

    def for_profile(self, profile: dict | None) -> Session | None:
        return self.session(profile["slug"]) if profile and self.enabled() else None

    def present_sessions(self, service: str) -> list[tuple[dict, Session]]:
        pairs = [(p, self.for_profile(p)) for p in identity.present()]
        return [(p, s) for p, s in pairs if s and s.ready(service)]

    def auth_url(self, slug: str, services: list[str]) -> str:
        if not people.load(slug):
            raise ValueError("Persona sconosciuta")
        return oauth.auth_url(slug, services or DEFAULT_SERVICES.split(","), accounts.granted(accounts.get(slug) or {}))

    async def link(self, pasted: str, slug_hint: str = "") -> tuple[str, str]:
        slug, body, grant = await oauth.exchange(pasted, slug_hint)
        keys = GRANTS[grant]
        before = set(accounts.covered(accounts.get(slug) or {}))
        accounts.put(slug, {keys["refresh"]: body["refresh_token"], keys["scopes"]: body.get("scope", "").split(),
                            "linked_at": time.time(), keys["revoked"]: False})
        for service in set(accounts.covered(accounts.get(slug) or {})) - before:
            accounts.set_off(slug, service, False)
        session = self.sessions.get(slug) or Session(slug)
        session.tokens[grant] = (body["access_token"], time.time() + body.get("expires_in", 3600) - 60)
        self.sessions[slug] = session
        who = (people.load(slug) or {}).get("name", slug)
        if grant == HEALTH:
            from agenti.people.vitals import cloud
            cloud.reset(slug)
            store.event("INFO", f"Google Health autorizzato per {who}", "google")
            return slug, (accounts.get(slug) or {}).get("email", "")
        try:
            me = await session._get("https://openidconnect.googleapis.com/v1/userinfo")
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Profilo Google di %s non letto dopo il collegamento: %s", slug, exc)
            me = {}
        if me:
            accounts.put(slug, {"email": str(me.get("email", ""))[:200], "name": str(me.get("name", ""))[:120]})
        store.event("INFO", f"Google collegato per {who} ({me.get('email', '')}): "
                            f"{', '.join(SERVICES[s]['name'] for s in session.granted())}", "google")
        return slug, me.get("email", "")

    async def unlink(self, slug: str) -> None:
        entry = accounts.remove(slug)
        self.sessions.pop(slug, None)
        for token in [entry.get(keys["refresh"]) for keys in GRANTS.values()] if entry else []:
            if not token:
                continue
            try:
                await oauth.revoke(token)
            except httpx.HTTPError as exc:
                log.warning("Revoca del token Google non confermata: %s", exc)

    def services_of(self, slug: str) -> list[dict]:
        entry = accounts.get(slug) or {}
        granted = set(accounts.granted(entry)) if entry else set()
        return [{"id": s, "name": d["name"], "icon": d["icon"], "granted": s in granted, "workspace": bool(d.get("workspace"))}
                for s, d in SERVICES.items() if linkable(s)]

    def enable_service(self, slug: str, service: str) -> str | None:
        if not linkable(service):
            raise ValueError("Servizio non valido")
        entry = accounts.get(slug) or {}
        if entry.get("refresh") and service in accounts.covered(entry):
            accounts.set_off(slug, service, False)
            return None
        return self.auth_url(slug, [service])

    async def disable_service(self, slug: str, service: str) -> bool:
        entry = accounts.get(slug)
        if not entry or service not in accounts.granted(entry):
            raise ValueError("Servizio non collegato")
        accounts.set_off(slug, service, True)
        if not accounts.granted(accounts.get(slug) or {}):
            await self.unlink(slug)
            return True
        return False

    def person_row(self, slug: str, name: str | None, role: str) -> dict:
        entry = accounts.get(slug) or {}
        session = self.sessions.get(slug)
        return {"slug": slug, "name": name, "role": role,
                "linked": bool(entry.get("refresh") or entry.get("health_refresh")), "email": entry.get("email", ""),
                "granted": accounts.granted(entry) if entry else [], "revoked": bool(entry.get("revoked")),
                "health_revoked": bool(entry.get("health_refresh") and entry.get("health_revoked")),
                "status": "da ricollegare" if entry.get("revoked") else session.status if session else ("collegato" if entry else "non collegato"),
                "unread": session.unread if session else None}

    @staticmethod
    def reminder_minutes(slug: str) -> int:
        entry = accounts.get(slug) or {}
        value = entry.get("remind_min")
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAX_REMIND_MIN:
            return value
        try:
            return max(0, min(MAX_REMIND_MIN, int(env_get("NUXIVA_GOOGLE_REMIND_MIN", "10") or 10)))
        except ValueError:
            return DEFAULT_REMIND_MIN

    def set_reminder(self, slug: str, minutes: int) -> int:
        if isinstance(minutes, bool) or not isinstance(minutes, int) or not 0 <= minutes <= MAX_REMIND_MIN:
            raise ValueError("Minuti non validi")
        if not accounts.get(slug):
            raise LookupError("Account Google non collegato")
        accounts.put(slug, {"remind_min": minutes})
        return minutes

    def person_state(self, slug: str) -> dict:
        profile = people.load(slug) or {}
        row = self.person_row(slug, profile.get("name"), profile.get("role", ""))
        cid, secret = oauth.credentials()
        return {**row, "remind_min": self.reminder_minutes(slug), "available": bool(cid and secret) and self.enabled(), "pending": slug in {f["slug"] for f in flows.pending()},
                "services": self.services_of(slug)}

    def summary(self) -> dict:
        cid, secret = oauth.credentials()
        rows = [self.person_row(p["slug"], p.get("name"), p.get("role", "")) for p in people.all_profiles(light=True)]
        return {"enabled": self.enabled(), "has_credentials": bool(cid and secret), "client_id": cid,
                "redirect_uri": REDIRECT_URI,
                "default_services": DEFAULT_SERVICES.split(","),
                "services": [{"id": s, "name": d["name"], "icon": d["icon"], "api": d["api"],
                              "workspace": bool(d.get("workspace"))} for s, d in SERVICES.items() if linkable(s)],
                "people": rows}

    async def preview(self, slug: str) -> dict:
        session = self.session(slug)
        if not session:
            return {}
        out: dict = {}
        now = datetime.now().astimezone()
        jobs = {"events": ("calendar", lambda: session.events(now, now + timedelta(days=7), 8)),
                "mail": ("gmail", lambda: session.mails(limit=5)), "tasks": ("tasks", lambda: session.tasks(10))}
        for key, (service, job) in jobs.items():
            if not session.ready(service):
                continue
            try:
                result = await job()
            except (httpx.HTTPError, ValueError) as exc:
                out[f"{key}_error"] = str(exc)
                continue
            if key == "events":
                out[key] = [event_json(e) for e in result]
            elif key == "mail":
                out[key] = {"unread": result[0], "items": result[1]}
            else:
                out[key] = result
        return out

    async def _refresh(self, profile: dict, minutes: int) -> None:
        session = self.for_profile(profile)
        slug = profile["slug"]
        if not session:
            return
        if not session.info.get("refresh"):
            return
        if session.info.get("revoked"):
            board.fail(slug, "google", "da ricollegare", reason="revoked")
            return
        jobs = {"google": lambda: notifier.brief(profile, session),
                "google_calendar": lambda: self._calendar(profile, session, minutes),
                "google_gmail": lambda: notifier.mail(profile, session),
                "google_tasks": lambda: notifier.tasks(profile, session)}
        failed = ""
        for key, job in jobs.items():
            service = key.removeprefix("google_")
            if key != "google" and not session.ready(service):
                board.off(slug, key)
                continue
            board.start(slug, key)
            try:
                await job()
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                failed = failed or str(exc)
                board.fail(slug, key, str(exc) or type(exc).__name__, reason=getattr(exc, "reason", ""))
                log.warning("Google (%s) %s: %s", slug, key, exc)
                continue
            board.ok(slug, key)
        session.status = f"errore: {failed}"[:160] if failed else "collegato"

    @staticmethod
    async def _calendar(profile: dict, session: Session, minutes: int) -> None:
        if minutes > 0:
            await notifier.soon(profile, session, minutes)
        await notifier.calendar(profile, session)

    async def run(self) -> None:
        seen: set[str] = set()
        last_full = 0.0
        while True:
            if self.enabled() and oauth.ready():
                accounts.slugs()
                here = identity.present()
                full = time.time() - last_full >= 60
                for profile in here:
                    if full or profile["slug"] not in seen:
                        await self._refresh(profile, self.reminder_minutes(profile["slug"]))
                seen = {p["slug"] for p in here}
                if full:
                    last_full = time.time()
            await asyncio.sleep(4)


google = Google()
