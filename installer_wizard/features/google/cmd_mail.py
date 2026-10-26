import re
import unicodedata
from pathlib import Path

from config import STATE_DIR
from features.google import panels
from features.google.commands import Ctx

_SENDER = re.compile(r"\b(?:da|di)\s+([A-Za-zÀ-ÿ'][\wÀ-ÿ'. -]{1,40})$", re.I)
_TOPIC = re.compile(r"\b(?:su|riguardo(?: a)?|che parla(?:no)? di|con oggetto)\s+(.{2,60})$", re.I)
_NOT_SENDER = re.compile(r"^(?:oggi|ieri|stamattina|nuove|non lette|posta|gmail)\b", re.I)


def _query(text: str) -> tuple[str, str]:
    clean = text.strip(" ?!.")
    sender = _SENDER.search(clean)
    if sender and not _NOT_SENDER.match(sender.group(1)):
        who = sender.group(1).strip()
        return f"from:({who}) in:inbox", f"da {who}"
    topic = _TOPIC.search(clean)
    if topic:
        what = topic.group(1).strip(" \"'«»")
        return f"{what} in:inbox", f"su «{what}»"
    return "is:unread in:inbox", ""


def _private_reply(ctx: Ctx, total: int) -> tuple[str, dict]:
    return (f"{ctx.name}, ha {total} email non lett{'a' if total == 1 else 'e'}. Ci sono altre persone qui: "
            "le dirò mittenti e contenuti quando sarà da solo.", {"mode": "face"})


async def inbox(text: str, ctx: Ctx) -> tuple[str, dict]:
    query, label = _query(text)
    total, mails = await ctx.session.mails(query, 6)
    if not label:
        ctx.session.unread = total
    if not ctx.private:
        return _private_reply(ctx, total if not label else len(mails))
    if not mails:
        return (f"Non trovo email {label}." if label else f"{ctx.name}, nessuna email da leggere. Casella in ordine."), \
            {"mode": "face"}
    if label:
        last = mails[0]
        speech = f"L'ultima email {label} è di {last['from']}, oggetto «{last['subject']}». {last['snippet'][:160]}"
        title = f"Email {label}"
    else:
        speech = f"{ctx.name}, ha {total} email non lett{'a' if total == 1 else 'e'}. " + " ".join(
            f"Da {x['from']}: {x['subject']}." for x in mails[:3])
        title = f"Posta di {ctx.name} — {total} non lette"
    return speech, {"mode": "focus", "title": title, "subtitle": ctx.email,
                    "panels": [panels.mail(total if not label else len(mails), mails, "Messaggi")]}


async def read(text: str, ctx: Ctx) -> tuple[str, dict]:
    query, label = _query(text)
    if not ctx.private:
        total, _ = await ctx.session.mails("is:unread in:inbox", 0)
        return _private_reply(ctx, total)
    _, mails = await ctx.session.mails(query, 1)
    if not mails and not label:
        _, mails = await ctx.session.mails("in:inbox", 1)
    if not mails:
        return f"Non trovo email {label or 'recenti'}.", {"mode": "face"}
    m = mails[0]
    body = await ctx.session.mail_text(m["id"])
    speech = f"Email di {m['from']}, oggetto «{m['subject']}». {body[:600]}"
    return speech, {"mode": "focus", "title": m["subject"], "subtitle": f"{m['from']} · {ctx.email}",
                    "panels": [panels.mail_body(m, body)]}


MAX_FILES = 20
MAX_BYTES = 25 * 2 ** 20
ROOT = STATE_DIR / "downloads" / "gmail"
_TOPIC_DL = re.compile(r"\b(?:tutt[eio]\s+)?(?:le|i|gli|l'|la|il)\s*([A-Za-zÀ-ÿ]{3,30})\b", re.I)
_OWNER_DL = re.compile(r"\b(?:di|da|del|della)\s+([A-Za-zÀ-ÿ][\wÀ-ÿ&.-]{1,30})", re.I)
_FOLDER_DL = re.compile(r"\bcartella\s+(.{1,60})$", re.I)
_SKIP_TOPIC = {"mail", "email", "posta", "allegati", "allegato", "pdf", "file"}


def _slug(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")[:40] or "varie"


def _safe_name(name: str) -> str:
    stem = _slug(Path(name).stem)
    return f"{stem}.pdf"


def attachment_request(text: str) -> tuple[str, str]:
    clean = text.strip(" ?!.")
    folder = _FOLDER_DL.search(clean)
    if folder:
        clean = clean[:folder.start()].strip()
    topic = next((m.group(1) for m in _TOPIC_DL.finditer(clean) if m.group(1).lower() not in _SKIP_TOPIC), "")
    who = next((m.group(1) for m in _OWNER_DL.finditer(clean) if m.group(1).lower() not in _SKIP_TOPIC), "")
    terms = " ".join(x for x in (topic, who) if x)
    query = f"{terms} has:attachment filename:pdf".strip()
    return query, _slug(folder.group(1) if folder else terms)


async def download(text: str, ctx: Ctx) -> tuple[str, dict]:
    if not ctx.private:
        return (f"{ctx.name}, per scaricare i suoi allegati aspetto di essere da solo con lei.", {"mode": "face"})
    query, folder = attachment_request(text)
    files = (await ctx.session.pdf_attachments(query, MAX_FILES))[:MAX_FILES]
    if not files:
        return f"Non trovo allegati PDF per «{query.replace(' has:attachment filename:pdf', '')}».", {"mode": "face"}
    target = ROOT / _slug(ctx.email or ctx.name) / folder
    target.mkdir(parents=True, exist_ok=True)
    saved, skipped = [], 0
    for item in files:
        if item["size"] > MAX_BYTES:
            skipped += 1
            continue
        raw = await ctx.session.attachment_bytes(item["mail_id"], item["attachment_id"])
        if not raw.startswith(b"%PDF") or len(raw) > MAX_BYTES:
            skipped += 1
            continue
        path = target / f"{int(item['at'])}-{_safe_name(item['name'])}"
        path.write_bytes(raw)
        saved.append(path.name)
    where = str(target)
    if not saved:
        return f"Ho trovato {len(files)} allegati ma nessuno era un PDF valido o entro i limiti.", {"mode": "face"}
    extra = f" Ne ho saltati {skipped}." if skipped else ""
    speech = f"{ctx.name}, ho scaricato {len(saved)} PDF nella cartella {where}.{extra}"
    return speech, {"mode": "focus", "title": "Allegati scaricati", "subtitle": where,
                    "panels": [{"type": "list", "title": "File", "items": [{"label": n, "value": "", "status": ""} for n in saved]}]}
