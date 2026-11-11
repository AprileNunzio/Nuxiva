import os
import json
import time
import sqlite3
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
from server.config.env import settings
from server.core.context_graph.node_schema import (
    KnowledgeNode,
    KnowledgeEdge,
    NodeType,
    RelationType,
    GraphSnapshot,
)
from server.shared.errors.domain_errors import EntityNotFoundException

try:
    from nuxiva_native import RustContextGraph  # type: ignore
except ImportError:
    RustContextGraph = None  # type: ignore

logger = logging.getLogger("nuxiva.graph_client")


class GraphClient:

    def __init__(self, db_path: str = "") -> None:
        if not db_path:
            db_path = os.path.join(settings.DATA_DIR, "db", "knowledge_graph.sqlite")
        self._db_path = db_path
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._create_tables()
        self._native_graph = RustContextGraph() if RustContextGraph is not None else None
        self._bootstrap_default_topology()
        self._hydrate_native_graph()

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                label TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                properties TEXT DEFAULT '{}',
                PRIMARY KEY (source_id, target_id, relation_type),
                FOREIGN KEY (source_id) REFERENCES nodes(id),
                FOREIGN KEY (target_id) REFERENCES nodes(id)
            );
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);
        """)
        self._conn.commit()
        logger.info("Knowledge graph database initialized at %s", self._db_path)

    def _bootstrap_default_topology(self) -> None:
        now = time.time()
        row = self._conn.execute("SELECT id FROM nodes WHERE id = ?", ("nuxiva_core",)).fetchone()
        if not row:
            self._conn.execute(
                "INSERT INTO nodes (id, node_type, label, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("nuxiva_core", NodeType.AGENT.value if hasattr(NodeType.AGENT, "value") else str(NodeType.AGENT),
                 "Nuxiva Orchestrator",
                 json.dumps({"version": "5.7.8", "status": "ONLINE"}),
                 now, now),
            )
            self._conn.commit()

    def _hydrate_native_graph(self) -> None:
        if self._native_graph is None:
            return
        try:
            nodes = self._conn.execute("SELECT id, node_type, label, properties FROM nodes").fetchall()
            for nid, ntype, label, props in nodes:
                self._native_graph.upsert_node(nid, ntype, label, props, 1.0)
            edges = self._conn.execute("SELECT source_id, target_id, relation_type, weight, properties FROM edges").fetchall()
            for sid, tid, rel, weight, props in edges:
                self._native_graph.upsert_edge(sid, tid, rel, float(weight), props)
        except Exception as exc:
            logger.warning("Errore durante idratazione native context graph: %s", exc)

    def upsert_node(
        self,
        node_id: str,
        node_type: NodeType,
        label: str,
        properties: Dict[str, Any],
    ) -> KnowledgeNode:
        now = time.time()
        type_str = node_type.value if hasattr(node_type, "value") else str(node_type)
        props_json = json.dumps(properties, default=str)

        with self._lock:
            existing = self._conn.execute(
                "SELECT properties, created_at FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()

            if existing:
                old_props = json.loads(existing[0])
                merged = {**old_props, **properties}
                merged_json = json.dumps(merged, default=str)
                self._conn.execute(
                    "UPDATE nodes SET node_type=?, label=?, properties=?, updated_at=? WHERE id=?",
                    (type_str, label, merged_json, now, node_id),
                )
                created_at = existing[1]
                final_props = merged
            else:
                self._conn.execute(
                    "INSERT INTO nodes (id, node_type, label, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (node_id, type_str, label, props_json, now, now),
                )
                created_at = now
                final_props = properties

            self._conn.commit()

        if self._native_graph is not None:
            self._native_graph.upsert_node(node_id, type_str, label, json.dumps(final_props, default=str), 1.0)

        return KnowledgeNode(
            id=node_id,
            node_type=node_type,
            label=label,
            properties=final_props,
            created_at=created_at,
            updated_at=now,
        )

    def get_node(self, node_id: str) -> KnowledgeNode:
        row = self._conn.execute(
            "SELECT id, node_type, label, properties, created_at, updated_at FROM nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
        if not row:
            raise EntityNotFoundException("KnowledgeNode", node_id)
        return self._row_to_node(row)

    def link_nodes(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEdge:
        src = self._conn.execute("SELECT id FROM nodes WHERE id = ?", (source_id,)).fetchone()
        tgt = self._conn.execute("SELECT id FROM nodes WHERE id = ?", (target_id,)).fetchone()
        if not src:
            raise EntityNotFoundException("KnowledgeNode", source_id)
        if not tgt:
            raise EntityNotFoundException("KnowledgeNode", target_id)

        rel_str = relation_type.value if hasattr(relation_type, "value") else str(relation_type)
        props_json = json.dumps(properties or {}, default=str)

        with self._lock:
            self._conn.execute(
                """INSERT INTO edges (source_id, target_id, relation_type, weight, properties)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(source_id, target_id, relation_type)
                   DO UPDATE SET weight=excluded.weight, properties=excluded.properties""",
                (source_id, target_id, rel_str, weight, props_json),
            )
            self._conn.commit()

        if self._native_graph is not None:
            self._native_graph.upsert_edge(source_id, target_id, rel_str, float(weight), props_json)

        return KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            properties=properties or {},
        )

    def shortest_path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        if self._native_graph is not None:
            return self._native_graph.shortest_path(from_id, to_id)
        visited = set()
        queue: List[Tuple[str, List[str]]] = [(from_id, [from_id])]
        while queue:
            curr, path = queue.pop(0)
            if curr == to_id:
                return path
            if curr in visited:
                continue
            visited.add(curr)
            rows = self._conn.execute("SELECT target_id FROM edges WHERE source_id = ?", (curr,)).fetchall()
            for r in rows:
                if r[0] not in visited:
                    queue.append((r[0], path + [r[0]]))
        return None

    def k_hop_subgraph(
        self,
        start_id: str,
        max_hops: int = 2,
        max_nodes: int = 50,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if self._native_graph is not None:
            nodes_tup, edges_tup = self._native_graph.k_hop_subgraph(start_id, max_hops, max_nodes)
            nodes = [{"id": n[0], "node_type": n[1], "label": n[2], "properties": json.loads(n[3]), "weight": n[4]} for n in nodes_tup]
            edges = [{"source_id": e[0], "target_id": e[1], "relation_type": e[2], "weight": e[3], "properties": json.loads(e[4])} for e in edges_tup]
            return nodes, edges
        node = self._conn.execute("SELECT id, node_type, label, properties FROM nodes WHERE id = ?", (start_id,)).fetchone()
        if not node:
            return [], []
        nodes = [{"id": node[0], "node_type": node[1], "label": node[2], "properties": json.loads(node[3]), "weight": 1.0}]
        edges: List[Dict[str, Any]] = []
        return nodes, edges

    def pagerank(self, damping: float = 0.85, iterations: int = 20) -> List[Tuple[str, float]]:
        if self._native_graph is not None:
            return self._native_graph.pagerank(damping, iterations)
        return []

    def export_snapshot(self) -> GraphSnapshot:
        node_rows = self._conn.execute(
            "SELECT id, node_type, label, properties, created_at, updated_at FROM nodes"
        ).fetchall()
        edge_rows = self._conn.execute(
            "SELECT source_id, target_id, relation_type, weight, properties FROM edges"
        ).fetchall()

        nodes = [self._row_to_node(r) for r in node_rows]
        edges = [self._row_to_edge(r) for r in edge_rows]
        return GraphSnapshot(nodes=nodes, edges=edges)

    def node_count(self) -> int:
        if self._native_graph is not None:
            return self._native_graph.node_count()
        row = self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()
        return row[0] if row else 0

    def edge_count(self) -> int:
        if self._native_graph is not None:
            return self._native_graph.edge_count()
        row = self._conn.execute("SELECT COUNT(*) FROM edges").fetchone()
        return row[0] if row else 0

    @staticmethod
    def _row_to_node(row: tuple) -> KnowledgeNode:
        node_id, node_type_str, label, props_json, created_at, updated_at = row
        try:
            node_type = NodeType(node_type_str)
        except (ValueError, KeyError):
            node_type = NodeType.CONCEPT
        return KnowledgeNode(
            id=node_id,
            node_type=node_type,
            label=label,
            properties=json.loads(props_json),
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def _row_to_edge(row: tuple) -> KnowledgeEdge:
        source_id, target_id, rel_type_str, weight, props_json = row
        try:
            relation_type = RelationType(rel_type_str)
        except (ValueError, KeyError):
            relation_type = RelationType.DEPENDS_ON
        return KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            properties=json.loads(props_json),
        )

    def close(self) -> None:
        self._conn.close()


graph_client = GraphClient()
