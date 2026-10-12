from enum import Enum
from typing import List, Dict, Optional, Set
from pydantic import BaseModel, Field

class TenancyProfile(str, Enum):
    HOME = "home"
    ENTERPRISE = "enterprise"

class SystemRole(str, Enum):
    # Enterprise Roles
    SUPERADMIN = "superadmin"
    PROJECT_LEAD = "project_lead"
    SPECIALIST = "specialist"
    EXTERNAL_CONTRACTOR = "external_contractor"
    AUDITOR = "auditor"
    
    # Household (Home) Roles
    OWNER_ADMIN = "owner_admin"
    FAMILY_MEMBER = "family_member"
    HOUSE_MANAGER = "house_manager"       # Maggiordomo / Amministratore Casa
    SECRETARY = "secretary"               # Segretaria personale
    CHAUFFEUR = "chauffeur"               # Autista
    HOUSEKEEPING = "housekeeping"         # Signora delle pulizie
    MAINTENANCE = "maintenance"           # Giardiniere / Tecnico impianti
    GUEST = "guest"                       # Ospite / Bambino

class ResourcePermission(str, Enum):
    # Progetti
    PROJECTS_CREATE = "projects:create"
    PROJECTS_VIEW_ALL = "projects:view_all"
    PROJECTS_VIEW_ASSIGNED = "projects:view_assigned"
    PROJECTS_EDIT = "projects:edit"
    PROJECTS_DELETE = "projects:delete"
    PROJECTS_RUN_247 = "projects:run_247"
    
    # Agenti
    AGENTS_ASSIGN = "agents:assign"
    AGENTS_MANAGE = "agents:manage"
    AGENTS_FORGE = "agents:forge"
    
    # War Room & Analytics
    WAR_ROOM_VIEW = "war_room:view"
    WAR_ROOM_POST = "war_room:post"
    WAR_ROOM_ANALYTICS = "war_room:analytics"
    
    # Sensori & Hardware
    SENSORY_WEBCAM_VIEW = "sensory:webcam_view"
    SENSORY_WEBCAM_HUD = "sensory:webcam_hud"
    SENSORY_MIC = "sensory:mic"
    HARDWARE_REMOTE_DESKTOP = "hardware:remote_desktop"
    HARDWARE_SMART_HOME = "hardware:smart_home"
    HARDWARE_VEHICLES = "hardware:vehicles"
    
    # Privacy & Finanze
    PRIVACY_CONFIDENTIAL_DOCS = "privacy:confidential_docs"
    PRIVACY_FINANCIALS = "privacy:financials"
    PRIVACY_FAMILY_ARCHIVE = "privacy:family_archive"

class UserAccount(BaseModel):
    user_id: str
    username: str
    display_name: str
    profile: TenancyProfile
    role: SystemRole
    face_encoding_id: Optional[str] = None
    voice_print_id: Optional[str] = None
    assigned_projects: List[str] = Field(default_factory=list)
    custom_permissions: List[ResourcePermission] = Field(default_factory=list)
    created_at: float = 0.0

ROLE_PERMISSIONS_MATRIX: Dict[SystemRole, Set[ResourcePermission]] = {
    # ENTERPRISE MATRIX
    SystemRole.SUPERADMIN: {p for p in ResourcePermission},
    SystemRole.PROJECT_LEAD: {
        ResourcePermission.PROJECTS_CREATE,
        ResourcePermission.PROJECTS_VIEW_ALL,
        ResourcePermission.PROJECTS_EDIT,
        ResourcePermission.PROJECTS_RUN_247,
        ResourcePermission.AGENTS_ASSIGN,
        ResourcePermission.AGENTS_MANAGE,
        ResourcePermission.AGENTS_FORGE,
        ResourcePermission.WAR_ROOM_VIEW,
        ResourcePermission.WAR_ROOM_POST,
        ResourcePermission.WAR_ROOM_ANALYTICS,
        ResourcePermission.SENSORY_WEBCAM_HUD,
        ResourcePermission.SENSORY_MIC,
        ResourcePermission.HARDWARE_SMART_HOME,
    },
    SystemRole.SPECIALIST: {
        ResourcePermission.PROJECTS_VIEW_ASSIGNED,
        ResourcePermission.PROJECTS_EDIT,
        ResourcePermission.WAR_ROOM_VIEW,
        ResourcePermission.WAR_ROOM_POST,
        ResourcePermission.WAR_ROOM_ANALYTICS,
        ResourcePermission.SENSORY_WEBCAM_HUD,
        ResourcePermission.SENSORY_MIC,
    },
    SystemRole.EXTERNAL_CONTRACTOR: {
        ResourcePermission.PROJECTS_VIEW_ASSIGNED,
        ResourcePermission.WAR_ROOM_VIEW,
        ResourcePermission.WAR_ROOM_POST,
    },
    SystemRole.AUDITOR: {
        ResourcePermission.PROJECTS_VIEW_ALL,
        ResourcePermission.WAR_ROOM_VIEW,
        ResourcePermission.WAR_ROOM_ANALYTICS,
    },
    
    # HOUSEHOLD (HOME) MATRIX
    SystemRole.OWNER_ADMIN: {p for p in ResourcePermission},
    SystemRole.FAMILY_MEMBER: {
        ResourcePermission.PROJECTS_CREATE,
        ResourcePermission.PROJECTS_VIEW_ASSIGNED,
        ResourcePermission.PROJECTS_EDIT,
        ResourcePermission.WAR_ROOM_VIEW,
        ResourcePermission.WAR_ROOM_POST,
        ResourcePermission.SENSORY_WEBCAM_VIEW,
        ResourcePermission.SENSORY_WEBCAM_HUD,
        ResourcePermission.SENSORY_MIC,
        ResourcePermission.HARDWARE_SMART_HOME,
        ResourcePermission.HARDWARE_VEHICLES,
        ResourcePermission.PRIVACY_FAMILY_ARCHIVE,
    },
    SystemRole.HOUSE_MANAGER: { # Maggiordomo
        ResourcePermission.PROJECTS_VIEW_ASSIGNED,
        ResourcePermission.WAR_ROOM_VIEW,
        ResourcePermission.SENSORY_WEBCAM_VIEW,
        ResourcePermission.SENSORY_MIC,
        ResourcePermission.HARDWARE_SMART_HOME,
        ResourcePermission.HARDWARE_VEHICLES,
    },
    SystemRole.SECRETARY: { # Segretaria
        ResourcePermission.PROJECTS_CREATE,
        ResourcePermission.PROJECTS_VIEW_ASSIGNED,
        ResourcePermission.PROJECTS_EDIT,
        ResourcePermission.WAR_ROOM_VIEW,
        ResourcePermission.WAR_ROOM_POST,
        ResourcePermission.WAR_ROOM_ANALYTICS,
        ResourcePermission.SENSORY_WEBCAM_HUD,
        ResourcePermission.SENSORY_MIC,
    },
    SystemRole.CHAUFFEUR: { # Autista
        ResourcePermission.SENSORY_MIC,
        ResourcePermission.HARDWARE_VEHICLES,
    },
    SystemRole.HOUSEKEEPING: { # Personale Pulizie
        ResourcePermission.HARDWARE_SMART_HOME,
    },
    SystemRole.MAINTENANCE: { # Manutenzione / Giardino
        ResourcePermission.HARDWARE_SMART_HOME,
    },
    SystemRole.GUEST: { # Ospite
        ResourcePermission.SENSORY_MIC,
    },
}
