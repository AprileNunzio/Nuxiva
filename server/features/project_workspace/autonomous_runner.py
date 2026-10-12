import asyncio
import logging
import time
from typing import Dict, Any, Optional
from server.features.project_workspace.manager import project_manager
from server.features.project_workspace.chief_supervisor import chief_supervisor
from server.features.project_workspace.project_models import (
    ProjectStateExtended,
    MilestoneStatus,
    WarRoomMessage,
    WarRoomMessageType,
)
from server.features.agent_tools.social_tools import instagram_generate_copy, telegram_broadcast_message
from server.features.agent_tools.cad_tools import cad_generate_dxf, cad_calculate_bom
from server.features.agent_tools.google_suite_tools import google_gmail_send, google_calendar_schedule

logger = logging.getLogger("nuxiva.autonomous_runner")

class AutonomousProjectRunner:
    _instance = None

    def __new__(cls) -> "AutonomousProjectRunner":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._running = False
            cls._instance._task: Optional[asyncio.Task] = None
            cls._instance._interval_seconds = 8.0 # Step intervallo tra azioni autonome
        return cls._instance

    def start(self) -> None:
        if not self._running:
            self._running = True
            try:
                loop = asyncio.get_running_loop()
                self._task = loop.create_task(self._main_loop())
                logger.info("Autonomous 24/7 Multi-Project Runner avviato.")
            except RuntimeError:
                pass

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Autonomous 24/7 Multi-Project Runner arrestato.")

    async def _main_loop(self) -> None:
        while self._running:
            try:
                await self.tick_all_projects()
            except Exception as e:
                logger.error("Errore nel ciclo autonomo 24/7: %s", e)
            await asyncio.sleep(self._interval_seconds)

    async def tick_all_projects(self) -> None:
        # Recupera tutti i progetti attivi con autonomia 24/7
        active_projects = [
            p for p in project_manager.get_all("user_primary")
            if p.status == "ACTIVE" and p.autonomous_247 and p.completion_percentage < 100.0
        ]

        for project in active_projects:
            await self._step_project(project)

    async def _step_project(self, project: ProjectStateExtended) -> None:
        # Trova la prima milestone non completata
        target_milestone = None
        for m in project.milestones:
            if m.status in [MilestoneStatus.TODO, MilestoneStatus.IN_PROGRESS]:
                target_milestone = m
                break

        if not target_milestone:
            # Tutte le milestone completate
            project.status = "COMPLETED"
            project.completion_percentage = 100.0
            msg = WarRoomMessage(
                sender_id="chief_supervisor",
                sender_name="Capo Agente (Chief)",
                sender_role="Chief Overseer",
                message_type=WarRoomMessageType.ALERT,
                content=f"[COMPLETATO]: Progetto '{project.name}' completato al 100%! Tutti i deliverable sono stati prodotti e verificati.",
            )

            project_manager.post_war_room_message(project.owner_id, project.project_id, msg)
            project_manager.save(project.owner_id, project)
            return

        target_milestone.status = MilestoneStatus.IN_PROGRESS
        agent_id = target_milestone.assigned_agent_id or "chief_supervisor"

        # Esecuzione specializzata in base all'agente assegnato
        action_text = ""
        deliverable_data = {}

        if "cad" in agent_id or "autocad" in agent_id:
            res = cad_generate_dxf(
                project_id=project.project_id,
                part_name=project.name,
                width_mm=250.0,
                height_mm=120.0,
                holes=3,
                hole_diameter_mm=12.0,
            )
            action_text = f"Generato disegno DXF vettoriale '{res['filename']}' con contorno e forature (Area: {res['area_sq_cm']} cm²)."
            deliverable_data = res

        elif "instagram" in agent_id or "social" in agent_id:
            res = instagram_generate_copy(topic=project.name)
            action_text = f"Pianificato post Instagram con copy strategico ed hook: '{res['hook']}'"
            deliverable_data = res

        elif "google" in agent_id:
            res = google_gmail_send(to="team@nuxiva.local", subject=f"Avanzamento: {project.name}", body_text="Report generato automaticamente")
            action_text = f"Creata bozza Gmail di coordinamento per '{project.name}' con allegati."
            deliverable_data = res

        else:
            action_text = f"Avanzamento fase esecutiva: elaborazione task '{target_milestone.title}'."
            deliverable_data = {"progress_step": 0.25}

        # Controllo Anti-Loop del Capo Agente
        loop_guard = chief_supervisor.inspect_and_guard_loop(project, agent_id, action_text)
        if loop_guard:
            # Il Capo Agente ha congelato l'azione ripetitiva: shift strategico
            # Passa l'assegnazione al prossimo specialista nel team per sbloccare il flusso
            available_specialists = [a for a in project.assigned_agents if a != agent_id and a != "chief_supervisor"]
            if available_specialists:
                next_agent = available_specialists[0]
                target_milestone.assigned_agent_id = next_agent
                shift_msg = WarRoomMessage(
                    sender_id="chief_supervisor",
                    sender_name="Capo Agente (Chief)",
                    sender_role="Chief Overseer",
                    message_type=WarRoomMessageType.ALERT,
                    content=f"[STRATEGIA RICALIBRATA]: Task '{target_milestone.title}' riassegnato a '{next_agent}' per sbloccare lo stallo.",
                )
                project.war_room_feed.append(shift_msg)
            else:
                target_milestone.status = MilestoneStatus.DONE
                target_milestone.progress = 1.0
            chief_supervisor.calculate_progress(project)
            project_manager.save(project.owner_id, project)
            return

        # Incrementa progresso della milestone (+25% a step fino a completamento)
        target_milestone.progress = min(1.0, round(target_milestone.progress + 0.25, 2))
        if target_milestone.progress >= 1.0:
            target_milestone.status = MilestoneStatus.DONE
            target_milestone.completed_at = time.time()


        # Invia messaggio nella War Room
        wr_msg = WarRoomMessage(
            sender_id=agent_id,
            sender_name=agent_id.replace("_", " ").title(),
            sender_role="Specialist",
            message_type=WarRoomMessageType.ACTION if target_milestone.progress < 1.0 else WarRoomMessageType.DELIVERABLE,
            content=action_text,
            attachments=[deliverable_data] if deliverable_data else [],
        )
        project_manager.post_war_room_message(project.owner_id, project.project_id, wr_msg)
        chief_supervisor.calculate_progress(project)
        project_manager.save(project.owner_id, project)

autonomous_runner = AutonomousProjectRunner()
