import json
import os
import re
import threading
import time
from pathlib import Path

from config import STATE_DIR
from features.particles import morphogenesis
from features.stage import native

CATALOG_ROOT = Path(os.environ.get("NUXIVA_VISUAL_CATALOG_DIR", str(STATE_DIR / "visual_catalog")))


def _sanitize_segment(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", str(raw or "").strip()).strip("_")
    return cleaned[:48] if cleaned else "oggetto"


def map_engine_folder(engine: str) -> str:
    norm = str(engine or "").strip().lower()
    if norm in ("diorama", "scene_3d"):
        return "diorama"
    if norm in ("gaussian_splat", "neural_radiance", "depth_parallax", "animazioni_3d"):
        return "animazioni_3d"
    return "particelle"


def _classify_domain_and_slug(concept: str) -> tuple[str, str, str, str]:
    lower = str(concept or "").lower()
    if any(k in lower for k in ("medusa", "rhizostoma", "cnidar", "jellyfish")):
        return ("animali", "mare", "Rhizostoma_pulmo", "Rhizostoma pulmo (Cnidaria · Scyphozoa)")
    if any(k in lower for k in ("polp", "octopus", "calamar", "squalo", "delfin", "balen", "pesce")):
        return ("animali", "mare", _sanitize_segment(concept), "Fauna Marina Pelagica / Bentonica")
    if any(k in lower for k in ("aquila", "leone", "lupo", "orso", "cane", "gatto", "cavallo")):
        return ("animali", "terra", _sanitize_segment(concept), "Vertebrata · Fauna Terrestre")
    if any(k in lower for k in ("motore", "v8", "turbina", "pistone", "cilindr")):
        slug = "motore_v8" if ("v8" in lower or "motore" in lower) else _sanitize_segment(concept)
        return ("auto", "motori", slug, "Propulsore Termodinamico Endotermico V8")
    if any(k in lower for k in ("auto", "telaio", "freno", "cambio", "sospension")):
        return ("auto", "meccanica", _sanitize_segment(concept), "Ingegneria dell'Autoveicolo")
    if any(k in lower for k in ("castel", "fortezza", "rocca")):
        slug = "Castel_dell_Ovo" if "ovo" in lower else _sanitize_segment(concept)
        return ("castelli", "monumenti", slug, "Architettura Fortificata Storica")
    if any(k in lower for k in ("cervell", "cuore", "polmon", "neurone", "dna", "cellula")):
        return ("anatomia", "corpo_umano", _sanitize_segment(concept), "Anatomia e Fisiologia Umana")
    if any(k in lower for k in ("pianeta", "saturno", "galassia", "stella", "buco nero", "sistema solare")):
        return ("astronomia", "cosmo", _sanitize_segment(concept), "Astrofisica e Meccanica Celeste")
    if any(k in lower for k in ("atom", "molecol", "cristall", "quarzo")):
        return ("scienza", "materia", _sanitize_segment(concept), "Fisica della Materia e Cristallografia")
    return ("enciclopedia", "modelli", _sanitize_segment(concept), "Tassonomia Strutturale Multidimensionale")


def classify_academic_entry(
    concept: str,
    engine: str = "particles",
    digest: str = "",
    hotspots: list[dict] | None = None,
) -> dict:
    if native.lib is not None and hasattr(native.lib, "visual_catalog_classify"):
        try:
            raw = native.lib.visual_catalog_classify(str(concept or ""), str(engine or "particles"), str(digest or ""))
            parsed = json.loads(raw)
            if hotspots is not None:
                parsed["lecture"]["hotspots"] = hotspots
            return parsed
        except Exception:
            pass

    engine_folder = map_engine_folder(engine)
    domain, subdomain, slug, binomial = _classify_domain_and_slug(concept)
    relative_dir = f"{engine_folder}/{domain}/{subdomain}/{slug}"
    spots = hotspots if hotspots is not None else morphogenesis.extract_hotspots(concept, morphogenesis.synthesize_spec(concept))
    display_title = str(concept or "").strip() or slug.replace("_", " ")

    return {
        "engine_folder": engine_folder,
        "domain": domain,
        "subdomain": subdomain,
        "slug": slug,
        "relative_dir": relative_dir,
        "concept": str(concept or "").strip().lower(),
        "digest": str(digest or ""),
        "lecture": {
            "title": display_title,
            "binomial_or_code": binomial,
            "taxonomy_path": relative_dir,
            "abstract_summary": (
                f"Analisi accademica tridimensionale di «{display_title}» ({binomial}). "
                "Ruota il modello con il cursore, usa lo zoom per ispezionare la micro-architettura "
                "e seleziona ciascun nodo anatomico o meccanico per la spiegazione cattedratica dettagliata."
            ),
            "structural_notes": f"Archiviato in {relative_dir} · Motore: {engine_folder} · Punti di ispezione attivi: {len(spots)}",
            "hotspots": spots,
        },
    }


class VisualCatalog:
    def __init__(self, root: Path = CATALOG_ROOT) -> None:
        self.root = root
        self.lock = threading.RLock()
        self.by_concept: dict[str, dict] = {}
        self.by_path: dict[str, str] = {}
        self.loaded = False

    def _ensure(self) -> None:
        if self.loaded:
            return
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        idx_file = self.root / "catalog_index.json"
        if idx_file.exists():
            try:
                data = json.loads(idx_file.read_text(encoding="utf-8"))
                for key, item in (data.get("entries") or {}).items():
                    if isinstance(item, dict) and "relative_dir" in item:
                        self.by_concept[key] = item
                        self.by_path[item["relative_dir"]] = key
            except (OSError, ValueError):
                pass
        self.loaded = True

    def _persist_index(self) -> None:
        idx_file = self.root / "catalog_index.json"
        tmp = idx_file.with_suffix(".tmp")
        payload = json.dumps({"entries": self.by_concept, "updated": time.time()}, ensure_ascii=False, indent=1)
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(idx_file)

    def record(
        self,
        concept: str,
        engine: str = "particles",
        digest: str = "",
        spec: dict | None = None,
        blob: bytes | None = None,
        hotspots: list[dict] | None = None,
    ) -> dict:
        entry = classify_academic_entry(concept, engine, digest, hotspots)
        key = entry["concept"]
        rel_dir = entry["relative_dir"]
        with self.lock:
            self._ensure()
            target_dir = self.root / rel_dir
            target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            manifest = {
                **entry,
                "spec": spec,
                "updated_at": time.time(),
            }
            (target_dir / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
            (target_dir / "lecture.json").write_text(
                json.dumps(entry["lecture"], ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
            if blob is not None:
                (target_dir / f"{entry['slug']}.nxpc").write_bytes(blob)
            self.by_concept[key] = entry
            self.by_path[rel_dir] = key
            self._persist_index()
        return entry

    def lookup(self, concept_or_path: str) -> dict | None:
        query = str(concept_or_path or "").strip()
        if not query:
            return None
        with self.lock:
            self._ensure()
            if query in self.by_path:
                return self.by_concept.get(self.by_path[query])
            return self.by_concept.get(query.lower())

    def tree(self) -> list[dict]:
        with self.lock:
            self._ensure()
            return list(self.by_concept.values())


catalog = VisualCatalog()
