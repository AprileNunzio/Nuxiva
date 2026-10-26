from fastapi import APIRouter, Depends

from access import require_admin
from server.core.hippocampus_router.api import router as hippocampus_router

public_routes = APIRouter()
admin_routes = APIRouter()
admin_routes.include_router(hippocampus_router, dependencies=[Depends(require_admin)])
