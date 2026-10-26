import time
from urllib.parse import urlsplit

import httpx

TIMEOUT = httpx.Timeout(6.0, connect=4.0)


def reason(exc: Exception) -> tuple[str, str]:
    text = str(exc)
    if isinstance(exc, httpx.ConnectTimeout) or isinstance(exc, httpx.ReadTimeout):
        return "timeout", "Nessuna risposta: controlla indirizzo e rete"
    if "CERTIFICATE" in text.upper() or "SSL" in text.upper():
        return "tls", "Certificato HTTPS non valido: disattiva la verifica del certificato se è autofirmato"
    if isinstance(exc, httpx.ConnectError):
        return "unreachable", "Indirizzo non raggiungibile: controlla IP, porta e che Home Assistant sia acceso"
    return "error", f"{type(exc).__name__}"[:120]


async def probe(url: str, token: str, verify_ssl: bool) -> dict:
    started = time.monotonic()
    result = {"url": url, "ok": False, "state": "error", "message": "", "version": "", "name": "", "ms": 0}
    if not urlsplit(url).hostname:
        return {**result, "state": "invalid", "message": "Indirizzo non valido"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, verify=verify_ssl, follow_redirects=False) as client:
            response = await client.get(f"{url}/api/config", headers={"Authorization": f"Bearer {token}"} if token else {})
    except httpx.HTTPError as exc:
        state, message = reason(exc)
        return {**result, "state": state, "message": message, "ms": int((time.monotonic() - started) * 1000)}
    result["ms"] = int((time.monotonic() - started) * 1000)
    if response.status_code == 200:
        try:
            body = response.json()
        except ValueError:
            return {**result, "state": "not_home_assistant", "message": "L'indirizzo risponde ma non è Home Assistant"}
        return {**result, "ok": True, "state": "ok", "version": str(body.get("version", ""))[:40],
                "name": str(body.get("location_name", ""))[:80]}
    if response.status_code == 401:
        return {**result, "state": "auth" if token else "no_token",
                "message": "Token rifiutato: creane uno nuovo dal tuo profilo di Home Assistant" if token
                else "Home Assistant risponde: inserisci il token di accesso"}
    if response.status_code in (301, 302, 307, 308):
        return {**result, "state": "redirect", "message": "L'indirizzo reindirizza altrove: usa direttamente quello finale (es. https://…)"}
    return {**result, "state": "not_home_assistant", "message": f"Risposta inattesa (HTTP {response.status_code})"}


async def probe_all(urls: list[str], token: str, verify_ssl: bool) -> list[dict]:
    return [await probe(url, token, verify_ssl) for url in urls]
