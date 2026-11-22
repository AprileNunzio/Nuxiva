import os
import re
import time
from pathlib import Path
from typing import List, Optional
from config import DEMO, STATE_DIR
from .models import SmbItem

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

SHARE = "condivisa"
DEFAULT_ROOT = (STATE_DIR / "srv" / SHARE) if (DEMO or os.environ.get("NUXIVA_TEST_AUTH") == "1") else Path("/srv/nuxiva") / SHARE
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9._ /-]+$")


class SmbStudioService:
    def __init__(self, root_path: Optional[Path] = None) -> None:
        if root_path is not None:
            self.root_path = root_path
        else:
            try:
                DEFAULT_ROOT.mkdir(parents=True, exist_ok=True)
                self.root_path = DEFAULT_ROOT
            except OSError:
                fallback_share = Path.home() / ".local/share/nuxiva/condivisa"
                self.root_path = fallback_share
        try:
            self.root_path.mkdir(parents=True, exist_ok=True)
            self._ensure_standard_folders()
        except OSError:
            pass

    def _ensure_standard_folders(self) -> None:
        standard = [
            "01 Documenti",
            "02 Siti web",
            "03 Modelli 3D",
            "04 Codice",
            "05 Scambio",
            "06 Musica",
            "07 Diorami",
            "08 Produzioni",
            "09 Progetti",
        ]
        for folder in standard:
            (self.root_path / folder).mkdir(parents=True, exist_ok=True)

    def validate_relative_path(self, rel_path: str) -> Path:
        if nuxiva_native and hasattr(nuxiva_native, "RustChatStudio"):
            try:
                resolved = nuxiva_native.RustChatStudio.resolve_safe_smb_path(str(self.root_path), rel_path)
                return Path(resolved)
            except Exception:
                raise ValueError("Path traversal or illegal SMB path detected")

        clean = rel_path.replace("\\", "/").strip().lstrip("/")
        if not clean:
            return self.root_path
        if "\0" in clean or ".." in clean.split("/"):
            raise ValueError("Path traversal or illegal SMB path detected")
        if not SAFE_PATH_RE.match(clean):
            raise ValueError("Illegal characters in SMB path")

        target = (self.root_path / clean).resolve()
        if not str(target).startswith(str(self.root_path.resolve())):
            raise ValueError("Path escapes SMB root")
        return target

    def list_folder(self, rel_path: str = "") -> List[SmbItem]:
        target = self.validate_relative_path(rel_path)
        if not target.exists() or not target.is_dir():
            return []

        items: List[SmbItem] = []
        for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            try:
                rel = str(entry.relative_to(self.root_path)).replace("\\", "/")
                stat = entry.stat()
                items.append(
                    SmbItem(
                        name=entry.name,
                        relative_path=rel,
                        is_dir=entry.is_dir(),
                        size=stat.st_size if not entry.is_dir() else 0,
                        modified_at=int(stat.st_mtime),
                    )
                )
            except (OSError, ValueError):
                continue
        return items

    def save_file(self, rel_dir: str, filename: str, content: str) -> str:
        clean_name = re.sub(r"[^A-Za-z0-9._ -]+", "_", filename).strip()
        if not clean_name:
            clean_name = f"artifact_{int(time.time())}.txt"

        dir_path = self.validate_relative_path(rel_dir)
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / clean_name
        file_path.write_text(content, encoding="utf-8")
        return str(file_path.relative_to(self.root_path)).replace("\\", "/")

    def get_unc_path(self, rel_path: str) -> str:
        clean = rel_path.replace("/", "\\").strip("\\")
        return f"\\\\Nuxiva\\{SHARE}\\{clean}"
