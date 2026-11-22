"""Preset e libreria di prompt: persona, istruzioni di sistema e modalità riutilizzabili."""

import re
import time
import uuid
from typing import Any, Dict, List, Optional

from .store import StudioStore

VALID_MODES = ("fast", "reasoning", "creative", "code")
_VAR_RE = re.compile(r"\{\{\s*([\w\- ]{1,40})\s*\}\}")


def render_template(text: str, variables: Optional[Dict[str, str]] = None) -> str:
    """Sostituisce {{campo}} con i valori forniti; i campi sconosciuti restano invariati."""
    values = variables or {}
    return _VAR_RE.sub(lambda m: str(values.get(m.group(1).strip(), m.group(0))), text)


class PresetService:
    def __init__(self, store: StudioStore) -> None:
        self.store = store
        with self.store._lock, self.store._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS presets (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    system_prompt TEXT NOT NULL DEFAULT '',
                    model_mode TEXT NOT NULL DEFAULT 'reasoning',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )

    def create(
        self,
        name: str,
        system_prompt: str,
        description: str = "",
        model_mode: str = "reasoning",
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        mode = model_mode if model_mode in VALID_MODES else "reasoning"
        now = int(time.time())
        preset_id = f"pre_{now}_{uuid.uuid4().hex[:6]}"
        with self.store._lock, self.store._get_connection() as conn:
            conn.execute(
                "INSERT INTO presets (id, project_id, name, description, system_prompt, model_mode, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (preset_id, project_id, name, description, system_prompt, mode, now, now),
            )
        return self.get(preset_id) or {}

    def get(self, preset_id: str) -> Optional[Dict[str, Any]]:
        with self.store._lock, self.store._get_connection() as conn:
            row = conn.execute("SELECT * FROM presets WHERE id = ?", (preset_id,)).fetchone()
        return dict(row) if row else None

    def list(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Preset globali (project_id nullo) più quelli del progetto indicato."""
        with self.store._lock, self.store._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM presets WHERE project_id IS NULL OR project_id = ? ORDER BY name COLLATE NOCASE",
                (project_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, preset_id: str) -> bool:
        with self.store._lock, self.store._get_connection() as conn:
            return bool(conn.execute("DELETE FROM presets WHERE id = ?", (preset_id,)).rowcount)
