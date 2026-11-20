import time
from dataclasses import asdict, dataclass, field


@dataclass
class EpisodicNode:
    node_id: str
    kind: str
    label: str
    person_slug: str
    timestamp: float
    metadata: dict = field(default_factory=dict)


@dataclass
class CausalEdge:
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    decay_rate: float = 0.05
    created_at: float = field(default_factory=time.time)


class CausalEpisodicMemoryGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, EpisodicNode] = {}
        self.edges: list[CausalEdge] = []

    def record_episode(
        self,
        person_slug: str,
        event_name: str,
        emotion_state: str,
        context_payload: dict,
        consequence_action: str | None = None,
    ) -> dict:
        now = time.time()
        slug = str(person_slug).strip().lower()

        event_node_id = f"event_{slug}_{int(now * 1000)}"
        event_node = EpisodicNode(
            node_id=event_node_id,
            kind="event",
            label=event_name,
            person_slug=slug,
            timestamp=now,
            metadata=context_payload,
        )
        self.nodes[event_node_id] = event_node

        emotion_node_id = f"emotion_{slug}_{int(now * 1000)}"
        emotion_node = EpisodicNode(
            node_id=emotion_node_id,
            kind="emotion",
            label=emotion_state,
            person_slug=slug,
            timestamp=now,
        )
        self.nodes[emotion_node_id] = emotion_node

        self.edges.append(CausalEdge(
            source_id=event_node_id,
            target_id=emotion_node_id,
            relation="induced_emotion",
            weight=1.0,
        ))

        if consequence_action:
            action_node_id = f"action_{slug}_{int(now * 1000)}"
            action_node = EpisodicNode(
                node_id=action_node_id,
                kind="behavioral_adaptation",
                label=consequence_action,
                person_slug=slug,
                timestamp=now,
            )
            self.nodes[action_node_id] = action_node

            self.edges.append(CausalEdge(
                source_id=emotion_node_id,
                target_id=action_node_id,
                relation="led_to_preference",
                weight=1.2,
            ))

        return {
            "status": "episode_consolidated",
            "event_id": event_node_id,
            "person_slug": slug,
            "causal_links_count": len(self.edges),
        }

    def predict_preference(self, person_slug: str, current_emotion_or_event: str) -> dict:
        slug = str(person_slug).strip().lower()
        query = current_emotion_or_event.lower()

        matched_consequences = []
        for edge in self.edges:
            src = self.nodes.get(edge.source_id)
            tgt = self.nodes.get(edge.target_id)
            if src and tgt and src.person_slug == slug:
                if query in src.label.lower() and tgt.kind == "behavioral_adaptation":
                    matched_consequences.append((tgt.label, edge.weight))

        if matched_consequences:
            top_prediction = max(matched_consequences, key=lambda x: x[1])[0]
            confidence = 0.94
        else:
            top_prediction = "richiesta_discrezione_e_supporto_neutro"
            confidence = 0.65

        return {
            "person_slug": slug,
            "trigger_query": current_emotion_or_event,
            "predicted_preference": top_prediction,
            "causal_confidence": confidence,
            "recommended_butler_posture": f"Adatta l'ambiente e i widget a: {top_prediction}",
        }


episodic_graph = CausalEpisodicMemoryGraph()
