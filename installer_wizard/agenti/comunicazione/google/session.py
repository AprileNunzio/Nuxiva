import asyncio
import time

import httpx

from agenti.google.accounts import accounts
from agenti.google.app import oauth
from agenti.google.constants import GRANTS, HEALTH, MAIN, grant_for_url, grant_of, log
from agenti.google.data import GoogleData
from agenti.google.errors import GoogleApiError, explain

RETRY_STATUS = {429, 500, 502, 503, 504}
RETRIES = 2
BACKOFF = 0.8
TIMEOUT = httpx.Timeout(15.0, connect=6.0)


class Session(GoogleData):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        self.tokens: dict[str, tuple[str, float]] = {}
        self.unread: int | None = None
        self.status = "collegato"
        self._refresh_lock = asyncio.Lock()

    @property
    def access_token(self) -> str:
        return self.tokens.get(MAIN, ("", 0.0))[0]

    @access_token.setter
    def access_token(self, value: str) -> None:
        self.tokens[MAIN] = (value, self.tokens.get(MAIN, ("", 0.0))[1])

    @property
    def expires_at(self) -> float:
        return self.tokens.get(MAIN, ("", 0.0))[1]

    @expires_at.setter
    def expires_at(self, value: float) -> None:
        self.tokens[MAIN] = (self.tokens.get(MAIN, ("", 0.0))[0], value)

    @property
    def info(self) -> dict:
        return accounts.get(self.slug) or {}

    def granted(self) -> list[str]:
        return accounts.granted(self.info)

    def ready(self, service: str) -> bool:
        info, keys = self.info, GRANTS[grant_of(service)]
        return bool(info.get(keys["refresh"])) and not info.get(keys["revoked"]) and service in accounts.granted(info)

    def _fresh(self, grant: str) -> str:
        token, until = self.tokens.get(grant, ("", 0.0))
        return token if token and time.time() < until else ""

    async def _access(self, force: bool = False, grant: str = MAIN) -> str:
        if not force and (token := self._fresh(grant)):
            return token
        keys = GRANTS[grant]
        async with self._refresh_lock:
            if not force and (token := self._fresh(grant)):
                return token
            refresh = self.info.get(keys["refresh"], "")
            if not refresh:
                raise GoogleApiError(401, "not_linked", "Google Health non autorizzato: attiva il suo interruttore" if grant == HEALTH
                                     else "Account Google non collegato")
            try:
                body = await oauth.token({"grant_type": "refresh_token", "refresh_token": refresh})
            except ValueError as exc:
                if "ricollega" in str(exc):
                    accounts.put(self.slug, {keys["revoked"]: True})
                    if grant == MAIN:
                        self.status = "da ricollegare"
                raise
            self.tokens[grant] = (body["access_token"], time.time() + int(body.get("expires_in", 3600)) - 60)
            changes: dict = {keys["revoked"]: False}
            returned = set(str(body.get("scope") or "").split())
            stored = set(self.info.get(keys["scopes"]) or [])
            if returned - stored:
                changes[keys["scopes"]] = sorted(stored | returned)
            missing = stored - returned
            if returned and missing:
                log.info("Google (%s): il rinnovo non elenca %s, li verifico alla prima risposta dell'API", self.slug, ", ".join(sorted(missing)))
            accounts.put(self.slug, changes)
            return self.tokens[grant][0]

    async def verify_scopes(self, grant: str = MAIN) -> list[str]:
        token = await self._access(grant=grant)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get("https://oauth2.googleapis.com/tokeninfo", params={"access_token": token})
        if r.status_code != 200:
            raise explain(r)
        scopes = sorted(set(str(r.json().get("scope") or "").split()))
        if scopes:
            accounts.put(self.slug, {GRANTS[grant]["scopes"]: scopes})
        return scopes

    async def _call(self, method: str, url: str, **kw) -> dict:
        grant = grant_for_url(url)
        renewed = False
        attempt = 0
        while True:
            token = await self._access(force=renewed, grant=grant)
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                r = await client.request(method, url, headers={"Authorization": f"Bearer {token}"}, **kw)
            if r.status_code == 401 and not renewed:
                self.tokens.pop(grant, None)
                renewed = True
                continue
            if r.status_code in RETRY_STATUS and attempt < RETRIES:
                attempt += 1
                wait = _retry_after(r) or BACKOFF * (2 ** (attempt - 1))
                log.info("Google %s %s: %s, nuovo tentativo tra %.1fs", method, url.split("?")[0], r.status_code, wait)
                await asyncio.sleep(min(wait, 8.0))
                continue
            if r.status_code >= 400:
                error = explain(r)
                if error.reason == "scope_missing":
                    await self._recheck_scopes(grant)
                raise error
            return r.json() if r.content else {}

    async def _recheck_scopes(self, grant: str = MAIN) -> None:
        try:
            before = set(accounts.granted(self.info))
            await self.verify_scopes(grant)
            lost = before - set(accounts.granted(self.info))
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Google (%s): permessi non verificati: %s", self.slug, exc)
            return
        if lost:
            log.warning("Google (%s): Google non concede più %s", self.slug, ", ".join(sorted(lost)))

    async def _get(self, url: str, **params) -> dict:
        return await self._call("GET", url, params=params or None)


def _retry_after(r: httpx.Response) -> float:
    try:
        return max(0.0, float(r.headers.get("retry-after", "")))
    except ValueError:
        return 0.0
