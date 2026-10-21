from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ContextDimension(BaseModel):
    user_role: str = "user_primary"
    active_environment: str = "smart_home"
    available_plugins: List[str] = Field(default_factory=list)
    active_widgets: List[str] = Field(default_factory=list)
    system_load: float = 0.15
    privacy_mode: bool = False
    preferred_language: str = "it"


class CandidateAction(BaseModel):
    action_id: str
    target_agent: str
    subagent_id: Optional[str] = None
    required_tool: Optional[str] = None
    associated_widget: Optional[str] = None
    base_utility: float = 1.0
    execution_cost: float = 0.1
    privacy_risk: float = 0.0


TARGET_KEYWORDS: Dict[str, List[str]] = {
    "google_gmail": ["mail", "email", "gmail", "invia mail", "messaggio", "posta", "scrivi a"],
    "google_calendar": ["calendario", "calendar", "evento", "appuntamento", "riunione", "orario", "fissa"],
    "google_contacts": ["contatto", "contatti", "rubrica", "numero", "indirizzo", "persona", "trova contatto"],
    "google_classroom": ["classroom", "lezione", "compito", "corso", "materia", "studenti", "scuola"],
    "google_drive": ["drive", "file", "cartella", "documento", "pdf", "salva file", "upload"],
    "home_assistant": ["luci", "luce", "accendi", "spegni", "porta", "temperatura", "termostato"],
    "cad_engineer": ["cad", "dxf", "disegno", "dwg", "flangia", "ingegneria", "quota"],
    "social_media": ["instagram", "post", "copy", "social", "caption", "feed", "telegram"],
}


def build_default_candidate_actions() -> List[CandidateAction]:
    return [
        CandidateAction(
            action_id="gmail_send_message",
            target_agent="google_suite_agent",
            subagent_id="google_gmail",
            required_tool="google_gmail_tool",
            associated_widget="gmail_composer_card",
            base_utility=2.8,
            execution_cost=0.15,
            privacy_risk=0.1,
        ),
        CandidateAction(
            action_id="calendar_schedule_event",
            target_agent="google_suite_agent",
            subagent_id="google_calendar",
            required_tool="google_calendar_tool",
            associated_widget="calendar_card",
            base_utility=2.6,
            execution_cost=0.12,
            privacy_risk=0.05,
        ),
        CandidateAction(
            action_id="contacts_lookup_person",
            target_agent="google_suite_agent",
            subagent_id="google_contacts",
            required_tool="google_contacts_tool",
            associated_widget="contacts_card",
            base_utility=2.4,
            execution_cost=0.1,
            privacy_risk=0.2,
        ),
        CandidateAction(
            action_id="classroom_manage_course",
            target_agent="google_suite_agent",
            subagent_id="google_classroom",
            required_tool="google_classroom_tool",
            associated_widget="classroom_card",
            base_utility=2.5,
            execution_cost=0.14,
            privacy_risk=0.1,
        ),
        CandidateAction(
            action_id="drive_sync_file",
            target_agent="google_suite_agent",
            subagent_id="google_drive",
            required_tool="google_drive_tool",
            associated_widget="drive_card",
            base_utility=2.7,
            execution_cost=0.18,
            privacy_risk=0.15,
        ),
        CandidateAction(
            action_id="smart_home_toggle",
            target_agent="agent_home_assistant",
            subagent_id="home_assistant",
            required_tool="homeassistant_toggle",
            associated_widget="smart_switch",
            base_utility=3.0,
            execution_cost=0.08,
            privacy_risk=0.0,
        ),
        CandidateAction(
            action_id="cad_generate_dxf",
            target_agent="autocad_designer",
            subagent_id="cad_engineer",
            required_tool="cad_generate_dxf",
            associated_widget="cad_viewer",
            base_utility=2.9,
            execution_cost=0.25,
            privacy_risk=0.0,
        ),
        CandidateAction(
            action_id="social_instagram_draft",
            target_agent="instagram_agent",
            subagent_id="social_media",
            required_tool="instagram_generate_copy",
            associated_widget="social_post_preview",
            base_utility=2.5,
            execution_cost=0.12,
            privacy_risk=0.05,
        ),
    ]
