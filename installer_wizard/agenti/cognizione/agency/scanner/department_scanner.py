import json
import re
from pathlib import Path

from agenti.agency.scanner.recursive_scanner import recursive_scanner

DEFAULT_CATALOG_DIR = Path(__file__).resolve().parents[1] / "departments_catalog"


def _clean_str(value: str, limit: int = 400) -> str:
    return str(value or "").strip()[:limit]


def scan_departments(extra_dirs: list[Path] | None = None) -> dict[str, dict]:
    dirs = [DEFAULT_CATALOG_DIR]
    if extra_dirs:
        dirs.extend(extra_dirs)
    departments: dict[str, dict] = {}
    for d in dirs:
        if not d.exists() or not d.is_dir():
            continue
        for file_path, data, category in recursive_scanner.scan_json_files(d):
            dep_id = _clean_str(data.get("id"), 40).lower()
            if not dep_id:
                continue
            rec = {
                "id": dep_id,
                "name": _clean_str(data.get("name"), 120) or f"Specialist · {dep_id.title()}",
                "department": _clean_str(data.get("department"), 120) or "Dipartimento Speciale",
                "category": category,
                "prompt": _clean_str(data.get("prompt"), 2000),
                "skills": [str(s)[:60] for s in data.get("skills", []) if isinstance(s, (str, int))],
                "capabilities": [str(c)[:60] for c in data.get("capabilities", []) if isinstance(c, (str, int))],
                "widgets": [w for w in data.get("widgets", []) if isinstance(w, dict)],
                "path": str(file_path),
            }
            departments[dep_id] = rec
            if category and category != "general":
                departments[f"{category}.{dep_id}"] = rec
    return departments


DOMAIN_SYNONYMS = {
    "customer": ("chiam", "chiamami", "telefon", "fonia", "voce", "call", "voice", "whatsapp", "ordine", "assistenza", "supporto", "ticket", "notifica", "telegram", "sms", "luci", "camera", "casa"),
    "sales": ("email", "mail", "pec", "preventiv", "acquist", "vendit", "cliente", "lead", "commerciale"),
    "finance": ("fattur", "fattura", "sdi", "xml", "iva", "bonific", "pagament", "fisco", "bilancio", "contabil"),
    "field_tech": ("nvr", "telecam", "cctv", "hikvision", "router", "ping", "porta", "guast", "diagnostic", "hardware", "server", "telemetri", "rete"),
    "marketing": ("campagn", "funnel", "adv", "marketing", "copywriting", "growth", "seo"),
    "social_media": ("social", "instagram", "tiktok", "reel", "post", "editoriale", "community", "facebook"),
    "influencer_ops": ("influencer", "creator", "sponsor", "media kit", "talent", "collaboraz", "brand"),
    "web_studio": ("sito", "landing", "web", "pizzeria", "ecommerce", "negozio", "portfolio", "pagina"),
    "medical": ("medicin", "medic", "farmac", "clinica", "sintom", "paziente", "dottor", "terapia", "diagnosi", "paracetamolo", "ibuprofene", "cefalea"),
    "family_home": ("spesa", "famigli", "pulizie", "manutenzion", "casa", "bollett", "rifiut"),
    "people_butler": ("persona", "persone", "abitudin", "gust", "preferenz", "passion", "hobby", "maggiordom", "profilo", "adatt"),
    "education_tutor": ("compit", "studio", "scuola", "matematica", "fisica", "latino", "tutor", "lezione", "storia", "geografia", "scienze"),
    "culinary_chef": ("cucina", "ricett", "cucinare", "piatto", "cena", "pranzo", "ingrediente", "dispensa", "frigo", "forno", "cuoc", "pasta"),
    "storyteller_kids": ("favol", "fiaba", "racconto", "nanna", "storiella", "fiabe", "favola"),
    "integrations": ("mcp", "google", "slack", "shopify", "stripe", "calendario", "integraz", "webhook", "api"),
    "html5_expert": ("html", "html5", "canvas", "pwa", "webcomponent", "webaudio", "markup", "accessib"),
    "tsx_expert": ("tsx", "typescript", "react", "next", "vite", "jsx", "signal", "zustand", "frontend_reattiv"),
    "rust_expert": ("rust", "cargo", "tokio", "wasm", "webassembly", "axum", "microserviz", "concorrenz"),
    "php_expert": ("php", "php8", "composer", "symfony", "laravel", "swoole", "roadrunner", "esagonal", "psr"),
    "security_crypto_expert": ("sicurezza", "crypto", "crittografia", "zerotrust", "cifratura", "token", "audit", "pentest", "chacha", "aes", "ed25519", "argon2"),
    "video_editor": ("montagg", "video", "clip", "editing", "sottotitol", "render", "timeline", "tagli", "audio_sync", "sincronizz", "reel", "short"),
    "audio_producer": ("smb", "traccia", "audio", "sound", "suono", "musica", "jingle", "soundtrack", "voce_sintetic", "tts", "voce_ai", "waveform"),
}


