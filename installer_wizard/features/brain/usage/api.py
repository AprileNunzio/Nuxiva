from access import require_admin, require_display
from fastapi import APIRouter, Depends, HTTPException, Request

from features.brain.usage.ledger import BudgetError, usage_ledger
from state import store

admin_routes = APIRouter()
public_routes = APIRouter()


@admin_routes.get("/api/brains/usage")
async def usage_overview(_: str = Depends(require_admin)):
    return usage_ledger.summary()


@admin_routes.put("/api/brains/usage/budgets")
async def usage_budgets(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(400, "budget_invalid")
    try:
        summary = usage_ledger.set_budgets(body)
    except BudgetError as exc:
        raise HTTPException(400, str(exc)) from exc
    store.event("INFO", f"Limiti di consumo dei cervelli aggiornati da {user}", "models")
    return summary


@public_routes.get("/api/brain/usage")
async def usage_compact(request: Request):
    require_display(request)
    return usage_ledger.compact()
