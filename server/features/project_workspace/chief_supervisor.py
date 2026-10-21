import hashlib
import time
from typing import Dict, List, Any, Optional
from server.features.project_workspace.project_models import (
    ProjectStateExtended,
    WarRoomMessage,
    WarRoomMessageType,
)

class ChiefSupervisor:
    """
    Il Capo Agente (Chief Orchestrator & Anti-Loop Watchdog).
    Monitora costantemente lo stato dei progetti, valuta l'avanzamento reale,
    individua pattern di loop ripetitivi o stalli e genera analisi e schemi.
    """
    _instance = None

    def __new__(cls) -> "ChiefSupervisor":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._recent_actions: Dict[str, List[Dict[str, Any]]] = {}
        return cls._instance

    def calculate_progress(self, project: ProjectStateExtended) -> float:
        """
        Calcola la percentuale di completamento reale in base al peso delle milestone.
        """
        if not project.milestones:
            return 0.0
        
        total_weight = sum(m.weight for m in project.milestones)
        if total_weight <= 0:
            return 0.0

        current_progress = sum(m.progress * m.weight for m in project.milestones)
        pct = round((current_progress / total_weight) * 100.0, 1)
        project.completion_percentage = min(100.0, max(0.0, pct))
        return project.completion_percentage

    def inspect_and_guard_loop(
        self,
        project: ProjectStateExtended,
        agent_id: str,
        proposed_action_or_text: str,
    ) -> Optional[str]:
        """
        Watchdog Anti-Loop euristico:
        Controlla se l'agente sta reiterando la stessa azione/proposta o se
        esiste un ping-pong loop con altri agenti.
        Ritorna una stringa di intervento correttivo se rileva un loop, altrimenti None.
        """
        proj_id = project.project_id
        if proj_id not in self._recent_actions:
            self._recent_actions[proj_id] = []

        history = self._recent_actions[proj_id]

        # Calcola un hash del contenuto semantico per comparazione rapida
        normalized_str = proposed_action_or_text.strip().lower()
        content_hash = hashlib.md5(normalized_str.encode("utf-8")).hexdigest()

        # Registra azione corrente
        now = time.time()
        history.append({
            "agent_id": agent_id,
            "hash": content_hash,
            "preview": normalized_str[:120],
            "timestamp": now,
        })

        # Mantieni solo ultime 15 azioni per progetto
        if len(history) > 15:
            history.pop(0)

        # Regola 1: Lo stesso agente propone lo stesso hash 3 volte consecutive
        same_agent_repeats = [
            h for h in history[-4:]
            if h["agent_id"] == agent_id and h["hash"] == content_hash
        ]
        if len(same_agent_repeats) >= 3:
            project.loop_warnings_count += 1
            directive = (
                f"[INTERVENTO CAPO AGENTE]: Rilevato loop di ripetizione su '{agent_id}'. "
                f"Azione bloccata. Cambio forzato di approccio strategico o richiesta chiarimento utente."
            )
            self._inject_war_room_alert(project, directive)
            return directive

        # Regola 2: Ping-pong loop (due agenti si alternano con output identici/simili per 4 scambi)
        if len(history) >= 4:
            last_4 = history[-4:]
            agents_sequence = [h["agent_id"] for h in last_4]
            if (
                agents_sequence[0] == agents_sequence[2]
                and agents_sequence[1] == agents_sequence[3]
                and agents_sequence[0] != agents_sequence[1]
            ):
                # Pattern A -> B -> A -> B rilevato
                hashes = {h["hash"] for h in last_4}
                if len(hashes) <= 2:
                    project.loop_warnings_count += 1
                    directive = (
                        f"[INTERVENTO CAPO AGENTE]: Ping-Pong loop intercettato tra '{agents_sequence[0]}' "
                        f"e '{agents_sequence[1]}'. Congelamento del sotto-task e riesame delle precondizioni."
                    )
                    self._inject_war_room_alert(project, directive)
                    return directive


        return None

    def _inject_war_room_alert(self, project: ProjectStateExtended, alert_text: str) -> None:
        alert_msg = WarRoomMessage(
            sender_id="chief_supervisor",
            sender_name="Capo Agente (Chief)",
            sender_role="Chief Overseer",
            message_type=WarRoomMessageType.ALERT,
            content=alert_text,
            metadata={"priority": "high", "anti_loop_trigger": True},
        )
        project.war_room_feed.append(alert_msg)

    def request_agent_recruitment(
        self,
        project: ProjectStateExtended,
        requester_agent_id: str,
        target_agent_id: str,
        justification: str,
    ) -> Dict[str, Any]:
        """
        Un agente chiede al Capo Agente di convocare e aggiungere un nuovo specialista al team.
        Il Capo Agente valuta, autorizza e aggiorna la War Room e i componenti.
        """
        from server.core.agent_registry.forge import agent_forge
        spec = agent_forge.get_agent(target_agent_id)
        target_name = spec.name if spec else target_agent_id

        if target_agent_id in project.assigned_agents:
            return {
                "status": "already_assigned",
                "message": f"L'agente '{target_name}' fa già parte del team attivo.",
            }

        project.assigned_agents.append(target_agent_id)

        recruitment_msg = WarRoomMessage(
            sender_id="chief_supervisor",
            sender_name="Capo Agente (Chief)",
            sender_role="Chief Overseer",
            message_type=WarRoomMessageType.ALERT,
            content=(
                f"[CONVOCAZIONE AUTORIZZATA]: L'agente '{requester_agent_id}' ha richiesto il supporto "
                f"di '{target_name}' (Motivo: '{justification}'). Il Capo Agente ha convalidato "
                f"la richiesta e aggiunto lo specialista al team di progetto."
            ),
            metadata={
                "action": "agent_recruited",
                "requester": requester_agent_id,
                "recruited_agent": target_agent_id,
                "justification": justification,
            },
        )
        project.war_room_feed.append(recruitment_msg)
        return {
            "status": "approved",
            "recruited_agent": target_agent_id,
            "recruited_name": target_name,
            "message": recruitment_msg.content,
        }


    def generate_war_room_analytics(self, project: ProjectStateExtended) -> Dict[str, Any]:
        """
        Genera analisi visiva avanzata, diagramma Mermaid dei flussi e statistiche prestazionali.
        """
        # Genera diagramma di flusso Mermaid
        mermaid_lines = ["graph TD", f"    Start([Avvio Progetto: {project.name[:20]}]) --> Chief[Capo Agente Superiore]"]
        
        for m in project.milestones:
            m_label = f"{m.title} ({int(m.progress * 100)}%)"
            clean_id = m.milestone_id
            mermaid_lines.append(f'    Chief --> M_{clean_id}["{m_label}"]')
            if m.assigned_agent_id:
                mermaid_lines.append(f'    M_{clean_id} --> Ag_{clean_id}["Agente: {m.assigned_agent_id}"]')

        mermaid_graph = "\n".join(mermaid_lines)

        # Statistiche feed War Room
        total_messages = len(project.war_room_feed)
        thoughts_count = sum(1 for m in project.war_room_feed if m.message_type == WarRoomMessageType.THOUGHT)
        actions_count = sum(1 for m in project.war_room_feed if m.message_type == WarRoomMessageType.ACTION)
        deliverables_count = sum(1 for m in project.war_room_feed if m.message_type == WarRoomMessageType.DELIVERABLE)
        alerts_count = sum(1 for m in project.war_room_feed if m.message_type == WarRoomMessageType.ALERT)

        return {
            "project_id": project.project_id,
            "project_name": project.name,
            "completion_percentage": project.completion_percentage,
            "status": project.status,
            "autonomous_247": project.autonomous_247,
            "loop_warnings_interventions": project.loop_warnings_count,
            "mermaid_flowchart": mermaid_graph,
            "feed_metrics": {
                "total_messages": total_messages,
                "thoughts": thoughts_count,
                "actions": actions_count,
                "deliverables": deliverables_count,
                "alerts": alerts_count,
            },
            "milestones_summary": [
                {
                    "id": m.milestone_id,
                    "title": m.title,
                    "status": m.status.value,
                    "progress_pct": round(m.progress * 100, 1),
                    "agent": m.assigned_agent_id,
                }
                for m in project.milestones
            ],
        }

chief_supervisor = ChiefSupervisor()
