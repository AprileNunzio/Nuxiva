import re
from pathlib import Path
from typing import Optional

WEB_DIR = Path(__file__).resolve().parent
LAYOUT_FILE = WEB_DIR / "layout" / "master.html"
TARGET_INDEX = WEB_DIR / "index.html"
INCLUDE_PATTERN = re.compile(r"<!--\s*@include\s+([a-zA-Z0-9_\-\./]+)\s*-->")

_cached_html: Optional[str] = None
_last_mtime: float = 0.0

def _get_latest_mtime() -> float:
    """Restituisce il timestamp di modifica più recente tra il master layout e tutti i componenti."""
    mtimes = [LAYOUT_FILE.stat().st_mtime] if LAYOUT_FILE.exists() else [0.0]
    for sub in WEB_DIR.glob("features/**/*.html"):
        try:
            mtimes.append(sub.stat().st_mtime)
        except OSError:
            pass
    return max(mtimes) if mtimes else 0.0

def compose_html(use_cache: bool = True) -> str:
    """
    Assembla dinamicamente l'interfaccia Enterprise componendo
    il layout master con i singoli moduli indipendenti (deck e modali).
    Zero dipendenze esterne, massime performance con cache in memoria.
    """
    global _cached_html, _last_mtime

    latest_mtime = _get_latest_mtime()
    if use_cache and _cached_html is not None and latest_mtime <= _last_mtime:
        return _cached_html

    if not LAYOUT_FILE.exists():
        if TARGET_INDEX.exists():
            return TARGET_INDEX.read_text(encoding="utf-8")
        return "<html><body><h1>Nuxiva Layout Not Found</h1></body></html>"

    master_content = LAYOUT_FILE.read_text(encoding="utf-8")

    def _replace_include(match: re.Match) -> str:
        rel_path = match.group(1).strip()
        comp_file = WEB_DIR / rel_path
        if comp_file.exists():
            return comp_file.read_text(encoding="utf-8")
        return f"<!-- Componente non trovato: {rel_path} -->"

    composed = INCLUDE_PATTERN.sub(_replace_include, master_content)
    _cached_html = composed
    _last_mtime = latest_mtime
    return composed

def build_index_html() -> str:
    """Compila il file server/web/index.html sincronizzato su disco."""
    html = compose_html(use_cache=False)
    TARGET_INDEX.write_text(html, encoding="utf-8")
    return html

if __name__ == "__main__":
    out = build_index_html()
    print(f"✅ index.html generato con successo dai componenti modulari ({len(out.splitlines())} righe).")
