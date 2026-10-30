import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from config import STATE_DIR
from state import store

log = logging.getLogger("nuxiva.vision.nightly")
FACES = Path(os.environ.get("NUXIVA_FACES_DIR", str(STATE_DIR / "faces")))

# Nightly run scheduled between 03:00 and 04:00 AM
NIGHTLY_HOUR = 3
NIGHTLY_MINUTE = 30


def optimize_person(slug: str) -> dict:
    from features.vision.gallery import FACES as GFACES, quality_percent
    from features.people.people import slugify
    base = GFACES if GFACES.exists() else FACES
    d = base / slugify(slug)
    if not d.is_dir():
        return {"slug": slug, "status": "skipped", "reason": "directory_missing"}

    emb_file = d / "embeddings.npy"
    photos_dir = d / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    samples_count = 0
    ir_count = 0
    stats = None

    if emb_file.is_file():
        try:
            sys_path = Path(__file__).resolve().parents[1] / "biometrics"
            import sys
            if str(sys_path) not in sys.path:
                sys.path.append(str(sys_path))
            import embeddings as emb
            import sealed_rows

            rows = sealed_rows.load(emb_file)
            if rows is not None and len(rows) > 0:
                cleaned = emb.unit_rows(rows)
                c = emb.centroid(cleaned)
                sims = cleaned @ c
                # Outlier rejection: prune samples that diverge strongly from centroid
                kept = cleaned[sims >= 0.28] if len(cleaned) >= 6 else cleaned
                if len(kept) < 2:
                    kept = cleaned
                # Compact and limit to best 40 samples
                kept = emb.prune(kept, 40)
                sealed_rows.save(emb_file, kept)
                samples_count = len(kept)
                stats = emb.intra_stats(kept)
        except Exception as exc:
            log.warning("Errore ottimizzazione embeddings per %s: %s", slug, exc)

    # Read and update meta
    meta_path = d / "meta.json"
    meta = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
    ir_count = meta.get("samples_ir", 0)
    samples_count = samples_count or meta.get("samples", 1)

    pct = quality_percent(samples_count, ir_count, stats)
    meta["samples"] = samples_count
    meta["quality_pct"] = pct
    meta["optimized_at"] = time.time()
    try:
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass

    return {
        "slug": slug,
        "status": "optimized",
        "samples": samples_count,
        "quality_pct": pct,
        "photos_count": len(list(photos_dir.glob("*.jpg"))),
    }


def optimize_all() -> dict:
    from features.people import people
    from features.vision.gallery import FACES as GFACES
    base = GFACES if GFACES.exists() else FACES
    all_p = people.all_profiles(light=True)
    slugs = {p["slug"] for p in all_p}
    if base.is_dir():
        for d in base.iterdir():
            if d.is_dir():
                slugs.add(d.name)

    results = []
    for slug in sorted(slugs):
        try:
            res = optimize_person(slug)
            results.append(res)
        except Exception as exc:
            log.error("Ottimizzazione biometrica fallita per %s: %s", slug, exc)
            results.append({"slug": slug, "status": "error", "error": str(exc)})



    summary = {
        "timestamp": time.time(),
        "date": datetime.now().isoformat(),
        "total_people": len(results),
        "results": results,
    }
    store.event("INFO", f"Ottimizzazione notturna biometrica completata per {len(results)} persone", "vision")
    return summary


def consolidate_synapses() -> dict:
    from features.brain.assignments import load_synaptic_weights, save_synaptic_weights
    weights = load_synaptic_weights()
    if not weights:
        return {"status": "skipped", "count": 0}
    consolidated = {}
    for key, weight in weights.items():
        decayed = max(0.1, min(2.5, 0.5 + (weight - 0.5) * 0.95))
        consolidated[key] = round(decayed, 3)
    save_synaptic_weights(consolidated)
    store.event("INFO", f"Ciclo REM notturno: consolidamento di {len(consolidated)} connessioni sinaptiche completato", "brain")
    return {"status": "ok", "count": len(consolidated)}


class NightlyVisionOptimizer:
    def __init__(self) -> None:
        self.last_run_day = ""

    async def loop(self) -> None:
        log.info("Avviato guardiano notturno per ottimizzazione biometrica persone (finestra %02d:%02d)",
                 NIGHTLY_HOUR, NIGHTLY_MINUTE)
        while True:
            try:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")
                if now.hour == NIGHTLY_HOUR and now.minute >= NIGHTLY_MINUTE and self.last_run_day != today_str:
                    log.info("Esecuzione programmata: ottimizzazione notturna del riconoscimento facciale...")
                    await asyncio.to_thread(optimize_all)
                    await asyncio.to_thread(consolidate_synapses)
                    self.last_run_day = today_str
            except Exception as exc:
                log.warning("Eccezione durante il ciclo notturno di ottimizzazione: %s", exc)
            await asyncio.sleep(60)


optimizer = NightlyVisionOptimizer()
loop = optimizer.loop
