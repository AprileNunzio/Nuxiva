import fnmatch
import hashlib
from pathlib import Path
import threading
import time
from typing import Any

from config import STATE_DIR
from features.autonomous_worker.application.code_intel import code_intel
from features.autonomous_worker.application.sandbox_validator import sandbox_validator
from features.autonomous_worker.domain.entities import ArtifactRevision
from features.autonomous_worker.domain.exceptions import MissionValidationError
from features.autonomous_worker.domain.models import Mission, MissionArtifact
from features.autonomous_worker.domain.sanitizer import resolve_safe_path, sanitize_text

ARTIFACTS_ROOT = STATE_DIR / "autonomous_missions" / "artifacts"


class ArtifactVault:
    def __init__(self, root: Path = ARTIFACTS_ROOT) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._guard = threading.RLock()
        self._file_locks: dict[str, threading.RLock] = {}

    def _lock_for(self, mission_id: str, relative_path: str) -> threading.RLock:
        key = f"{mission_id}:{relative_path}"
        with self._guard:
            if key not in self._file_locks:
                self._file_locks[key] = threading.RLock()
            return self._file_locks[key]

    def mission_dir(self, mission_id: str) -> Path:
        target = self.root / sanitize_text(mission_id, 40)
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _revisions_dir(self, mission_id: str) -> Path:
        rdir = self.mission_dir(mission_id) / ".revisions"
        rdir.mkdir(parents=True, exist_ok=True)
        return rdir

    def store_file(
        self,
        mission: Mission,
        relative_path: str,
        content: str | bytes,
        generated_by: str,
        title: str = "",
        kind: str = "file",
        expected_checksum: str = "",
    ) -> MissionArtifact:
        mdir = self.mission_dir(mission.id)
        target_path = resolve_safe_path(mdir, relative_path)
        rel_posix = str(target_path.relative_to(mdir).as_posix())

        with self._lock_for(mission.id, rel_posix):
            target_path.parent.mkdir(parents=True, exist_ok=True)
            old_text = ""
            if target_path.is_file():
                old_text = target_path.read_text(encoding="utf-8", errors="replace")
                if expected_checksum:
                    current_hash = hashlib.sha256(old_text.encode("utf-8")).hexdigest()
                    if current_hash != expected_checksum:
                        raise MissionValidationError(
                            f"CONCURRENT_MODIFICATION: {rel_posix} è stato modificato da un task parallelo"
                        )

            text_content = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
            data = content if isinstance(content, bytes) else content.encode("utf-8")
            target_path.write_bytes(data)

            checksum = hashlib.sha256(data).hexdigest()
            snap_file = self._revisions_dir(mission.id) / f"{checksum}.snap"
            if not snap_file.exists():
                snap_file.write_bytes(data)

            art_id = f"art_{checksum[:10]}"
            diff_str = code_intel.compute_unified_diff(old_text, text_content, rel_posix)
            symbols = code_intel.extract_symbols(rel_posix, text_content)
            imports = code_intel.extract_imports(rel_posix, text_content)
            line_count = code_intel.count_lines(text_content)
            now = time.time()

            existing_idx = next(
                (i for i, a in enumerate(mission.artifacts) if a.relative_path == rel_posix),
                None,
            )
            if existing_idx is not None:
                prev_art = mission.artifacts[existing_idx]
                new_version = prev_art.version + 1
                revisions = list(prev_art.revisions)
            else:
                new_version = 1
                revisions = []

            rev_entry = ArtifactRevision(
                version=new_version,
                checksum=checksum,
                diff=diff_str,
                line_count=line_count,
                size_bytes=len(data),
                generated_by=sanitize_text(generated_by, 60),
                timestamp=now,
            )
            revisions.append(rev_entry)
            revisions = revisions[-20:]

            artifact = MissionArtifact(
                id=art_id,
                title=sanitize_text(title or target_path.name, 100),
                kind=sanitize_text(kind, 30),
                relative_path=rel_posix,
                checksum=checksum,
                size_bytes=len(data),
                generated_by=sanitize_text(generated_by, 60),
                diff=diff_str,
                symbols=symbols,
                imports=imports,
                line_count=line_count,
                version=new_version,
                revisions=revisions,
                timestamp=now,
            )

            if existing_idx is not None:
                mission.artifacts[existing_idx] = artifact
            else:
                mission.artifacts.append(artifact)

            return artifact

    def apply_atomic_patch(
        self,
        mission: Mission,
        relative_path: str,
        target_block: str,
        replacement_block: str,
        generated_by: str,
        expected_checksum: str = "",
    ) -> MissionArtifact:
        mdir = self.mission_dir(mission.id)
        target_path = resolve_safe_path(mdir, relative_path)
        rel_posix = str(target_path.relative_to(mdir).as_posix())

        with self._lock_for(mission.id, rel_posix):
            if not target_path.is_file():
                raise FileNotFoundError(f"File non trovato per patch: {relative_path}")

            current_text = target_path.read_text(encoding="utf-8", errors="replace")
            if expected_checksum:
                current_hash = hashlib.sha256(current_text.encode("utf-8")).hexdigest()
                if current_hash != expected_checksum:
                    raise MissionValidationError("CHECKSUM_MISMATCH: il file è stato modificato da un altro agente")

            if target_block not in current_text:
                raise MissionValidationError("TARGET_BLOCK_NOT_FOUND: blocco originale non trovato nel file")

            if current_text.count(target_block) > 1:
                raise MissionValidationError("AMBIGUOUS_TARGET_BLOCK: il blocco appare più volte nel file")

            updated_text = current_text.replace(target_block, replacement_block, 1)
            is_valid, err_msg = sandbox_validator.validate_code(relative_path, updated_text)
            if not is_valid:
                raise MissionValidationError(err_msg)

            return self.store_file(
                mission=mission,
                relative_path=relative_path,
                content=updated_text,
                generated_by=generated_by,
                title=f"Patch: {target_path.name}",
                kind="patch",
            )

    def rollback_file(
        self,
        mission: Mission,
        relative_path: str,
        target_version: int,
        actor: str = "CEO Rollback",
    ) -> MissionArtifact:
        art = next((a for a in mission.artifacts if a.relative_path == relative_path), None)
        if not art:
            raise FileNotFoundError(f"Artefatto non trovato: {relative_path}")
        target_rev = next((r for r in art.revisions if r.version == target_version), None)
        if not target_rev:
            raise MissionValidationError(f"Versione v{target_version} non presente nello storico di {relative_path}")
        snap_file = self._revisions_dir(mission.id) / f"{target_rev.checksum}.snap"
        if not snap_file.is_file():
            raise FileNotFoundError(f"Snapshot fisico mancante per checksum {target_rev.checksum[:10]}")
        restored_bytes = snap_file.read_bytes()
        return self.store_file(
            mission=mission,
            relative_path=relative_path,
            content=restored_bytes,
            generated_by=f"{actor} ( -> v{target_version})",
            title=f"Rollback v{target_version}: {Path(relative_path).name}",
            kind="rollback",
        )

    def list_files(self, mission_id: str) -> list[dict[str, Any]]:
        mdir = self.mission_dir(mission_id)
        if not mdir.exists():
            return []
        items = []
        for p in mdir.rglob("*"):
            if p.is_file() and ".revisions" not in p.parts:
                rel = p.relative_to(mdir).as_posix()
                items.append({
                    "path": rel,
                    "size": p.stat().st_size,
                    "mtime": p.stat().st_mtime,
                })
        return items

    def read_file(self, mission_id: str, relative_path: str) -> str:
        mdir = self.mission_dir(mission_id)
        target_path = resolve_safe_path(mdir, relative_path)
        return target_path.read_text(encoding="utf-8", errors="replace")

    def read_file_lines(
        self,
        mission_id: str,
        relative_path: str,
        start_line: int = 1,
        end_line: int = 250,
    ) -> str:
        text = self.read_file(mission_id, relative_path)
        lines = text.splitlines()
        s_idx = max(0, int(start_line) - 1)
        e_idx = min(len(lines), max(s_idx + 1, int(end_line)))
        numbered = [f"{idx}: {lines[idx - 1]}" for idx in range(s_idx + 1, e_idx + 1)]
        return "\n".join(numbered)

    def search_workspace(
        self,
        mission_id: str,
        query: str,
        file_pattern: str = "*",
    ) -> list[dict[str, Any]]:
        mdir = self.mission_dir(mission_id)
        clean_q = query.strip()
        if not clean_q or not mdir.exists():
            return []
        matches: list[dict[str, Any]] = []
        q_low = clean_q.lower()
        for p in mdir.rglob("*"):
            if not p.is_file() or ".revisions" in p.parts:
                continue
            rel = p.relative_to(mdir).as_posix()
            if file_pattern and file_pattern != "*" and not fnmatch.fnmatch(rel, file_pattern):
                continue
            try:
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for idx, line in enumerate(lines, 1):
                if q_low in line.lower():
                    matches.append({
                        "path": rel,
                        "line": idx,
                        "snippet": line.strip()[:180],
                    })
                    if len(matches) >= 40:
                        return matches
        return matches


vault = ArtifactVault()
