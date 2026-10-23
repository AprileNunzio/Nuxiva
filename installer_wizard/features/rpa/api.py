import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse

from features.rpa import enrolled_package, package, releases

admin_routes = APIRouter(tags=["RPA"])
public_routes = APIRouter(tags=["RPA"])
admin_routes.include_router(enrolled_package.admin_routes)


def _server_address(request: Request) -> str:
    """Indirizzo pubblico di NUXIVA (le API dei nodi non stanno sulla porta del pannello di amministrazione)."""
    try:
        from config import PUBLIC_PORT
    except ImportError:
        PUBLIC_PORT = 80
    host = request.url.hostname or ""
    if not host or host in ("localhost", "127.0.0.1", "::1"):
        return ""
    return f"http://{host}" + ("" if PUBLIC_PORT == 80 else f":{PUBLIC_PORT}")


@admin_routes.get("/api/rpa/download-client")
@public_routes.get("/api/rpa/download-client")
async def download_client(request: Request, format: str = "exe"):
    if format != "zip":
        url = await releases.installer_url()
        if url:
            return RedirectResponse(url, status_code=302)
    if not os.path.isfile(os.path.join(package.ASSISTANT_DIR, "nuxiva_assistant.py")):
        raise HTTPException(
            status_code=404,
            detail=f"Sorgenti dell'Assistente Windows non trovati in {package.ASSISTANT_DIR}. "
                   "Verifica che la cartella client_satellite/windows_assistant sia presente nell'installazione di NUXIVA.",
        )
    return StreamingResponse(
        package.generate_zip(_server_address(request)),
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=NUXIVA_Assistente_Windows.zip"},
    )
