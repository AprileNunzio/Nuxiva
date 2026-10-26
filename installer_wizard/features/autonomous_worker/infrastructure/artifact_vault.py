import hashlib
from pathlib import Path
import time

from config import STATE_DIR
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

        data = content.encode("utf-8") if isinstance(content, str) else content
        target_path.write_bytes(data)

        checksum = hashlib.sha256(data).hexdigest()
        art_id = f"art_{checksum[:10]}"

        artifact = MissionArtifact(
            id=art_id,
            title=sanitize_text(title or target_path.name, 100),
            kind=sanitize_text(kind, 30),
            relative_path=str(target_path.relative_to(mdir).as_posix()),
            checksum=checksum,
            size_bytes=len(data),
            generated_by=sanitize_text(generated_by, 60),
            timestamp=time.time(),
        )

        existing_idx = next((i for i, a in enumerate(mission.artifacts) if a.relative_path == artifact.relative_path), None)
        if existing_idx is not None:
            mission.artifacts[existing_idx] = artifact
        else:
            mission.artifacts.append(artifact)

        return artifact

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
