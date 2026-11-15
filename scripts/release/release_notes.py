import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ci"))

import changelog_valid

LANGS = changelog_valid.LANGS
SCHEMA = 1
MAX_NOTES = 200
BODY_LIMIT = 60000
SKIP_PREFIX = "release-"
PLATFORMS = {"Nuxiva.apk": "android", "Nuxiva_Setup.exe": "windows"}
HEADINGS = {
    "it": ("Novità", "Bugfix", "Download", "Note aggiuntive omesse per lunghezza"),
    "en": ("New features", "Bug fixes", "Downloads", "Further notes omitted for length"),
    "fr": ("Nouveautés", "Corrections", "Téléchargements", "Notes supplémentaires omises pour la longueur"),
    "es": ("Novedades", "Correcciones", "Descargas", "Notas adicionales omitidas por longitud"),
}
TITLES = {"it": "Nuxiva {v} per Android e Windows", "en": "Nuxiva {v} for Android and Windows",
          "fr": "Nuxiva {v} pour Android et Windows", "es": "Nuxiva {v} para Android y Windows"}


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def note_paths(previous_tag: str, commit: str) -> list[str]:
    if previous_tag and subprocess.run(["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", f"refs/tags/{previous_tag}^{{commit}}"], capture_output=True).returncode == 0:
        out = git("diff", "--name-only", "--diff-filter=A", f"{previous_tag}..{commit}", "--", "changelog/*.json")
        paths = out.split()
    else:
        paths = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "changelog").glob("*.json"))
    names = [p for p in paths if not Path(p).name[15:].startswith(SKIP_PREFIX)]
    return sorted(names)[-MAX_NOTES:]


def load_notes(paths: list[str]) -> list[dict]:
    notes = []
    for relative in paths:
        path = ROOT / relative
        if not path.is_file() or changelog_valid.check(path):
            continue
        data = json.loads(path.read_bytes())
        notes.append({"id": path.stem, "date": data["date"], "title": data["title"],
                      "features": data.get("features", []), "fixes": data.get("fixes", [])})
    return notes


def flatten(notes: list[dict], section: str) -> list[dict]:
    seen: set[str] = set()
    items = []
    for note in notes:
        for text in note[section]:
            fingerprint = json.dumps(text, sort_keys=True, ensure_ascii=False)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            items.append({"source": note["id"], "date": note["date"], "text": text})
    return items


def gradle_field(pattern: str) -> str:
    text = (ROOT / "client_apk/app/build.gradle.kts").read_text(encoding="utf-8")
    match = re.search(pattern, text)
    if not match:
        raise LookupError(pattern)
    return match.group(1)


def windows_version() -> str:
    text = (ROOT / "client_satellite/windows_assistant/settings/paths.py").read_text(encoding="utf-8")
    return re.search(r'(?m)^VERSION = "([0-9.]+)"', text).group(1)


def describe(path: Path) -> dict:
    data = path.read_bytes()
    return {"name": path.name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(), "platform": PLATFORMS.get(path.name, "support")}


def build(version: str, tag: str, commit: str, previous_tag: str, assets: list[Path], notes: list[dict]) -> dict:
    features, fixes = flatten(notes, "features"), flatten(notes, "fixes")
    return {
        "schema": SCHEMA,
        "version": version,
        "tag": tag,
        "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": commit,
        "previous": {"tag": previous_tag, "version": re.sub(r"^(?:assistant-|android-)?v", "", previous_tag)} if previous_tag else None,
        "title": {lang: TITLES[lang].format(v=version) for lang in LANGS},
        "summary": {"notes": len(notes), "features": len(features), "fixes": len(fixes)},
        "components": {
            "server": {"version": (ROOT / "VERSION").read_text(encoding="utf-8").strip()},
            "android": {"version": gradle_field(r'versionName = "([0-9.]+)"'), "version_code": int(gradle_field(r"versionCode = (\d+)")), "file": "Nuxiva.apk"},
            "windows": {"version": windows_version(), "file": "Nuxiva_Setup.exe"},
        },
        "assets": [describe(path) for path in sorted(assets, key=lambda p: p.name)],
        "features": features,
        "fixes": fixes,
        "notes": notes,
    }


def markdown(release: dict, lang: str, repository: str) -> str:
    news, fixes, downloads, omitted = HEADINGS[lang]
    lines = [f"## {release['title'][lang]}", ""]
    for heading, section in ((news, "features"), (fixes, "fixes")):
        items = release[section]
        if not items:
            continue
        lines += [f"### {heading}", ""]
        lines += [f"- {item['text'][lang]}" for item in items]
        lines.append("")
    lines += [f"### {downloads}", ""]
    for asset in release["assets"]:
        url = f"https://github.com/{repository}/releases/download/{release['tag']}/{asset['name']}"
        lines.append(f"- [{asset['name']}]({url}) · {asset['size']} B · SHA-256 `{asset['sha256']}`")
    return "\n".join(lines)


def body(release: dict, repository: str) -> str:
    parts = [markdown(release, lang, repository) for lang in LANGS]
    text = "\n\n---\n\n".join(parts)
    if len(text) > BODY_LIMIT:
        text = text[:BODY_LIMIT].rsplit("\n", 1)[0] + f"\n\n_{HEADINGS['en'][3]}._"
    return text + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="release_notes")
    parser.add_argument("--version", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--previous-tag", default="")
    parser.add_argument("--assets", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--repository", default="AprileNunzio/Nuxiva")
    args = parser.parse_args(argv)
    assets = [Path(p) for p in args.assets]
    missing = [str(p) for p in assets if not p.is_file()]
    if missing:
        print(f"asset mancanti / missing assets: {missing}", file=sys.stderr)
        return 2
    notes = load_notes(note_paths(args.previous_tag, args.commit))
    release = build(args.version, args.tag, args.commit, args.previous_tag, assets, notes)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "release.json").write_text(json.dumps(release, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "release_body.md").write_text(body(release, args.repository), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
