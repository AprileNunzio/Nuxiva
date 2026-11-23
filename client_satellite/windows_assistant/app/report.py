from i18n.strings import t

ERROR_KEYS = {"brain_unavailable": "brain.unavailable", "privacy_blocked": "brain.privacy_blocked",
              "brain_timeout": "brain.timeout"}
MAX_DETAIL = 3


def _failure(result: dict) -> str:
    return str(result.get("error") or t("report.unknown_error"))[:200]


def _success(result: dict) -> str:
    if result.get("type") == "open_url":
        url = str(result.get("url") or "")
        if result.get("fallback"):
            return t("report.site_fallback", url=url, browser=str(result.get("requested_browser") or ""))
        if result.get("browser"):
            return t("report.site_opened_in", url=url, browser=str(result["browser"]))
        return t("report.site_opened", url=url)
    return ""


def compose(reply: str, results: list[dict]) -> str:
    reply = (reply or "").strip()
    if not results:
        return reply
    failed = [r for r in results if not r.get("ok")]
    done = [r for r in results if r.get("ok")]
    if failed:
        detail = "; ".join(_failure(r) for r in failed[:MAX_DETAIL])
        if done:
            return t("report.partial", done=len(done), failed=len(failed), detail=detail)
        return t("report.failed", detail=detail)
    specific = [line for line in (_success(r) for r in done) if line]
    if any(r.get("fallback") for r in done):
        return " ".join(specific)
    return reply or " ".join(specific) or t("report.done", count=len(done))


def error_message(code: str) -> str:
    return t(ERROR_KEYS.get(str(code or ""), "brain.failed"))
