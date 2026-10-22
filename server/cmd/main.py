from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from server.config.env import settings
from server.shared.errors.global_handler import register_global_error_handlers
from server.core.security_guard.zero_trust_interceptor import ZeroTrustMiddleware
from server.core.agent_registry.pool_manager import agent_pool
from server.features.home_assistant_bridge.ha_agent import HomeAssistantAgent
from server.features.vision_surveillance.surveillance_agent import VisionSurveillanceAgent
from server.features.self_healing_coder.coder_agent import SelfHealingCoderAgent
from server.features.analytic_agent.analytic_agent import AnalyticReasonerAgent
from server.features.parametric.designer_agent import ParametricDesignerAgent
from server.features.skill_synthesis.composition import dynamic_tools_agent, tool_builder_agent
from server.features.sysops_automation.sysops_agent import SysOpsAutomationAgent
from server.cmd.api_routes import router, router_v2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("nuxiva.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    from server.features.music_library.scanner import music_organizer
    from server.core.sensory_bus.event_router import sensory_bus
    from server.core.sensory_bus.actuator_gateway import actuator_gateway
    from server.features.project_workspace.autonomous_runner import autonomous_runner
    import asyncio
    asyncio.create_task(music_organizer.scan_loop())
    sensory_bus.start()
    actuator_gateway.attach_to_bus()
    autonomous_runner.start()
    from server.core.plasticity.composition import plasticity_service
    from server.core.plasticity.scheduler import rem_loop
    rem_task = asyncio.create_task(rem_loop(plasticity_service))

    try:
        from server.core.db.database import engine, Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database ORM Inizializzato (Tabelle sincronizzate).")
    except Exception as e:
        logger.error("Impossibile connettersi al database: %s", str(e))

    from server.core.cognitive_audit.embedding_engine import embedding_engine
    from server.core.context_graph.graph_client import graph_client

    model_ok = await embedding_engine.ensure_model_available()
    if not model_ok:
        logger.warning("Embedding model not found! Run: ollama pull nomic-embed-text")

    from server.core.orchestrator.interrupt_manager import project_manager
    project_manager.mark_interrupted_projects()

    logger.info(
        "Nuxiva v2.0.0 online — %d agents, %d graph nodes, %d graph edges",
        len(agent_pool.list_agents()),
        graph_client.node_count(),
        graph_client.edge_count(),
    )
    yield
    rem_task.cancel()

def create_application() -> FastAPI:
    app = FastAPI(
        title="Nuxiva Autonomous Cognitive Orchestrator",
        version="5.3.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    origins = [o.strip() for o in settings.NUXIVA_CORS_ORIGINS.split(",") if o.strip() and o.strip() != "*"]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type", "Accept-Language"],
        )
    app.add_middleware(ZeroTrustMiddleware)
    
    from server.shared.i18n.middleware import I18nMiddleware
    app.add_middleware(I18nMiddleware)

    register_global_error_handlers(app)

    try:
        from server.core.observability.telemetry import setup_telemetry
        setup_telemetry(app)
    except ImportError:
        logger.warning("Modulo Telemetry non trovato. Ignoro OpenTelemetry.")

    from server.features.agent_tools.scanner import tool_scanner
    discovered_tools = tool_scanner.scan_all()
    logger.info("Tool dinamici scansionati e registrati: %d", len(discovered_tools))

    agent_pool.register_agent(HomeAssistantAgent())
    agent_pool.register_agent(VisionSurveillanceAgent())
    agent_pool.register_agent(SelfHealingCoderAgent())
    agent_pool.register_agent(SysOpsAutomationAgent())
    agent_pool.register_agent(AnalyticReasonerAgent())
    agent_pool.register_agent(ParametricDesignerAgent())
    agent_pool.register_agent(dynamic_tools_agent)
    agent_pool.register_agent(tool_builder_agent)
    logger.info("Core agents registered: %s", agent_pool.list_agents())

    try:
        from server.web.features.computer_control.api import router as computer_control_router
        app.include_router(computer_control_router)
        logger.info("Computer Control UI router caricato.")
    except Exception as e:
        logger.error("Errore nel caricare computer control UI: %s", str(e))

    try:
        from server.core.games_scanner.api import router as games_scanner_router
        app.include_router(games_scanner_router)
    except Exception as e:
        logger.error("Errore nel caricare games scanner API: %s", str(e))

    from server.core.hippocampus_router.api import router as hippocampus_router
    app.include_router(hippocampus_router)
    from server.core.skill_forge.api import router as skill_forge_router
    from server.core.plasticity.api import router as plasticity_router
    app.include_router(skill_forge_router)
    app.include_router(plasticity_router)
    app.include_router(router)
    app.include_router(router_v2)

    web_dir = Path(__file__).resolve().parent.parent / "web"
    if web_dir.exists():
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

        @app.get("/")
        async def serve_index():
            return FileResponse(str(web_dir / "index.html"))

        @app.get("/web")
        async def serve_web_page():
            return FileResponse(str(web_dir / "index.html"))


    @app.get("/health")
    async def health_check():
        from server.core.context_graph.graph_client import graph_client
        return {
            "status": "HEALTHY",
            "version": "5.3.0",
            "orchestrator": "ONLINE",
            "active_agents": agent_pool.list_agents(),
            "knowledge_graph": {
                "nodes": graph_client.node_count(),
                "edges": graph_client.edge_count(),
            },
            "upgrades": [
                "llm_intent_classifier",
                "react_reasoning_loop",
                "task_planner",
                "persistent_knowledge_graph",
                "real_embeddings",
                "skill_synthesis",
                "self_critique",
                "tool_protocol",
                "hardware_aware_onboarding",
                "semantic_fast_path_cache",
                "system1_non_autoregressive_router",
                "system2_latent_reasoning_engine",
                "realtime_streaming_web_interface",
                "nuxiva_probabilistic_decision_arbiter_v2",
            ],
        }

    return app

app = create_application()

if __name__ == "__main__":
    port_to_bind = int(os.environ.get("NUXIVA_PORT", getattr(settings, "NUXIVA_PORT", 80)))
    uvicorn.run(
        "server.cmd.main:app",
        host=settings.NUXIVA_HOST,
        port=port_to_bind,
        reload=(settings.NUXIVA_ENV == "development"),
    )
