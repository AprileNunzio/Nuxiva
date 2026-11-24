import httpx

_MAX = 240


def _message(data) -> str:
    if not isinstance(data, dict):
        return ""
    error = data.get("error")
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    if isinstance(error, str):
        return error
    message = data.get("message")
    return message if isinstance(message, str) else ""


def provider_message(res: httpx.Response) -> str:
    try:
        data = res.json()
    except ValueError:
        data = None
    text = _message(data) or res.text or ""
    return "".join(c for c in text if c.isprintable())[:_MAX]


def describe(name: str, url: str, res: httpx.Response) -> str:
    detail = provider_message(res)
    hint = " (indirizzo del servizio o modello inesistente o ritirato)" if res.status_code == 404 else ""
    return f"{name} {res.status_code} su {url}{hint}{': ' + detail if detail else ''}"
