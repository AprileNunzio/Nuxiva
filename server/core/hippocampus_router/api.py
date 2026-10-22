from typing import Any, Dict

from fastapi import APIRouter

from server.core.hippocampus_router.composition import hippocampus_service
from server.shared.i18n.context import current_language

router = APIRouter(tags=["Nuxiva Hippocampus Router"])


@router.get("/api/v1/cognition/hippocampus/status")
async def get_hippocampus_status() -> Dict[str, Any]:
    return hippocampus_service().status(current_language.get())
