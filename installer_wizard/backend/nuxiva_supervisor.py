# flake8: noqa: E402
import asyncio
import logging
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent
_WIZARD = _BACKEND.parent
_ROOT = _WIZARD.parent

for _p in (str(_ROOT), str(_WIZARD), str(_BACKEND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import uvicorn
from fastapi import FastAPI, Request, Response

import body_errors
from feature_api_scanner import discover_feature_apis
import bus_api
import licensing_api
import health
from loops import supervisor as loop_supervisor
import pages
import registry_api
import setup_api
import packages_api
import system_api
import mesh_api
import node_api
import node_commands_api
from features.update_center import api as update_center_api
import updater
from config import ADMIN_PORT, DEMO, PUBLIC_PORT, VERSION, env_get
from origin_guard import OriginGuard
from nuxiva_bus import nuxiva_bus
from feature_registry import registry
from features.brain import api as brain_api
from features.brain import routing as brain_routing
from features.presentation import api as presentation_api
from features.secure import api as secure_api
from features.actions import api as actions_api
from features.bluetooth import api as bluetooth_api
from features.bluetooth.service import service as bluetooth_service
from features.vision.tips import tips as object_tips
from features.nodes.beacon import beacon as node_beacon
from features.chat import api as chat_api
from features.nodes import api as nodes_api
from features.cloud import api as cloud_api
from features.desktop import api as desktop_api
from features.desktop.desk import desk
from features.desktop.secretary import secretary
from features.documents import api as documents_api
from features.devices import api as devices_api
from features.devices import audio
from features.google import api as google_api
from features.google.gservices import google
from features.home_assistant import api as home_api
from features.home_assistant import home
from features.location import api as location_api
from features.cameras import api as cameras_api
from features.models3d import api as models3d_api
from features.models3d import studio_api as models3d_studio_api
from features.ear import api as ear_api
from features.automations import api as automations_api
from features.automations.engine import engine as automations_engine
from features.autonomy import api as autonomy_api
from features.avatars import api as avatars_api
from features.capabilities import api as capabilities_api
from features.habits import api as habits_api
from features.kiosk import driver as display_driver
from features.habits.service import habits
from features.governor import api as governor_api
from features.governor.service import governor
from features.scheduler import api as scheduler_api
from features.selftest import api as selftest_api
from features.shares import api as shares_api
from features.vault import api as vault_api
from features.vault.service import vault
from features.selftest.service import selftest
from features.sounds import api as sounds_api
from features.autonomy.engine import autonomy
from features.cameras import autosetup as cameras_autosetup
from features.cameras import controls as cameras_controls
from features.cameras import motion as cameras_motion
from features.cameras.recorder import recorder as cameras_recorder
from features.laws import api as laws_api
from features.maps import api as maps_api
from features.mind import api as mind_api
from features.authz import api as authz_api
from features.locale import api as locale_api
from features.locale.colocated import api as i18n_bundle_api
from features.locale.colocated import handlers as i18n_handlers
from features.firewall import api as firewall_api
from features.firewall.events import monitor as firewall_monitor
from features.vpn import api as vpn_api
from features.places import api as places_api
from features.sports import api as sports_api
from features.tv import api as tv_api
from features.hub import api as hub_api
from features.tv import service as tv_service
from features.sports.watch import watcher as sports_watcher
from features.proxmox import api as proxmox_api
from features.voicestudio import api as voicestudio_api
from features.nodes import display_link as display_link_api
from features.ducking import api as ducking_api
from features.redalert import api as redalert_api
from features.ducking.ducker import ducker
from features.places import service as places_service
from features.locale import household as locale_household
from features.vpn.service import service as vpn_service
from features.maps.maps import maps
from features.mcpclient import api as mcpclient_api
from features.mcpclient.service import run as mcpclient_run
from features.music import api as music_api
from features.music import api_library as music_library_api
from features.music import api_play as music_play_api
from features.music import api_playlists as music_playlists_api
from features.music import api_share as music_share_api
from features.music import subsonic as music_subsonic_api
from features.music.outputs import outputs as music_outputs
from features.music.service import library as music_library
from features.network import api as network_api
from features.network.explorer import explorer
from features.people import api as people_api
from features.people import presence
from features.people.vitals.local_ble import local_ble as vitals_local_ble
from features.skills import api as skills_api
from features.soup import api as soup_api
from features.study import api as study_api
from features.study import study
from features.diorama import learning as diorama_learning
from features.team import api as team_api
from features.experts import api as experts_api
from features.backup import api as backup_api
from features.backup import service as backup_service
from features.projects import api as projects_api
from features.projects import service as projects_service
from features.camsense import service as camsense_service
from features.telegram import api as telegram_api
from features.understanding import api as understanding_api
from features.telegram.bot import bot
from features.vision import api as vision_api
from features.vision.nightly import loop as nightly_biometrics_loop
from features.whiteboard import api as whiteboard_api
from features.printers import api as printers_api
from features.rpa import api as rpa_api
from features.nvr import api as nvr_api
from features.nvr.service import nvr as nvr_service
from features.scene import api as scene_api
from features.nexus import api as nexus_api
from features.flows import api as flows_api
from features.flows import watchdog as flows_watchdog
from features.scene.service import scene as scene_service
from features.twin import api as twin_api
from features.vision.webcams import webcams
from features.voices import api as voices_api
from orchestrator import orch, telemetry_loop

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
log = logging.getLogger("nuxiva.supervisor")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

FEATURE_APIS = (
    secure_api,
    presentation_api,
    actions_api,
    bluetooth_api,
    chat_api,
    cloud_api,
    voices_api,
    vision_api,
    devices_api,
    location_api,
    people_api,
    music_api,
    music_library_api,
    music_playlists_api,
    music_play_api,
    music_share_api,
    music_subsonic_api,
    study_api,
    soup_api,
    network_api,
    telegram_api,
    home_api,
    brain_api,
    desktop_api,
    google_api,
    maps_api,
    skills_api,
    nodes_api,
    mind_api,
    authz_api,
    locale_api,
    i18n_bundle_api,
    firewall_api,
    vpn_api,
    places_api,
    sports_api,
    tv_api,
    hub_api,
    proxmox_api,
    voicestudio_api,
    display_link_api,
    ducking_api,
    redalert_api,
    laws_api,
    cameras_api,
    models3d_studio_api,
    models3d_api,
    documents_api,
    ear_api,
    autonomy_api,
    avatars_api,
    automations_api,
    sounds_api,
    selftest_api,
    habits_api,
    vault_api,
    shares_api,
    scheduler_api,
    governor_api,
    capabilities_api,
    team_api,
    experts_api,
    projects_api,
    backup_api,
    mcpclient_api,
    whiteboard_api,
    understanding_api,
    printers_api,
    rpa_api,
    nvr_api,
    twin_api,
    scene_api,
    nexus_api,
    flows_api,
)


def build(admin: bool) -> FastAPI:
    title = "Nuxiva OS Admin" if admin else "Nuxiva OS"
    app = FastAPI(title=title, docs_url=None, redoc_url=None, openapi_url=None)
    body_errors.install(app)
    i18n_handlers.install(app)
    client_web_dist = Path(__file__).resolve().parent.parent.parent / "client_web" / "dist"
    if admin:
        pages.mount_static(app, "shared")
    else:
        pages.mount_static(app, "shared", "display", "monitor", "screen", "setup")

    if admin and (client_web_dist / "index.html").is_file():
        # Register before the assets mount: preview and desktop share one release.
        @app.get("/assets/webos-preview/index.html", include_in_schema=False)
        async def serve_webos_preview(request: Request):
            from features.nexus.api import nexus_index
            return await nexus_index(request)

    if (client_web_dist / "assets").exists():
        from fastapi.staticfiles import StaticFiles
        app.mount("/assets", StaticFiles(directory=str(client_web_dist / "assets")), name="client-web-assets")

    @app.get("/favicon.ico", include_in_schema=False)
    async def serve_favicon():
        return Response(status_code=204)

    giochi_dir = Path(__file__).resolve().parent.parent.parent / "giochi"
    if giochi_dir.exists():
        from fastapi.staticfiles import StaticFiles

        app.mount(
            "/giochi",
            StaticFiles(directory=str(giochi_dir)),
            name="static-giochi",
        )

    web_dir = Path(__file__).resolve().parent.parent.parent / "server" / "web"
    if web_dir.exists():
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse

        app.mount(
            "/static/dualbrain",
            StaticFiles(directory=str(web_dir)),
            name="static-dualbrain",
        )
        if not admin:

            @app.get("/web")
            async def serve_dualbrain_web():
                return FileResponse(str(web_dir / "index.html"))

    kind = "admin_routes" if admin else "public_routes"
    for module in (*FEATURE_APIS, *discover_feature_apis(), bus_api, licensing_api, registry_api, pages, setup_api, packages_api, system_api, mesh_api, node_api, node_commands_api, update_center_api):
        routes = getattr(module, kind, None)
        if routes is not None:
            app.include_router(routes)

    if admin:
        try:
            from server.web.features.computer_control.api import router as computer_control_router
        except ImportError as exc:
            log.error("Router computer_control non caricato: %s", exc)
        else:
            app.include_router(computer_control_router)

        try:
            from server.core.games_scanner.api import router as games_scanner_router
            app.include_router(games_scanner_router)
        except Exception as exc:
            log.warning("Router games_scanner non caricato: %s", exc)

        if client_web_dist.exists() and (client_web_dist / "index.html").exists():
            @app.get("/")
            @app.get("/canvas")
            @app.get("/node/{node_id:path}")
            @app.get("/apps/{app_id:path}")
            @app.get("/app/{app_id:path}")
            async def serve_admin_master_ui():
                return FileResponse(str(client_web_dist / "index.html"), headers={"Cache-Control": "no-cache"})

    allowed = f'{env_get("NUXIVA_ALLOWED_HOSTS")},{os.environ.get("NUXIVA_ALLOWED_HOSTS", "")}'
    app.add_middleware(OriginGuard, extra_hosts=allowed.split(","))
    return app


public = build(admin=False)
admin = build(admin=True)
from remote_admin import RemoteAdmin
public.mount("/admin", RemoteAdmin(admin), name="remote-admin")


def secure_server():
    import tls
    from config import STATE_DIR

    port = int(os.environ.get("NUXIVA_TLS_PORT", 8002 if DEMO else 443))
    try:
        material = tls.ensure_certificates(
            STATE_DIR / "tls", tls.local_names(), tls.local_addresses()
        )
        server = uvicorn.Server(
            uvicorn.Config(
                public,
                host="0.0.0.0",
                port=port,
                log_level="warning",
                ssl_certfile=str(material.cert),
                ssl_keyfile=str(material.key),
                timeout_graceful_shutdown=3,
            )
        )
    except Exception as exc:
        log.warning("HTTPS non disponibile: %s", exc)
        return None
    secure_api.announce(port)
    return server


async def serve_optional(server) -> None:
    try:
        await server.serve()
    except (SystemExit, Exception) as exc:
        log.warning("Il server HTTPS si è fermato: %s", exc)


BACKGROUND = (
    ("telemetria", telemetry_loop, 0.0),
    ("risorse", governor.run, 0.0),
    ("webcam", webcams.run, 0.0),
    ("avvio", orch.boot, 0.0),
    ("controllo-salute", lambda: health.Watchdog(orch).run(), 0.0),
    ("aggiornamenti", updater.scheduler, 0.0),
    ("presenze", presence.monitor.run, 0.0),
    ("telegram", bot.run, 0.0),
    ("rete", explorer.run, 0.0),
    ("audio", audio.watcher.run, 0.0),
    ("studio", study.engine.run, 0.0),
    ("diorami-appresi", diorama_learning.run, 0.0),
    ("addestramento", soup_api.trainer.run, 0.0),
    ("funzionalita", registry.run, 0.0),
    ("scrivania", desk.run, 0.0),
    ("segretario", secretary.run, 0.0),
    ("volume-conversazione", ducker.run, 0.0),
    ("google", google.run, 0.0),
    ("mappe", maps.run, 0.0),
    ("casa", home.brain.run, 0.0),
    ("bluetooth", bluetooth_service.run, 0.0),
    ("oggetti", object_tips.run, 0.0),
    ("nodi", node_beacon.run, 0.0),
    ("vitali-bluetooth", vitals_local_ble.run, 0.0),
    ("registrazioni-camere", cameras_recorder.run, 0.0),
    ("movimento-camere", cameras_motion.run, 0.0),
    ("controlli-webcam", cameras_controls.run, 0.0),
    ("auto-infrarosso", cameras_autosetup.run, 0.0),
    ("autonomia", autonomy.run, 0.0),
    ("automazioni", automations_engine.run, 60.0),
    ("autotest", selftest.loop, 0.0),
    ("abitudini", habits.run, 0.0),
    ("bus", nuxiva_bus.run, 0.0),
    ("nvr", nvr_service.run, 0.0),
    ("scena", scene_service.run, 0.0),
    ("cassaforte", vault.run, 0.0),
    ("schermo", display_driver.guard, 0.0),
    ("cervello", brain_routing.run, 0.0),
    ("musica", music_library.run, 0.0),
    ("uscite-musica", music_outputs.run, 0.0),
    ("mcp-esterni", mcpclient_run, 0.0),
    ("ottimizzazione-biometrica", nightly_biometrics_loop, 0.0),
    ("firewall", firewall_monitor.run, 0.0),
    ("vpn", vpn_service.run, 0.0),
    ("stanze", places_service.run, 0.0),
    ("sport", sports_watcher.run, 0.0),
    ("progetti", projects_service.run, 0.0),
    ("sensori-telecamera", camsense_service.run, 0.0),
    ("backup", backup_service.run, 0.0),
    ("tv", tv_service.run, 0.0),
    ("lingue-casa", locale_household.run, 0.0),
    ("flussi-sicurezza", flows_watchdog.run, 0.0),
)


def seed_experts() -> None:
    from features.experts import service as experts_service
    try:
        experts_service.seed_defaults(pages.ui_language() or "it")
    except Exception:
        log.exception("Esperti predefiniti non aggiunti")
    try:
        from features.fleet import mirror
        mirror.sync_all()
    except Exception:
        log.exception("Esperti non riportati nella flotta")


async def main() -> None:
    seed_experts()
    servers = [
        uvicorn.Server(
            uvicorn.Config(
                public,
                host="0.0.0.0",
                port=PUBLIC_PORT,
                log_level="warning",
                timeout_graceful_shutdown=3,
            )
        ),
        uvicorn.Server(
            uvicorn.Config(
                admin,
                host="0.0.0.0",
                port=ADMIN_PORT,
                log_level="warning",
                timeout_graceful_shutdown=3,
            )
        ),
    ]
    https = secure_server()
    log.info(
        "Nuxiva OS Supervisor v%s — utente :%d — admin :%d%s",
        VERSION,
        PUBLIC_PORT,
        ADMIN_PORT,
        " (DEMO)" if DEMO else "",
    )
    for name, factory, period in BACKGROUND:
        loop_supervisor.add(name, factory, period)
    tasks = [asyncio.create_task(loop_supervisor.run())]
    try:
        await asyncio.gather(
            *(s.serve() for s in servers), *([serve_optional(https)] if https else [])
        )
    finally:
        for t in tasks:
            t.cancel()
        study.engine.save()


if __name__ == "__main__":
    asyncio.run(main())
