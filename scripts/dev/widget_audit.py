import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIZARD = ROOT / "installer_wizard"
SHARED = WIZARD / "widgets"
AGENTI = WIZARD / "agenti"
LANGS = ("it", "en", "fr", "es")
JARGON = re.compile(r"\b(?:cpu|gpu|vram|ram|ssh|rag|vlan|dns|dhcp|usb|ci/cd|cicd|git|diff|docker|tcp|udp|ip|mac|ssid|bssid|api|token|tokens|latenza|ms|mb|gb|tb|hz|khz|bpm|rssi|fps|ttl|uuid|json|glb|gltf|stl|obj|ply|fbx|mesh|brute-?force|pipeline|container|firewall|kanban|vcard|contesto|payload)\b", re.I)
ACRONYM = re.compile(r"\b[A-Z]{2,6}\b")
HARDCODED = re.compile(r"""(?:>|`|")([A-ZÀ-Ü][a-zà-ü]{2,}[^<>"`$\n]{4,40})(?:<|`|")""")


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def locate() -> list[dict]:
    found = []
    for manifest in sorted(SHARED.glob("*/widget.json")):
        found.append({"path": manifest, "owner": "", "category": ""})
    for manifest in sorted(AGENTI.glob("*/*/widget/*/widget.json")):
        agent_dir = manifest.parents[2]
        found.append({"path": manifest, "owner": agent_dir.name, "category": agent_dir.parent.name})
    return found


def texts(folder: Path, lang: str) -> list[str]:
    data = load(folder / "language" / f"{lang}.json").get("dictionary", {})
    return [v for v in data.values() if isinstance(v, str)]


def score(folder: Path) -> dict:
    words = texts(folder, "it")
    joined = " ".join(words)
    jargon = len(JARGON.findall(joined))
    acronyms = len(ACRONYM.findall(joined))
    digits = sum(1 for w in words if re.search(r"\d", w))
    long_texts = sum(1 for w in words if len(w) > 70)
    script = (folder / "widget.js").read_text(encoding="utf-8") if (folder / "widget.js").exists() else ""
    hardcoded = len(HARDCODED.findall(script))
    mono = script.count("wk-mono") + script.count("wk-kv")
    total = jargon * 3 + acronyms * 2 + digits + long_texts * 2 + hardcoded * 2 + min(mono, 6)
    return {"jargon": jargon, "acronyms": acronyms, "digits": digits, "long": long_texts, "hardcoded": hardcoded, "mono": mono,
            "score": total, "keys": len(words), "js_lines": script.count("\n") + 1}


def rate(value: int) -> str:
    return "alto" if value >= 14 else "medio" if value >= 6 else "basso"


def audit() -> list[dict]:
    rows = []
    for item in locate():
        folder = item["path"].parent
        manifest = load(item["path"])
        simple = manifest.get("simple") if isinstance(manifest.get("simple"), dict) else {}
        rows.append({
            "id": manifest.get("id", folder.name), "name": manifest.get("name", ""), "owner": item["owner"],
            "category": item["category"], "frameless": manifest.get("chrome", True) is False,
            "simple": bool(simple), "langs": [l for l in LANGS if (folder / "language" / f"{l}.json").exists()],
            **score(folder),
        })
    return rows


def render(rows: list[dict]) -> str:
    shared = [r for r in rows if not r["owner"]]
    owned = [r for r in rows if r["owner"]]
    out = ["# Audit dei widget della pagina 80", "",
           f"Widget totali: {len(rows)}. Nella cartella generica: {len(shared)}. Dentro un agente: {len(owned)}.",
           f"Con livello semplice dichiarato: {sum(1 for r in rows if r['simple'])}.", "",
           "| Widget | Agente | Tecnicismo | Punti | Sigle | Numeri | Testi fissi | Lingue | Livello semplice |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (-r["score"], r["id"])):
        where = f"{r['category']}/{r['owner']}" if r["owner"] else "generico (fuori dagli agenti)"
        out.append(f"| {r['id']} | {where} | {rate(r['score'])} | {r['score']} | {r['acronyms'] + r['jargon']} | {r['digits']} | {r['hardcoded']} | {len(r['langs'])}/4 | {'sì' if r['simple'] else 'no'} |")
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rows = audit()
    text = json.dumps(rows, ensure_ascii=False, indent=1) if args.json else render(rows)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
