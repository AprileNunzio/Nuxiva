import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SolutionEntry:
    solution_id: str
    domain: str
    intent_keywords: List[str]
    title: str
    summary: str
    template_payload: Dict[str, Any]
    usage_count: int = 1
    success_count: int = 1
    quality_score: float = 1.0
    tokens_saved_estimate: int = 2500
    optimization_generation: int = 1
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        return round(self.success_count / max(1, self.usage_count), 3)

    def record_usage(self, success: bool = True, execution_time_ms: float = 0.0) -> None:
        self.usage_count += 1
        if success:
            self.success_count += 1
            self.quality_score = min(2.0, self.quality_score + 0.05)
        else:
            self.quality_score = max(0.1, self.quality_score - 0.1)
        self.tokens_saved_estimate += 2500
        self.last_used_at = time.time()


class InternalSolutionBank:
    def __init__(self, storage_path: Optional[str] = None) -> None:
        if storage_path:
            self.storage_file = Path(storage_path)
        else:
            home = os.environ.get("HOME", "/home/antigravity")
            self.storage_file = Path(home) / ".gemini" / "nuxiva_solution_bank.json"
        self.solutions: Dict[str, SolutionEntry] = {}
        self.load_from_disk()

    def _tokenize(self, text: str) -> set[str]:
        return {w.lower() for w in re.findall(r"\w{3,}", text.lower())}

    def compute_similarity(self, query_tokens: set[str], entry_keywords: List[str]) -> float:
        if not query_tokens or not entry_keywords:
            return 0.0
        kw_set = {k.lower() for k in entry_keywords}
        intersection = query_tokens.intersection(kw_set)
        union = query_tokens.union(kw_set)
        jaccard = len(intersection) / max(1, len(union))
        keyword_overlap = len(intersection) / max(1, len(kw_set))
        return round((jaccard * 0.4) + (keyword_overlap * 0.6), 3)

    def find_best_solution(
        self,
        query: str,
        domain: Optional[str] = None,
        min_confidence: float = 0.40
    ) -> Optional[Tuple[SolutionEntry, float]]:
        q_tokens = self._tokenize(query)
        if not q_tokens or not self.solutions:
            return None

        candidates = []
        for entry in self.solutions.values():
            if domain and entry.domain != domain and entry.domain != "universal":
                continue
            sim = self.compute_similarity(q_tokens, entry.intent_keywords)
            weighted_score = sim * min(1.5, entry.quality_score)
            if sim >= min_confidence:
                candidates.append((entry, weighted_score))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0]

    def register_solution(
        self,
        domain: str,
        title: str,
        keywords: List[str],
        summary: str,
        template_payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> SolutionEntry:
        clean_title = title.strip()
        slug = re.sub(r"\W+", "_", clean_title.lower()).strip("_")[:40]
        solution_id = f"sol_{domain}_{slug}"

        if solution_id in self.solutions:
            existing = self.solutions[solution_id]
            existing.template_payload = template_payload
            existing.optimization_generation += 1
            existing.record_usage(success=True)
            self.save_to_disk()
            return existing

        entry = SolutionEntry(
            solution_id=solution_id,
            domain=domain,
            intent_keywords=[k.lower().strip() for k in keywords if len(k) >= 2],
            title=clean_title,
            summary=summary.strip(),
            template_payload=template_payload,
            metadata=metadata or {},
        )
        self.solutions[solution_id] = entry
        self.save_to_disk()
        return entry

    def refine_solution(
        self,
        solution_id: str,
        optimized_payload: Dict[str, Any],
        improvement_note: str = ""
    ) -> Optional[SolutionEntry]:
        entry = self.solutions.get(solution_id)
        if not entry:
            return None
        entry.template_payload.update(optimized_payload)
        entry.optimization_generation += 1
        entry.quality_score = min(2.5, entry.quality_score + 0.1)
        if improvement_note:
            notes = entry.metadata.setdefault("refinement_history", [])
            notes.append({"generation": entry.optimization_generation, "note": improvement_note, "time": time.time()})
        self.save_to_disk()
        return entry

    def get_stats(self) -> Dict[str, Any]:
        total_sol = len(self.solutions)
        total_tokens_saved = sum(e.tokens_saved_estimate for e in self.solutions.values())
        total_uses = sum(e.usage_count for e in self.solutions.values())
        avg_score = round(sum(e.quality_score for e in self.solutions.values()) / max(1, total_sol), 2)
        by_domain = {}
        for e in self.solutions.values():
            by_domain[e.domain] = by_domain.get(e.domain, 0) + 1

        return {
            "total_solutions_indexed": total_sol,
            "total_tokens_saved": total_tokens_saved,
            "total_executions_accelerated": total_uses,
            "average_quality_score": avg_score,
            "solutions_by_domain": by_domain,
            "storage_file": str(self.storage_file),
        }

    def save_to_disk(self) -> None:
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            serializable = {k: asdict(v) for k, v in self.solutions.items()}
            self.storage_file.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def load_from_disk(self) -> None:
        if not self.storage_file.exists():
            self._seed_default_foundations()
            return
        try:
            raw = self.storage_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            for k, val in data.items():
                self.solutions[k] = SolutionEntry(**val)
        except Exception:
            self._seed_default_foundations()

    def _seed_default_foundations(self) -> None:
        self.register_solution(
            domain="object_3d_cad",
            title="Parametric Enclosure Box with Screw Posts",
            keywords=["scatola", "cover", "box", "enclosure", "3d", "stl", "openscad", "stampa", "supporto"],
            summary="Guscio protettivo parametrico OpenSCAD con torrette per viti e tolleranze ad incastro",
            template_payload={
                "code": (
                    "$fn = 40;\n"
                    "module enclosure(w=60, l=90, h=30, t=2) {\n"
                    "    difference() {\n"
                    "        cube([w, l, h], center=true);\n"
                    "        translate([0, 0, t]) cube([w-2*t, l-2*t, h], center=true);\n"
                    "    }\n"
                    "}\n"
                    "enclosure();\n"
                ),
                "extension": ".scad",
                "default_infill": 25,
            }
        )
        self.register_solution(
            domain="laser_cnc_vector",
            title="Living Hinge Flexible Wood Cut Template",
            keywords=["laser", "taglio", "legno", "compensato", "cerniera", "living hinge", "flessibile", "dxf", "svg"],
            summary="Tracciato laser parametrico per cerniere flessibili nel legno con kerf compensato",
            template_payload={
                "stroke_cut": "#FF0000",
                "stroke_engrave": "#0000FF",
                "kerf_mm": 0.14,
                "svg_template": '<svg viewBox="0 0 100 100"><rect x="5" y="5" width="90" height="90" stroke="#FF0000"/></svg>',
            }
        )
        self.register_solution(
            domain="software_web",
            title="Clean Hexagonal React and FastApi Scaffold",
            keywords=["sito", "web", "landing", "react", "fastapi", "frontend", "backend", "fullstack", "mcp"],
            summary="Scaffold modulare esagonale con divisione domain, adapter, controller e server MCP",
            template_payload={
                "frontend": "tsx_tailwind",
                "backend": "fastapi_clean_arch",
                "mcp_enabled": True,
            }
        )


solution_bank = InternalSolutionBank()