def find_specialist(query: str, extra_dirs: list[Path] | None = None) -> dict | None:
    deps = scan_departments(extra_dirs)
    lower_query = query.lower()
    tokens = [t.lower() for t in re.split(r"\W+", lower_query) if len(t) >= 3]
    if not tokens:
        return None
    for dep_id, prof in deps.items():
        if dep_id in tokens:
            return prof
    best_dep = None
    best_score = 0
    for dep_id, syns in DOMAIN_SYNONYMS.items():
        if dep_id not in deps:
            continue
        score = 0
        for s in syns:
            for t in tokens:
                if t == s:
                    score += 3
                elif len(s) >= 4 and t.startswith(s):
                    score += 2
        if score > best_score:
            best_score = score
            best_dep = deps[dep_id]
    if best_dep and best_score > 0:
        return best_dep
    for dep_id, prof in deps.items():
        search_space = f"{dep_id} {prof['name']} {prof['department']} {' '.join(prof['skills'])} {' '.join(prof['capabilities'])}".lower()
        search_tokens = set(re.split(r"\W+", search_space))
        if any(tok in search_tokens for tok in tokens):
            return prof
    return None


def forge_department(
    domain: str,
    name: str = "",
    dept_name: str = "",
    prompt: str = "",
    skills: list[str] | None = None,
    widgets: list[dict] | None = None,
    capabilities: list[str] | None = None,
    target_dir: Path | None = None,
    category: str = "general",
) -> dict:
    dest_dir = target_dir or DEFAULT_CATALOG_DIR
    cat_slug = recursive_scanner.clean_slug(category) or "general"
    cat_dir = dest_dir / cat_slug
    cat_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9_-]", "_", domain.lower().strip())[:40] or "specialist"
    title = slug.replace("_", " ").title()
    record = {
        "id": slug,
        "name": name or f"Specialist · {title}",
        "department": dept_name or f"Dipartimento {title}",
        "category": cat_slug,
        "prompt": prompt or f"Sei lo Specialista responsabile del dominio {title} per NunzioTech Agency.",
        "skills": skills or [f"{slug}-core", "domain-execution", "compliance", "verification"],
        "capabilities": capabilities or [f"{slug}_task", "data_synthesis"],
        "widgets": widgets or [{"id": f"{slug}_dashboard", "type": "domain_card", "title": f"Monitor {title}"}],
    }
    file_path = cat_dir / f"{slug}.json"
    file_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    record["path"] = str(file_path)
    return record


def list_categories(extra_dirs: list[Path] | None = None) -> list[str]:
    deps = scan_departments(extra_dirs)
    cats = {d.get("category", "general") for d in deps.values() if isinstance(d, dict)}
    return sorted(cats)


def get_departments_by_category(category: str, extra_dirs: list[Path] | None = None) -> list[dict]:
    deps = scan_departments(extra_dirs)
    target = category.lower().strip()
    results = []
    seen = set()
    for d in deps.values():
        if isinstance(d, dict) and d.get("category", "").lower() == target:
            dep_id = d.get("id")
            if dep_id and dep_id not in seen:
                seen.add(dep_id)
                results.append(d)
    return results
