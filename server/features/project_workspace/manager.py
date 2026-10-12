import os
import uuid
import time
import glob
import json
import asyncio
from typing import Dict, Optional, List
from server.config.env import settings
from server.features.project_workspace.project_models import (
    ProjectStateExtended,
    ProjectMilestone,
    MilestoneStatus,
    WarRoomMessage,
    WarRoomMessageType,
)
from server.features.project_workspace.chief_supervisor import chief_supervisor
from server.core.agent_registry.forge import agent_forge

class ProjectWorkspaceManager:
    _instance = None

    def __new__(cls) -> "ProjectWorkspaceManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._store_dir = os.path.join(settings.DATA_DIR, "projects")
            os.makedirs(cls._instance._store_dir, exist_ok=True)
            cls._instance._autonomous_tasks: Dict[str, asyncio.Task] = {}
        return cls._instance

    def _user_dir(self, user_id: str) -> str:
        uid = user_id or "default"
        d = os.path.join(self._store_dir, uid)
        os.makedirs(d, exist_ok=True)
        return d

    def get_all(self, user_id: str) -> List[ProjectStateExtended]:
        projects = []
        for path in glob.glob(os.path.join(self._user_dir(user_id), "*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Supporta sia schema legacy che esteso
                    if "war_room_feed" not in data:
                        data["war_room_feed"] = []
                    if "milestones" not in data:
                        data["milestones"] = []
                    if "assigned_agents" not in data:
                        data["assigned_agents"] = ["chief_supervisor", "project_director"]
                    if "completion_percentage" not in data:
                        data["completion_percentage"] = 0.0
                    if "autonomous_247" not in data:
                        data["autonomous_247"] = data.get("autonomous", False)
                    if "owner_id" not in data:
                        data["owner_id"] = user_id

                    projects.append(ProjectStateExtended(**data))
            except Exception:
                pass
        return sorted(projects, key=lambda x: x.updated_at, reverse=True)

    def get_by_id(self, user_id: str, project_id: str) -> Optional[ProjectStateExtended]:
        fpath = os.path.join(self._user_dir(user_id), f"{project_id}.json")
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return ProjectStateExtended(**data)
            except Exception:
                pass
        return None

    def get_active(self, user_id: str) -> Optional[ProjectStateExtended]:
        for p in self.get_all(user_id):
            if p.status == "ACTIVE":
                return p
        return None

    def save(self, user_id: str, state: ProjectStateExtended) -> None:
        state.updated_at = time.time()
        # Ricalcola percentuale con il Capo Agente
        chief_supervisor.calculate_progress(state)
        fpath = os.path.join(self._user_dir(user_id), f"{state.project_id}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(), f, indent=2)

    def auto_assign_agents(self, goal: str) -> List[str]:
        """
        Analizza la descrizione del progetto e seleziona automaticamente gli agenti ideali.
        Il Capo Agente e il Project Director sono sempre inclusi come spina dorsale.
        """
        lower = goal.lower()
        team = ["chief_supervisor", "project_director"]

        if any(w in lower for w in ["cad", "autocad", "disegno", "dxf", "dwg", "3d", "pianta", "architettura", "meccanica"]):
            team.append("autocad_designer")

        if any(w in lower for w in ["instagram", "post", "social", "reel", "carosello", "storia", "hashtag"]):
            team.append("instagram_agent")

        if any(w in lower for w in ["telegram", "canale", "bot", "broadcast", "gruppo"]):
            team.append("telegram_master")

        if any(w in lower for w in ["google", "gmail", "calendar", "drive", "docs", "sheets", "foglio", "posta"]):
            team.append("google_suite_agent")

        if any(w in lower for w in ["codice", "sviluppo", "sito", "app", "api", "database", "backend", "frontend", "programma"]):
            team.append("fullstack_coder")
            team.append("devops_engineer")

        if any(w in lower for w in ["casa", "domotica", "pulizie", "autista", "segretaria", "residenza", "famiglia", "maggiordomo"]):
            team.append("home_butler_agent")

        if any(w in lower for w in ["dati", "analisi", "statistiche", "grafici", "report", "kpi"]):
            team.append("data_analyst")

        # Rimuove duplicati preservando l'ordine
        return list(dict.fromkeys(team))

    def create_project(
        self,
        user_id: str,
        name: str,
        goal: str,
        autonomous_247: bool = False,
        visibility: str = "private",
        custom_agents: Optional[List[str]] = None,
    ) -> ProjectStateExtended:
        proj_id = uuid.uuid4().hex
        assigned = custom_agents if custom_agents else self.auto_assign_agents(goal)

        # Crea milestone iniziali predefinite
        milestones = [
            ProjectMilestone(
                title="Pianificazione Architetturale & Decomposizione",
                description="Analisi del brief e definizione roadmap esecutiva.",
                status=MilestoneStatus.IN_PROGRESS,
                progress=0.3,
                weight=1.0,
                assigned_agent_id="project_director",
            ),
            ProjectMilestone(
                title="Esecuzione Operativa dei Task",
                description="Sviluppo dei deliverable da parte degli agenti specializzati.",
                status=MilestoneStatus.TODO,
                progress=0.0,
                weight=3.0,
                assigned_agent_id=assigned[2] if len(assigned) > 2 else "chief_supervisor",
            ),
            ProjectMilestone(
                title="Revisione Qualità & Validazione Finale",
                description="Verifica deliverable, assenza bug e approvazione finale.",
                status=MilestoneStatus.TODO,
                progress=0.0,
                weight=1.0,
                assigned_agent_id="chief_supervisor",
            ),
        ]

        # Messaggio di benvenuto nella War Room
        welcome_msg = WarRoomMessage(
            sender_id="chief_supervisor",
            sender_name="Capo Agente (Chief)",
            sender_role="Chief Overseer",
            message_type=WarRoomMessageType.ALERT,
            content=(
                f"[WAR ROOM ATTIVA]: Progetto '{name}' inizializzato con successo. "
                f"Team assegnato: {', '.join(assigned)}. Modalità 24/7: {'Attiva' if autonomous_247 else 'Disattivata'}."
            ),
            metadata={"assigned_agents": assigned},
        )


        project = ProjectStateExtended(
            project_id=proj_id,
            name=name,
            goal=goal,
            status="ACTIVE",
            visibility=visibility,
            autonomous_247=autonomous_247,
            owner_id=user_id,
            assigned_agents=assigned,
            milestones=milestones,
            war_room_feed=[welcome_msg],
            created_at=time.time(),
            updated_at=time.time(),
        )

        self.save(user_id, project)
        self._notify_widget(project)
        return project

    def add_agent_to_project(self, user_id: str, project_id: str, agent_id: str) -> bool:
        project = self.get_by_id(user_id, project_id)
        if not project:
            return False
        if agent_id not in project.assigned_agents:
            project.assigned_agents.append(agent_id)
            # Notifica nella War Room
            spec = agent_forge.get_agent(agent_id)
            agent_name = spec.name if spec else agent_id
            msg = WarRoomMessage(
                sender_id="chief_supervisor",
                sender_name="Capo Agente (Chief)",
                sender_role="Chief Overseer",
                message_type=WarRoomMessageType.ALERT,
                content=f"🤝 Nuovo specialista aggiunto al team: '{agent_name}'.",
            )
            project.war_room_feed.append(msg)
            self.save(user_id, project)
            self._notify_widget(project)
            return True
        return False

    def remove_agent_from_project(self, user_id: str, project_id: str, agent_id: str) -> bool:
        if agent_id in ["chief_supervisor"]:
            return False # Il Capo Agente non può essere rimosso per garantire stabilità
        project = self.get_by_id(user_id, project_id)
        if not project or agent_id not in project.assigned_agents:
            return False

        project.assigned_agents.remove(agent_id)
        msg = WarRoomMessage(
            sender_id="chief_supervisor",
            sender_name="Capo Agente (Chief)",
            sender_role="Chief Overseer",
            message_type=WarRoomMessageType.ALERT,
            content=f"👋 Agente '{agent_id}' congedato dal progetto.",
        )
        project.war_room_feed.append(msg)
        self.save(user_id, project)
        self._notify_widget(project)
        return True

    def post_war_room_message(
        self,
        user_id: str,
        project_id: str,
        message: WarRoomMessage,
    ) -> WarRoomMessage:
        project = self.get_by_id(user_id, project_id)
        if not project:
            raise ValueError(f"Progetto {project_id} non trovato.")

        # Esegui controllo anti-loop da parte del Capo Agente
        loop_alert = chief_supervisor.inspect_and_guard_loop(
            project, message.sender_id, message.content
        )
        if loop_alert:
            alert_msg = WarRoomMessage(
                sender_id="chief_supervisor",
                sender_name="Capo Agente (Supervisor)",
                sender_role="Supervisor",
                message_type=WarRoomMessageType.ALERT,
                content=loop_alert,
            )
            project.war_room_feed.append(alert_msg)

        project.war_room_feed.append(message)
        self.save(user_id, project)
        self._notify_widget(project)
        return message

    def process_query(self, query: str, user_id: str) -> str:
        lower = query.lower()
        state = self.get_active(user_id)

        list_triggers = ["quali progetti", "lista progetti", "progetti aperti", "list projects"]
        if any(t in lower for t in list_triggers):
            open_projs = [p for p in self.get_all(user_id) if p.status in ["ACTIVE", "PENDING"]]
            self._notify_list(open_projs)
            return "System command: showing projects list."

        close_triggers = ["chiudi il progetto", "esci dal progetto", "termina il progetto", "close project"]
        for t in close_triggers:
            if t in lower:
                target = lower.split(t)[-1].strip()
                if target:
                    for p in self.get_all(user_id):
                        if target in p.name.lower() and p.status != "COMPLETED":
                            p.status = "COMPLETED"
                            self.save(user_id, p)
                            if state and p.project_id == state.project_id:
                                self._notify_widget(None)
                            return f"System command: project {p.name} completed."
                elif state:
                    state.status = "COMPLETED"
                    self.save(user_id, state)
                    self._notify_widget(None)
                    return "System command: current project completed."

        start_triggers = ["nuovo progetto", "crea un progetto", "lavoriamo a un progetto", "creami un sito web", "sviluppiamo", "creami un'app", "new project"]
        if any(t in lower for t in start_triggers):
            name = "Nuovo Progetto"
            if "sito web" in lower or "website" in lower: name = "Progetto Web"
            elif "cad" in lower or "disegno" in lower: name = "Progetto CAD & Struttura"
            elif "instagram" in lower or "social" in lower: name = "Campagna Social & Media"
            elif "telegram" in lower: name = "Canale Telegram Bot"

            auto = "autonomia" in lower or "notte" in lower or "background" in lower or "24h" in lower or "24 ore" in lower
            new_state = self.create_project(
                user_id=user_id,
                name=name,
                goal=query,
                autonomous_247=auto,
            )
            return f"[PROJECT_START: {name} (24/7:{auto}) Team:{len(new_state.assigned_agents)} agenti] {query}"

        if state and state.status == "ACTIVE":
            if "autonomia" in lower or "24h" in lower:
                state.autonomous_247 = True
            user_msg = WarRoomMessage(
                sender_id=user_id,
                sender_name="Operatore Umano",
                sender_role="Human Overseer",
                message_type=WarRoomMessageType.USER_INPUT,
                content=query,
            )
            self.post_war_room_message(user_id, state.project_id, user_msg)
            return f"[CONTESTO PROGETTO: {state.goal}] Richiesta: {query}"

        return query

    def add_response(self, user_id: str, response: str) -> None:
        state = self.get_active(user_id)
        if state and state.status == "ACTIVE":
            agent_msg = WarRoomMessage(
                sender_id="chief_supervisor",
                sender_name="Capo Agente (Chief)",
                sender_role="Chief Overseer",
                message_type=WarRoomMessageType.ACTION,
                content=response,
            )
            self.post_war_room_message(user_id, state.project_id, agent_msg)

    def _notify_widget(self, state: Optional[ProjectStateExtended]) -> None:
        try:
            from server.core.kernel.telemetry import NeuralTelemetry
            payload = state.model_dump() if state else {"status": "CLOSED"}
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(NeuralTelemetry.emit("project_mode", "system", payload))
            except RuntimeError:
                pass
        except Exception:
            pass

    def _notify_list(self, projects: List[ProjectStateExtended]) -> None:
        try:
            from server.core.kernel.telemetry import NeuralTelemetry
            payload = {"is_list": True, "projects": [p.model_dump() for p in projects]}
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(NeuralTelemetry.emit("project_mode", "system", payload))
            except RuntimeError:
                pass
        except Exception:
            pass


project_manager = ProjectWorkspaceManager()
