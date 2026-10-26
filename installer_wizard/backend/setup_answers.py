import os
from pathlib import Path
from fastapi import HTTPException
from config import DEMO, ETC_DIR
from state import store
import setup_owner
from setup_config import ANSWER_KEYS, PROFILES, SMB_RE

ANSWERS_FILE = ETC_DIR / "answers.env"

def parse_answers(text: str) -> dict:
    import setup_api
    raw: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key in ANSWER_KEYS:
            raw[key] = value.strip().strip('"').strip("'")
    profile = next((k for k, v in PROFILES.items() if v["model"] and v["model"] == raw.get("NUXIVA_LLM_MODEL")), "auto")
    picked = [p.strip() for p in raw.get("NUXIVA_PACKAGES", "").split(",") if p.strip()]
    updates = setup_api._clean({"name": raw.get("NUXIVA_USER_NAME", ""), "lang": raw.get("NUXIVA_UI_LANG", "it"), "profile": profile,
                      "brain": raw.get("NUXIVA_BRAIN", "local"), "ollama_url": raw.get("NUXIVA_OLLAMA_URL", ""),
                      "cloud_provider": raw.get("NUXIVA_CLOUD_PROVIDER", ""), "cloud_key": raw.get("NUXIVA_CLOUD_KEY", ""),
                      "packages": picked,
                      "voice": raw.get("NUXIVA_VOICE", "if_sara"), "ha_url": raw.get("HOME_ASSISTANT_URL", ""),
                      "ha_token": raw.get("HOME_ASSISTANT_TOKEN", ""), "telegram": raw.get("NUXIVA_TELEGRAM_TOKEN", ""),
                      "commercial": raw.get("NUXIVA_COMMERCIAL") == "1"})
    smb = raw.get("NUXIVA_SMB_PASSWORD", "")
    if smb:
        if not SMB_RE.fullmatch(smb):
            raise HTTPException(400, "Password delle condivisioni non valida (almeno 12 caratteri, nessuno spazio)")
        updates.update(NUXIVA_SMB_PASSWORD=smb, NUXIVA_SHARES="1")
    setup_api._store_cloud({"brain": raw.get("NUXIVA_BRAIN", ""), "cloud_provider": raw.get("NUXIVA_CLOUD_PROVIDER", ""),
                  "cloud_key": raw.get("NUXIVA_CLOUD_KEY", "")})
    return updates

def answers_trusted(path: Path) -> bool:
    try:
        st = path.lstat()
    except OSError:
        return False
    if not path.is_file() or path.is_symlink():
        return False
    return DEMO or os.environ.get("NUXIVA_TEST_AUTH") == "1" or (st.st_uid == 0 and not bool(st.st_mode & 0o022))

async def apply_answers_file(path: Path = ANSWERS_FILE) -> bool:
    import setup_api
    if setup_api.done() or not answers_trusted(path):
        return False
    try:
        updates = parse_answers(path.read_text(encoding="utf-8"))
    except HTTPException as exc:
        store.event("ERROR", f"File di risposte non applicato: {exc.detail}", "setup")
        return False
    except (OSError, UnicodeDecodeError) as exc:
        store.event("ERROR", f"File di risposte illeggibile: {exc}", "setup")
        return False
    await setup_api._apply(updates, "file di risposte")
    if updates.get("NUXIVA_USER_NAME"):
        setup_owner.register_owner(updates["NUXIVA_USER_NAME"], "", updates["NUXIVA_UI_LANG"], updates["NUXIVA_UI_LANG"])
    setup_api._mark_done("file di risposte")
    try:
        path.unlink()
    except OSError:
        pass
    return True
