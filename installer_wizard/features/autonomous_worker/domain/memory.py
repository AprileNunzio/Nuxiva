from dataclasses import dataclass, field
import time
from typing import Any


@dataclass
class EpisodicMemory:
    summary: str = ""
    lessons_learned: list[str] = field(default_factory=list)
    key_decisions: list[str] = field(default_factory=list)
    last_compressed_at: float = field(default_factory=time.time)
    compression_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "lessons_learned": list(self.lessons_learned),
            "key_decisions": list(self.key_decisions),
            "last_compressed_at": self.last_compressed_at,
            "compression_count": self.compression_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EpisodicMemory":
        return cls(
            summary=str(data.get("summary", "")),
            lessons_learned=[str(item) for item in data.get("lessons_learned", [])],
            key_decisions=[str(item) for item in data.get("key_decisions", [])],
            last_compressed_at=float(data.get("last_compressed_at", time.time())),
            compression_count=int(data.get("compression_count", 0)),
        )
