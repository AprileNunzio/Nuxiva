import time
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class AgentCapabilitySpec(BaseModel):
    id: str
    name: str
    role_category: str # "executive", "engineering", "social", "productivity", "household", "design"
    avatar_icon: str
    description: str
    system_prompt: str
    tools: List[str] = Field(default_factory=list)
    widgets: List[str] = Field(default_factory=list)
    is_custom: bool = False
    created_at: float = Field(default_factory=time.time)

DEFAULT_AGENT_CATALOG: Dict[str, AgentCapabilitySpec] = {
    "chief_supervisor": AgentCapabilitySpec(
        id="chief_supervisor",
        name="Capo Agente (Chief Supervisor)",
        role_category="executive",
        avatar_icon="shield-alert",
        description="Supervisore esecutivo 24/7. Monitora tutti gli agenti, previene loop infiniti e aggiorna la percentuale di avanzamento del progetto.",
        system_prompt="Sei il Capo Agente di Nuxiva. Il tuo compito è coordinare il team, validare i deliverable, individuare stalli o loop ripetitivi ed emettere report e diagrammi di avanzamento.",
        tools=["chief_anti_loop_watchdog", "recalculate_milestones", "broadcast_war_room"],
        widgets=["chief_supervision_hud", "war_room_thought_graph"],
        is_custom=False,
    ),
    "project_director": AgentCapabilitySpec(
        id="project_director",
        name="Project Director (PM)",
        role_category="executive",
        avatar_icon="clipboard-list",
        description="Pianificazione strategica, roadmap, suddivisione milestone e assegnazione task al team.",
        system_prompt="Sei il Project Director. Scomponi gli obiettivi dell'utente in milestone realistiche con criteri di accettazione rigorosi.",
        tools=["create_milestone", "assign_agent_task", "export_gantt"],
        widgets=["gantt_milestone_tracker"],
        is_custom=False,
    ),
    "google_suite_agent": AgentCapabilitySpec(
        id="google_suite_agent",
        name="Google Suite Specialist",
        role_category="productivity",
        avatar_icon="mail",
        description="Gestione integrata Google Workspace: Gmail, Google Calendar, Google Drive, Docs e Google Sheets.",
        system_prompt="Sei lo specialista Google Workspace. Gestisci corrispondenza email, sincronizzi appuntamenti in calendario e prepari documenti e fogli di calcolo.",
        tools=["google_gmail_send", "google_calendar_schedule", "google_drive_manage", "google_sheets_sync"],
        widgets=["google_workspace_widget"],
        is_custom=False,
    ),
    "instagram_agent": AgentCapabilitySpec(
        id="instagram_agent",
        name="Instagram & Social Strategist",
        role_category="social",
        avatar_icon="camera",
        description="Creazione e pianificazione post, caroselli, reel, copywriting accattivante e analisi hashtag per Instagram.",
        system_prompt="Sei l'agente specializzato in Instagram. Progetta piani editoriali, scrivi caption efficaci con hook potente e pianifica pubblicazioni.",
        tools=["instagram_generate_copy", "instagram_plan_carousel", "instagram_schedule_post"],
        widgets=["instagram_feed_preview"],
        is_custom=False,
    ),
    "telegram_master": AgentCapabilitySpec(
        id="telegram_master",
        name="Telegram Channel & Bot Master",
        role_category="social",
        avatar_icon="send",
        description="Gestione canali Telegram, broadcast comunicazioni, notifiche in tempo reale e gestione bot interattivi con tastiere inline.",
        system_prompt="Sei il gestore ufficiale dei canali e bot Telegram. Invia aggiornamenti in tempo reale e gestisci comandi interattivi.",
        tools=["telegram_broadcast_message", "telegram_create_poll", "telegram_manage_inline_buttons"],
        widgets=["telegram_channel_monitor"],
        is_custom=False,
    ),
    "autocad_designer": AgentCapabilitySpec(
        id="autocad_designer",
        name="AutoCAD & 3D CAD Engineer",
        role_category="design",
        avatar_icon="drafting-compass",
        description="Generazione disegni tecnici, script DXF/DWG parametrici, quotature e distinte materiali per ingegneria e architettura.",
        system_prompt="Sei l'ingegnere CAD di Nuxiva. Generi script geometrici precisi, file DXF ed esporti specifiche tecniche per produzione o stampa 3D.",
        tools=["cad_generate_dxf", "cad_calculate_bom", "cad_render_schematic"],
        widgets=["cad_viewport_viewer"],
        is_custom=False,
    ),
    "fullstack_coder": AgentCapabilitySpec(
        id="fullstack_coder",
        name="Fullstack Software Engineer",
        role_category="engineering",
        avatar_icon="code",
        description="Scrittura codice Python, TypeScript, React, backend API e architetture database con self-healing.",
        system_prompt="Sei il programmatore Fullstack. Implementi codice pulito, sicuro e performante in linea con i pattern del progetto.",
        tools=["code_sandbox_run", "git_commit_push", "run_unit_tests"],
        widgets=["code_ide_diff_viewer"],
        is_custom=False,
    ),
    "devops_engineer": AgentCapabilitySpec(
        id="devops_engineer",
        name="DevOps & Cloud Architect",
        role_category="engineering",
        avatar_icon="server",
        description="Gestione container Docker, pipeline CI/CD, monitoraggio salute server e deploy.",
        system_prompt="Sei il DevOps Engineer. Assicuri che l'infrastruttura sia solida, monitorata e senza downtime.",
        tools=["docker_inspect_deploy", "server_metrics_check", "logs_analyzer"],
        widgets=["devops_terminal_console"],
        is_custom=False,
    ),
    "data_analyst": AgentCapabilitySpec(
        id="data_analyst",
        name="Data & Business Analyst",
        role_category="productivity",
        avatar_icon="bar-chart",
        description="Analisi dati, estrazione statistiche, generazione grafici e report previsionali.",
        system_prompt="Sei l'analista dati. Trasforma log e informazioni grezze in grafici chiari e insight strategici.",
        tools=["run_data_analytics", "generate_chart_report"],
        widgets=["analytics_chart_widget"],
        is_custom=False,
    ),
    "home_butler_agent": AgentCapabilitySpec(
        id="home_butler_agent",
        name="Smart Butler & Household Specialist",
        role_category="household",
        avatar_icon="home",
        description="Coordinamento residenziale, scorte, promemoria per il personale (autista, maggiordomo, pulizie) e scenari domotici.",
        system_prompt="Sei il maggiordomo neurale per la residenza. Coordina le attività domestiche e assisti la famiglia e il personale con massima efficienza e discrezione.",
        tools=["smart_home_scene_trigger", "inventory_restock_alert", "staff_task_assign"],
        widgets=["smart_residence_dashboard"],
        is_custom=False,
    ),
}
