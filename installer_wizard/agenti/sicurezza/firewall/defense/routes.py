from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from access import NO_CACHE, require_admin

from agenti.firewall.defense.guardian import guardian
from agenti.firewall.defense.journal import journal
from agenti.firewall.defense.responder import Refused, responder

router = APIRouter()
MANUAL = ("block", "tarpit", "rate_limit", "honeypot", "quarantine", "sinkhole", "country_block")


def remember(request: Request) -> None:
    if request.client and request.client.host:
        responder.seen_admin(request.client.host)


@router.get("/api/firewall/defense")
async def defense_state(request: Request, _: str = Depends(require_admin)):
    remember(request)
    return JSONResponse(guardian.snapshot(), headers=NO_CACHE)


@router.post("/api/firewall/defense/actions")
async def defense_action(request: Request, user: str = Depends(require_admin)):
    from agenti.firewall.applier import FirewallError
    remember(request)
    body = await request.json()
    if not isinstance(body, dict) or body.get("kind") not in MANUAL or not isinstance(body.get("target"), str):
        raise HTTPException(400, "Azione di difesa non valida")
    try:
        minutes = int(body.get("minutes") or 60)
    except (TypeError, ValueError):
        raise HTTPException(400, "Durata non valida")
    action = {"kind": body["kind"], "target": body["target"][:80], "minutes": minutes,
              "reason": str(body.get("reason") or "manuale")[:80], "incident": str(body.get("incident") or "")[:16]}
    try:
        outcome = await responder.execute(action, user)
    except Refused as exc:
        raise HTTPException(409, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except FirewallError as exc:
        raise HTTPException(400, f"nftables ha rifiutato la modifica: {exc}")
    guardian.tick()
    return {"applied": outcome, **guardian.snapshot()}


@router.delete("/api/firewall/defense/responses/{key:path}")
async def defense_revoke(key: str, request: Request, user: str = Depends(require_admin)):
    from agenti.firewall.applier import FirewallError
    remember(request)
    try:
        await responder.revoke(key[:120], user)
    except KeyError:
        raise HTTPException(404, "Difesa non attiva")
    except FirewallError as exc:
        raise HTTPException(400, f"nftables ha rifiutato la modifica: {exc}")
    guardian.tick()
    return guardian.snapshot()


@router.get("/api/firewall/defense/journal")
async def defense_journal(_: str = Depends(require_admin)):
    return JSONResponse({"entries": journal.tail(500), "intact": journal.verify()}, headers=NO_CACHE)
