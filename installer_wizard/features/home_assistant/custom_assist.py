import glob
import logging
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from config import read_env
from features.home_assistant.nlu.text import norm

log = logging.getLogger("nuxiva.ha_custom_assist")


def get_config_dir() -> Path:
    env = read_env()
    raw = env.get("HOME_ASSISTANT_CONFIG_DIR", "/config").strip()
    p = Path(raw)
    if p.exists():
        return p
    # Fallback to local test paths if /config is not accessible on Windows
    alt = Path(__file__).resolve().parent / "custom_config"
    return alt if alt.exists() else p


def _clean_sentence_pattern(pattern: str) -> str:
    cleaned = re.sub(r"\[.*?\]", "", pattern)  # remove optional groups [optional]
    cleaned = re.sub(r"\{.*?\}", "", cleaned)  # remove slots {slot}
    cleaned = re.sub(r"\(.*?\)", "", cleaned)  # remove choices (a|b)
    return norm(cleaned)


def load_custom_sentences(config_dir: str | Path | None = None) -> dict:
    base = Path(config_dir) if config_dir else get_config_dir()
    data = {
        "intents": {},
        "responses": {},
        "files": [],
        "config_dir": str(base),
        "found": base.exists(),
    }
    if not base.exists() or yaml is None:
        return data

    # 1. Scan custom_sentences
    cs_pattern = str(base / "custom_sentences" / "**" / "*.yaml")
    for file_path in glob.glob(cs_pattern, recursive=True):
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            parsed = yaml.safe_load(content)
            if not isinstance(parsed, dict):
                continue
            data["files"].append(file_path)
            lang = str(parsed.get("language") or "it").lower()
            intents = parsed.get("intents") or {}
            for intent_name, intent_data in intents.items():
                if not isinstance(intent_data, dict):
                    continue
                sentences = []
                for entry in intent_data.get("data") or []:
                    if isinstance(entry, dict):
                        for s in entry.get("sentences") or []:
                            if isinstance(s, str) and s.strip():
                                sentences.append(s.strip())
                if sentences:
                    data["intents"].setdefault(intent_name, {
                        "sentences": [],
                        "language": lang,
                        "file": file_path,
                    })
                    data["intents"][intent_name]["sentences"].extend(sentences)
        except Exception as exc:
            log.warning("Errore lettura custom sentences da %s: %s", file_path, exc)

    # 2. Scan packages for intent_script responses
    pkg_pattern = str(base / "packages" / "**" / "*.yaml")
    for file_path in glob.glob(pkg_pattern, recursive=True):
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            parsed = yaml.safe_load(content)
            if not isinstance(parsed, dict):
                continue
            if file_path not in data["files"]:
                data["files"].append(file_path)
            scripts = parsed.get("intent_script") or {}
            for intent_name, script_data in scripts.items():
                if not isinstance(script_data, dict):
                    continue
                speech = script_data.get("speech") or {}
                text = speech.get("text", "") if isinstance(speech, dict) else str(speech)
                if text:
                    data["responses"][intent_name] = {
                        "text": text.strip(),
                        "file": file_path,
                    }
        except Exception as exc:
            log.warning("Errore lettura packages da %s: %s", file_path, exc)

    return data


def eval_simple_jinja(template: str, states: dict) -> str:
    """Valuta template Jinja essenziali di Home Assistant basandosi sugli stati reali."""
    # Sostituisce states('entity_id') o states("entity_id") con il valore reale
    def repl_states(m):
        eid = m.group(1).strip()
        st = states.get(eid) or {}
        val = st.get("state") if isinstance(st, dict) else str(st)
        return str(val) if val is not None and val != "unknown" and val != "unavailable" else "0"

    res = re.sub(r"\{\{\s*states\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}", repl_states, template)
    res = re.sub(r"\{\{\s*states\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\|\s*float\([0-9\.]*\)\s*\}\}", repl_states, res)
    # Rimuove blocchi Jinja generici residui {% ... %}
    res = re.sub(r"\{%.*?%\}", "", res)
    # Normalizza spazi
    return " ".join(res.split()).strip()


def match_and_eval(text: str, states: dict, config_dir: str | Path | None = None, language: str = "it") -> str | None:
    """Tenta il match con le custom sentences e genera la risposta con i sensori reali."""
    data = load_custom_sentences(config_dir)
    t_norm = norm(text)
    for intent_name, idata in data["intents"].items():
        if idata.get("language") and idata["language"] != language:
            continue
        for s in idata.get("sentences") or []:
            cleaned = _clean_sentence_pattern(s)
            if cleaned and (cleaned in t_norm or t_norm in cleaned):
                resp = data["responses"].get(intent_name)
                if resp and resp.get("text"):
                    return eval_simple_jinja(resp["text"], states)
    return None
