import hashlib
from pathlib import Path
import time

from config import STATE_DIR
from features.autonomous_worker.application.code_intel import code_intel
from features.autonomous_worker.application.sandbox_validator import sandbox_validator
from features.autonomous_worker.domain.exceptions import MissionValidationError
from features.autonomous_worker.domain.models import Mission, MissionArtifact
from features.autonomous_worker.domain.sanitizer import resolve_safe_path, sanitize_text

ARTIFACTS_ROOT = STATE_DIR / "autonomous_missions" / "artifacts"


class ArtifactVault:
    def __init__(self, root: Path = ARTIFACTS_ROOT) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def mission_dir(self, mission_id: str) -> Path:
        target = self.root / sanitize_text(mission_id, 40)
        target.mkdir(parents=True, exist_ok=True)
        return target

    def store_file(
        self,
        mission: Mission,
        relative_path: str,
        content: str | bytes,
        generated_by: str,
        title: str = "",
        kind: str = "file",
    ) -> MissionArtifact:
        mdir = self.mission_dir(mission.id)
        target_path = resolve_safe_path(mdir, relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        rel_posix = str(target_path.relative_to(mdir).as_posix())
        old_text = ""
        if target_path.is_file():
            old_text = target_path.read_text(encoding="utf-8", errors="replace")

        text_content = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
        data = content if isinstance(content, bytes) else content.encode("utf-8")
        target_path.write_bytes(data)

        checksum = hashlib.sha256(data).hexdigest()
        art_id = f"art_{checksum[:10]}"
        diff_str = code_intel.compute_unified_diff(old_text, text_content, rel_posix)
        symbols = code_intel.extract_symbols(rel_posix, text_content)
        line_count = code_intel.count_lines(text_content)

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
            line_count=line_count,
            timestamp=time.time(),
        )

        existing_idx = next(
            (i for i, a in enumerate(mission.artifacts) if a.relative_path == artifact.relative_path),
            None,
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

    def list_files(self, mission_id: str) -> list[dict]:
        mdir = self.mission_dir(mission_id)
        if not mdir.exists():
            return []
        items = []
        for p in mdir.rglob("*"):
            if p.is_file():
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


vault = ArtifactVault()
