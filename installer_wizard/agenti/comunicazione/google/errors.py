import re

import httpx

SAFE_URL = re.compile(r"^https://console\.(?:cloud\.google|developers\.google)\.com/[\w\-./?=&%:]{1,400}$")
API_NAMES = {
    "calendar-json.googleapis.com": "Google Calendar API",
    "gmail.googleapis.com": "Gmail API",
    "tasks.googleapis.com": "Google Tasks API",
    "people.googleapis.com": "People API",
    "drive.googleapis.com": "Google Drive API",
    "health.googleapis.com": "Google Health API",
    "keep.googleapis.com": "Google Keep API",
}
DISABLED = {"SERVICE_DISABLED", "accessNotConfigured"}
SCOPE = {"ACCESS_TOKEN_SCOPE_INSUFFICIENT", "insufficientPermissions"}
QUOTA = {"RATE_LIMIT_EXCEEDED", "rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded", "RESOURCE_EXHAUSTED"}


class GoogleApiError(ValueError):
    def __init__(self, status: int, reason: str, message: str, activation: str = "", api: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.reason = reason
        self.activation = activation
        self.api = api


def _details(body: dict) -> tuple[str, str, str, str]:
    error = body.get("error") if isinstance(body.get("error"), dict) else {}
    message = str(error.get("message") or "")[:300]
    reason, activation, api = str(error.get("status") or ""), "", ""
    for item in error.get("details") or []:
        if not isinstance(item, dict):
            continue
        if item.get("reason"):
            reason = str(item["reason"])
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        api = api or str(meta.get("service") or meta.get("consumer_service") or "")
        activation = activation or str(meta.get("activationUrl") or "")
        for link in item.get("links") or []:
            if isinstance(link, dict) and not activation and "apis/api" in str(link.get("url", "")):
                activation = str(link["url"])
    for item in error.get("errors") or []:
        if isinstance(item, dict) and item.get("reason") and not reason:
            reason = str(item["reason"])
    return reason, message, activation if SAFE_URL.match(activation) else "", api


def explain(r: httpx.Response) -> GoogleApiError:
    body: dict = {}
    if r.content and r.headers.get("content-type", "").startswith("application/json"):
        try:
            parsed = r.json()
        except ValueError:
            parsed = {}
        body = parsed if isinstance(parsed, dict) else {}
    reason, message, activation, api = _details(body)
    if reason in DISABLED or "has not been used in project" in message or "is disabled" in message:
        name = API_NAMES.get(api, api or "richiesta")
        text = f"Google: l'API «{name}» non è abilitata nel progetto Google Cloud: abilitala" + (f" da {activation}" if activation else " dalla Libreria API")
        return GoogleApiError(r.status_code, "api_disabled", text, activation, api)
    if "UberMint" in message or "GaiaMint" in message or reason == "DISALLOWED_OAUTH_SCOPES":
        return GoogleApiError(r.status_code, "health_grant",
                              "Google Health va autorizzato separatamente dagli altri servizi Google: riattiva l'interruttore di Google Health e conferma")
    if reason in SCOPE or reason == "MISSING_OAUTH_SCOPE":
        return GoogleApiError(r.status_code, "scope_missing", "Google: permesso non concesso per questo servizio: ricollega l'account e spunta tutte le caselle")
    if reason == "ACCOUNT_NOT_LINKED" or "ACCOUNT_NOT_LINKED" in message:
        return GoogleApiError(r.status_code, "health_profile_missing",
                              "Google Health: l'account non ha ancora un profilo Google Health: apri l'app Google Health sul telefono, accedi e crea il profilo (o migra Fitbit)")
    if r.status_code == 429 or reason in QUOTA:
        return GoogleApiError(r.status_code, "quota", "Google: troppe richieste in poco tempo, riprovo più tardi")
    if r.status_code == 401:
        return GoogleApiError(401, "unauthorized", "Google: accesso non valido, ricollega l'account")
    if reason == "API_PRIVATE_PREVIEW_ACCESS_DENIED":
        return GoogleApiError(r.status_code, "health_preview", "Google Health: questo account non è ancora abilitato all'API (anteprima privata di Google)")
    if reason == "DATA_ACCESS_DENIED":
        return GoogleApiError(r.status_code, "forbidden", "Google Health: Google non consente l'accesso a questi dati per questo account")
    if r.status_code == 403:
        return GoogleApiError(403, "forbidden", f"Google ha rifiutato la richiesta: {message or 'permesso mancante'}")
    if r.status_code == 404:
        return GoogleApiError(404, "not_found", "Google: elemento non trovato")
    return GoogleApiError(r.status_code, reason or "http_error", f"Google: errore {r.status_code}" + (f" ({message})" if message else ""))
