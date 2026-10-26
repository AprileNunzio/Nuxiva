import hashlib
import re
from features.autonomous_worker.domain.models import Mission, Specialist
from features.autonomous_worker.domain.sanitizer import sanitize_text
from features.team.scanner import scanner


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return cleaned[:32] or "specialist"


class SpecialistForge:
    def __init__(self) -> None:
        self.scanner = scanner

    def assemble_team(self, mission: Mission) -> list[Specialist]:
        available = self.scanner.scan()
        team_map: dict[str, Specialist] = {}

        for phase in mission.phases:
            for task in phase.tasks:
                role_req = task.specialist_role or "Specialista di Dominio"
                role_key = _slugify(role_req)

                if role_key not in team_map:
                    matched = self._find_existing_agent(available, role_req)
                    if matched:
                        spec = Specialist(
                            id=matched.id,
                            role=matched.name,
                            title=matched.description[:80],
                            mission_role=role_req,
                            capabilities=list(matched.capabilities),
                            tools=[t.get("name", "") for t in matched.tools if isinstance(t, dict)],
                            is_dynamic=False,
                        )
                    else:
                        digest = hashlib.sha256(f"{mission.id}:{role_req}".encode("utf-8")).hexdigest()[:6]
                        spec_id = f"exp_{role_key}_{digest}"
                        spec = Specialist(
                            id=spec_id,
                            role=sanitize_text(role_req, 60),
                            title=f"Esperto di {sanitize_text(role_req, 50)}",
                            mission_role=role_req,
                            capabilities=[role_key, mission.domain],
                            tools=["devstudio", "filesystem", "system"],
                            guidelines=f"Rispettare gli standard massimi mondiali per {role_req}.",
                            is_dynamic=True,
                        )
                    team_map[role_key] = spec

                task.specialist_id = team_map[role_key].id
                task.specialist_role = team_map[role_key].role

        mission.specialists = list(team_map.values())
        return mission.specialists

    def _find_existing_agent(self, available: dict, role_req: str):
        target = role_req.lower()
        for agent in available.values():
            if target in agent.name.lower() or target in agent.description.lower():
                return agent
            for cap in agent.capabilities:
                if target in cap.lower():
                    return agent
        return None


forge = SpecialistForge()
