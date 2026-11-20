from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Project:
    id: str
    name: str
    description: str
    instructions: str
    smb_folder: str
    created_at: int
    updated_at: int
    thread_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "smb_folder": self.smb_folder,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "thread_count": self.thread_count,
        }


@dataclass
class Thread:
    id: str
    project_id: Optional[str]
    title: str
    pinned: bool
    model_mode: str
    created_at: int
    updated_at: int
    message_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "pinned": self.pinned,
            "model_mode": self.model_mode,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": self.message_count,
        }


@dataclass
class Attachment:
    id: str
    name: str
    size: int
    mime_type: str
    kind: str
    path: str
    data_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "size": self.size,
            "mime_type": self.mime_type,
            "kind": self.kind,
            "path": self.path,
            "data_url": self.data_url,
        }


@dataclass
class Artifact:
    id: str
    identifier: str
    title: str
    kind: str
    language: str
    content: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "identifier": self.identifier,
            "title": self.title,
            "kind": self.kind,
            "language": self.language,
            "content": self.content,
        }


@dataclass
class MemoryFact:
    id: str
    source: str
    content: str
    speaker: str
    timestamp: int
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "content": self.content,
            "speaker": self.speaker,
            "timestamp": self.timestamp,
            "tags": self.tags,
        }


@dataclass
class Message:
    id: str
    thread_id: str
    role: str
    content: str
    thought: str
    artifacts: List[Artifact] = field(default_factory=list)
    attachments: List[Attachment] = field(default_factory=list)
    memory_recalls: List[MemoryFact] = field(default_factory=list)
    created_at: int = 0
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "role": self.role,
            "content": self.content,
            "thought": self.thought,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "attachments": [a.to_dict() for a in self.attachments],
            "memory_recalls": [m.to_dict() for m in self.memory_recalls],
            "created_at": self.created_at,
            "cached": self.cached,
        }


@dataclass
class SmbItem:
    name: str
    relative_path: str
    is_dir: bool
    size: int
    modified_at: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "relative_path": self.relative_path,
            "is_dir": self.is_dir,
            "size": self.size,
            "modified_at": self.modified_at,
        }
