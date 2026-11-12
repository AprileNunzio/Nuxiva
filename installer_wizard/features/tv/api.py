from pathlib import Path
import re
import httpx

from access import require_admin
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from starlette.background import BackgroundTask
from state import store

from features.tv import relay, targets
from features.tv.m3u import MAX_BYTES, PlaylistError
from features.tv.store import tv_store

admin_routes = APIRouter()
public_routes = APIRouter()
WATCH = Path(__file__).resolve().parent / "watch.html"


def _bad(exc: Exception, code: int = 400):
    raise HTTPException(code, str(exc))


def _check_vpn_constraint():
    """Verifica il rispetto della policy VPN obbligatoria per lo streaming IPTV."""
    settings = tv_store.settings()
    if not settings.get("vpn_required"):
        return

    try:
        from features.vpn.service import service as vpn_svc
        target_profile = settings.get("vpn_profile")
        if target_profile:
            is_connected = bool(vpn_svc.state.get(target_profile, {}).get("connected"))
        else:
            is_connected = any(st.get("connected") for st in vpn_svc.state.values())
    except Exception:
        is_connected = False

    if not is_connected:
        raise HTTPException(
            403,
            "VPN_REQUIRED: Connessione VPN obbligatoria non attiva. "
            "La riproduzione IPTV è protetta e richiede una VPN attiva per garantire la privacy."
        )


@admin_routes.get("/api/tv")
async def tv_overview(_: str = Depends(require_admin)):
    channels = tv_store.channels()
    groups = sorted({c["group"] for c in channels if c["group"]})
    return {
        "playlists": tv_store.playlists(),
        "count": len(channels),
        "groups": groups,
        "favorites": tv_store.favorites(),
        "tuners": tv_store.tuners(),
        "settings": tv_store.settings(),
    }


