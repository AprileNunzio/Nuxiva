from dataclasses import asdict, dataclass, field
import json
import time
from typing import Any

from config import STATE_DIR

KNOWLEDGE_FILE = STATE_DIR / "enterprise_knowledge_graph.json"


@dataclass
class KnowledgeNode:
    id: str
    kind: str
    label: str
    description: str
    domain: str = "general"
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeEdge:
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    context: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EnterpriseKnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, KnowledgeNode] = {}
        self.edges: list[KnowledgeEdge] = []
        self._load()

    def _load(self) -> None:
        if not KNOWLEDGE_FILE.exists():
            return
        try:
            data = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
            for n in data.get("nodes", []):
                node = KnowledgeNode(**n)
                self.nodes[node.id] = node
            for e in data.get("edges", []):
                self.edges.append(KnowledgeEdge(**e))
        except Exception:
            self.nodes = {}
            self.edges = []

    def save(self) -> None:
        payload = {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "updated_at": time.time(),
        }
        tmp = KNOWLEDGE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(KNOWLEDGE_FILE)

    def record_learning(self, mission_id: str, domain: str, lesson: str, decision: str = "") -> None:
        clean_lesson = lesson.strip()
        if not clean_lesson:
            return
        node_id = f"lesson_{abs(hash(clean_lesson)) % 10000000}"
        if node_id not in self.nodes:
            self.nodes[node_id] = KnowledgeNode(
                id=node_id,
                kind="lesson_learned",
                label=clean_lesson[:80],
                description=clean_lesson,
                domain=domain,
                metadata={"mission_id": mission_id},
            )
        if decision.strip():
            dec_id = f"decision_{abs(hash(decision)) % 10000000}"
            if dec_id not in self.nodes:
                self.nodes[dec_id] = KnowledgeNode(
                    id=dec_id,
                    kind="architectural_decision",
                    label=decision[:80],
                    description=decision,
                    domain=domain,
                    metadata={"mission_id": mission_id},
                )
            self.edges.append(KnowledgeEdge(source_id=dec_id, target_id=node_id, relation="prevents_error"))
        self.save()

    def query_context(self, domain: str, limit: int = 5) -> list[str]:
        matching = [
            n.description for n in self.nodes.values()
            if n.domain.lower() == domain.lower() or domain.lower() in ("general", "all")
        ]
        return matching[-limit:]


knowledge_graph = EnterpriseKnowledgeGraph()
