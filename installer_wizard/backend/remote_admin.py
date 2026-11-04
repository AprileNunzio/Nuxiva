from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

from access import require_admin, session_user


class RemoteAdmin:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        path = scope.get("path", "")
        root = scope.get("root_path", "")
        relative = path[len(root):] if root and path.startswith(root) else path
        if scope["type"] == "websocket":
            if not session_user(Request({**scope, "type": "http", "method": "GET"})):
                await send({"type": "websocket.close", "code": 4401})
                return
        elif scope["type"] == "http" and relative.startswith("/api/"):
            if relative not in ("/api/auth/login", "/api/auth/me"):
                try:
                    require_admin(Request(scope))
                except HTTPException as exc:
                    await JSONResponse({"detail": exc.detail}, status_code=exc.status_code)(scope, receive, send)
                    return
        await self.app(scope, receive, send)
