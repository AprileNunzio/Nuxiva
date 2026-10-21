import re

from server.core.agent_registry.agent_spec import AgentCapabilitySpec

_MAX_SLUG = 48


def specialist_id(specialty: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", specialty.lower()).strip("_")[:_MAX_SLUG]
    return f"expert_{slug or 'generic'}"


def build_specialist_spec(specialty: str, justification: str) -> AgentCapabilitySpec:
    return AgentCapabilitySpec(
        id=specialist_id(specialty),
        name=f"Specialist: {specialty}",
        role_category="engineering",
        avatar_icon="graduation-cap",
        description=f"Esperto convocato dal Capo Agente per: {specialty}. Motivo: {justification}",
        system_prompt=(
            f"Sei un esperto di livello superiore in {specialty}. Rispondi solo nel tuo ambito, "
            "indica con chiarezza ciò che non puoi verificare dalla telecamera o dai dati e "
            "chiedi al Capo Agente un ulteriore specialista se emerge un sotto-dominio fuori dalla tua competenza."
        ),
        tools=["domain_knowledge_lookup"],
        widgets=[],
    )