@admin_routes.get("/api/tv/channels")
async def tv_channels(
    q: str = "",
    group: str = "",
    fav: bool = False,
    page: int = 1,
    limit: int = 60,
    _: str = Depends(require_admin),
):
    favorites = set(tv_store.favorites())
    needle = q.strip().lower()[:80]
    rows = [
        c for c in tv_store.channels()
        if (not group or c["group"] == group)
        and (not fav or c["id"] in favorites)
        and (not needle or needle in c["name"].lower())
    ]
    rows.sort(key=lambda c: (c["id"] not in favorites, c["name"].lower()))
    page = max(1, page)
    total = len(rows)
    if limit <= 0:
        view = [
            {k: c[k] for k in ("id", "name", "group", "logo", "url")} | {"favorite": c["id"] in favorites}
            for c in rows
        ]
        return {"channels": view, "total": total, "page": 1, "pages": 1, "limit": total}

    pages = max(1, (total + limit - 1) // limit)
    page = min(page, pages)
    view = [
        {k: c[k] for k in ("id", "name", "group", "logo", "url")} | {"favorite": c["id"] in favorites}
        for c in rows[(page - 1) * limit: page * limit]
    ]
    return {"channels": view, "total": total, "page": page, "pages": pages, "limit": limit}


@admin_routes.get("/api/tv/settings")
async def tv_get_settings(_: str = Depends(require_admin)):
    return tv_store.settings()


@admin_routes.put("/api/tv/settings")
async def tv_update_settings(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    updated = tv_store.update_settings(body)
    store.event("INFO", f"Impostazioni TV aggiornate da {user}", "tv")
    return updated


@admin_routes.put("/api/tv/upload")
async def tv_upload(request: Request, user: str = Depends(require_admin)):
    name = request.query_params.get("name") or request.headers.get("X-File-Name") or "Playlist Caricata"
    try:
        body = await request.body()
    except Exception as exc:
        _bad(PlaylistError(f"Errore lettura dati: {exc}"))
    if len(body) > MAX_BYTES:
        _bad(PlaylistError("File playlist troppo grande"))
    text = body.decode("utf-8", errors="replace")
    try:
        entry = tv_store.add(name, "", text)
    except PlaylistError as exc:
        _bad(exc)
    store.event("INFO", f"Playlist TV «{entry['name']}» caricata da {user}: {entry['count']} canali", "tv")
    return entry


@admin_routes.get("/api/tv/tuners")
async def tv_tuners(_: str = Depends(require_admin)):
    return {"tuners": tv_store.tuners()}


@admin_routes.post("/api/tv/tuners/discover")
async def tv_tuners_discover(user: str = Depends(require_admin)):
    tuners = tv_store.discover_tuners()
    store.event("INFO", f"Discovery tuner TV avviata da {user}: {len(tuners)} tuner trovati", "tv")
    return {"tuners": tuners}


@admin_routes.post("/api/tv/tuners")
async def tv_add_tuner(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    try:
        tuner = tv_store.add_tuner(
            name=str(body.get("name") or ""),
            tuner_type=str(body.get("type") or "dvb_t2"),
            device=str(body.get("device") or ""),
            options=body.get("options")
        )
    except PlaylistError as exc:
        _bad(exc)
    store.event("INFO", f"Tuner «{tuner['name']}» ({tuner['type']}) aggiunto da {user}", "tv")
    return tuner


@admin_routes.delete("/api/tv/tuners/{tid}")
async def tv_remove_tuner(tid: str, user: str = Depends(require_admin)):
    tv_store.remove_tuner(tid)
    store.event("INFO", f"Tuner TV {tid} rimosso da {user}", "tv")
    return {"ok": True}


@admin_routes.post("/api/tv/tuners/{tid}/scan")
async def tv_tuner_scan(tid: str, user: str = Depends(require_admin)):
    try:
        tuner = tv_store.scan_tuner(tid)
    except PlaylistError as exc:
        _bad(exc, 404)
    store.event("INFO", f"Scansione frequenze reale completata su {tuner['name']} da {user}: {tuner['channels_count']} canali", "tv")
    return {"ok": True, "tuner": tuner}


@admin_routes.get("/api/tv/epg/{cid}")
async def tv_epg(cid: str, _: str = Depends(require_admin)):
    try:
        return tv_store.epg(cid)
    except PlaylistError as exc:
        _bad(exc, 404)


@admin_routes.post("/api/tv/epg/refresh")
async def tv_epg_refresh(request: Request, user: str = Depends(require_admin)):
    body = await request.json() if request.headers.get("content-length") else {}
    url = str(body.get("url") or "")
    try:
        result = await tv_store.refresh_epg(url)
    except PlaylistError as exc:
        _bad(exc, 502)
    store.event("INFO", f"Guida EPG XMLTV aggiornata da {user}: {result['total_programs']} programmi", "tv")
    return result


@admin_routes.post("/api/tv/playlists")
async def tv_add(request: Request, user: str = Depends(require_admin)):
    body = await request.json()
    text = str(body.get("text") or "")
    if len(text) > MAX_BYTES:
        _bad(PlaylistError("Playlist troppo grande"))
    try:
        entry = tv_store.add(str(body.get("name") or ""), str(body.get("url") or ""), text)
        if entry["source"] == "url":
            entry = await tv_store.refresh(entry["id"])
    except PlaylistError as exc:
        _bad(exc)
    store.event("INFO", f"Playlist TV «{entry['name']}» aggiunta da {user}: {entry['count']} canali", "tv")
    return entry


@admin_routes.post("/api/tv/playlists/{pid}/refresh")
async def tv_refresh(pid: str, _: str = Depends(require_admin)):
    try:
        return await tv_store.refresh(pid)
    except PlaylistError as exc:
        _bad(exc, 502)


@admin_routes.delete("/api/tv/playlists/{pid}")
async def tv_remove(pid: str, user: str = Depends(require_admin)):
    try:
        tv_store.remove(pid)
    except PlaylistError as exc:
        _bad(exc)
    store.event("INFO", f"Playlist TV {pid} rimossa da {user}", "tv")
    return {"ok": True}


@admin_routes.put("/api/tv/favorites/{cid}")
async def tv_favorite(cid: str, request: Request, _: str = Depends(require_admin)):
    try:
        return {"favorites": tv_store.set_favorite(cid, bool((await request.json()).get("on")))}
    except PlaylistError as exc:
        _bad(exc)


@admin_routes.get("/api/tv/targets")
async def tv_targets(discover: bool = False, _: str = Depends(require_admin)):
    return {"targets": await targets.listing(discover)}


@admin_routes.post("/api/tv/play")
async def tv_play(request: Request, user: str = Depends(require_admin)):
    _check_vpn_constraint()
    body = await request.json()
    channel = tv_store.channel(str(body.get("channel") or ""))
    if not channel:
        raise HTTPException(404, "Canale sconosciuto")
    try:
        where = await targets.play(channel, str(body.get("target") or "display"), user)
    except targets.TargetError as exc:
        _bad(exc, 409)
    return {"ok": True, "where": where, "preview": targets.live_path(channel)}


@admin_routes.get("/api/tv/preview/{cid}")
async def tv_preview(cid: str, _: str = Depends(require_admin)):
    channel = tv_store.channel(cid)
    if not channel:
        raise HTTPException(404, "Canale sconosciuto")
    return {"src": targets.live_path(channel), "name": channel["name"]}


@admin_routes.post("/api/tv/stop")
async def tv_stop(request: Request, _: str = Depends(require_admin)):
    try:
        body = await request.json()
        target_id = str(body.get("target") or "display")
    except Exception:
        target_id = "display"
    await targets.stop(target_id)
    return {"ok": True}


@admin_routes.post("/api/tv/cast/control")
async def tv_cast_control(request: Request, _: str = Depends(require_admin)):
    body = await request.json()
    target_id = str(body.get("target") or "")
    action = str(body.get("action") or "pause")
    value = float(body.get("value") or 0.0)
    try:
        await targets.control(target_id, action, value)
    except Exception as exc:
        _bad(exc, 400)
    return {"ok": True}


@admin_routes.get("/tv/watch")
@public_routes.get("/tv/watch")
async def tv_watch():
    return FileResponse(WATCH, media_type="text/html", headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


async def _relay(cid: str, url: str, token: str, wanted_range: str | None = None, request: Request | None = None) -> Response:
    _check_vpn_constraint()
    channel = tv_store.channel(cid)
    is_valid = relay.valid(cid, token)
    if not is_valid and request is not None:
        try:
            from access import session_user
            if session_user(request):
                is_valid = True
                token = relay.token_for(cid)
        except Exception:
            pass
    if not channel or not is_valid:
        raise HTTPException(401, "Collegamento scaduto o non valido")
    if not relay.allowed(channel["url"], url):
        raise HTTPException(403, "Sorgente non ammessa")
    try:
        client, res = await relay.open_upstream(url, relay.range_header(wanted_range))
    except relay.RelayError as exc:
        raise HTTPException(502, str(exc))
    kind = res.headers.get("content-type", "application/octet-stream")
    if relay.is_dash(str(res.url), kind):
        try:
            body = relay.rewrite_dash(await relay.read_playlist(res), str(res.url), cid, token, channel["url"])
        except relay.RelayError as exc:
            raise HTTPException(502, str(exc))
        finally:
            await res.aclose()
            await client.aclose()
        return Response(body, media_type=relay.DASH_TYPE, headers=relay.CORS)
    if relay.is_playlist(str(res.url), kind):
        try:
            text = await relay.read_playlist(res)
        except relay.RelayError as exc:
            raise HTTPException(502, str(exc))
        finally:
            await res.aclose()
            await client.aclose()
        body = relay.rewrite(text, str(res.url), cid, token, channel["url"])
        return Response(body, media_type="application/vnd.apple.mpegurl", headers=relay.CORS)

    async def close() -> None:
        await res.aclose()
        await client.aclose()
    passed = {k: v for k, v in res.headers.items() if k.lower() in relay.PASS_HEADERS}
    return StreamingResponse(
        res.aiter_raw(),
        status_code=206 if res.status_code == 206 else 200,
        media_type=kind.split(";")[0][:80],
        headers={**relay.CORS, **passed},
        background=BackgroundTask(close),
    )


@admin_routes.get("/api/tv/proxy/logo")
@public_routes.get("/api/tv/proxy/logo")
async def tv_proxy_logo(url: str):
    if not url or not url.startswith(("http://", "https://")):
        raise HTTPException(400, "URL non valido")

    urls_to_try = [url]
    m = re.match(r"^(https?://upload\.wikimedia\.org/wikipedia/commons)/thumb/([0-9a-f]/[0-9a-f]{2}/[^/]+)/.*$", url)
    if m:
        urls_to_try.append(f"{m.group(1)}/{m.group(2)}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Nuxiva/1.0",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    if "imgur.com" in url:
        headers["Referer"] = "https://imgur.com/"

    for target_url in urls_to_try:
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers) as client:
                resp = await client.get(target_url)
                if resp.status_code == 200 and resp.content:
                    media_type = resp.headers.get("content-type") or "image/png"
                    return Response(
                        resp.content,
                        media_type=media_type,
                        headers={
                            "Cache-Control": "public, max-age=86400",
                            "Access-Control-Allow-Origin": "*",
                        }
                    )
        except Exception:
            continue
    raise HTTPException(404, "Impossibile scaricare il logo")


@admin_routes.get("/api/tv/live/{cid}")
@public_routes.get("/api/tv/live/{cid}")
async def tv_live(cid: str, request: Request, t: str = ""):
    channel = tv_store.channel(cid)
    if not channel:
        raise HTTPException(404, "Canale sconosciuto")
    return await _relay(cid, channel["url"], t, request.headers.get("range"), request=request)


@admin_routes.get("/api/tv/dash/{cid}/{token}/{base}/{rest:path}")
@public_routes.get("/api/tv/dash/{cid}/{token}/{base}/{rest:path}")
async def tv_dash(cid: str, token: str, base: str, rest: str, request: Request):
    try:
        url = relay.dash_target(cid, base, rest, request.url.query)
    except relay.RelayError as exc:
        raise HTTPException(403, str(exc))
    return await _relay(cid, url, token, request.headers.get("range"), request=request)


@admin_routes.get("/api/tv/seg/{cid}")
@public_routes.get("/api/tv/seg/{cid}")
async def tv_segment(cid: str, request: Request, u: str = "", s: str = "", t: str = ""):
    try:
        url = relay.decode(cid, u[:4000], s)
    except relay.RelayError as exc:
        raise HTTPException(403, str(exc))
    return await _relay(cid, url, t, request.headers.get("range"), request=request)
