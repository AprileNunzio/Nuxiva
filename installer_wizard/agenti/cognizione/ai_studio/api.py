import re
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from access import require_admin
from .models import Attachment
from .service import StudioService

public_routes = APIRouter(prefix="/api/ai_studio", tags=["ai_studio"])
admin_routes = APIRouter(prefix="/api/ai_studio", tags=["ai_studio"])

service = StudioService()

SAFE_NAME_RE = re.compile(r"^[\w\s\-\.\,\:\(\)\[\]]{1,120}$", re.UNICODE)


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=1000)
    instructions: str = Field("", max_length=5000)
    smb_folder: str = Field("", max_length=255)


class ProjectUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=1000)
    instructions: str = Field("", max_length=5000)
    smb_folder: str = Field("", max_length=255)


class ThreadCreateRequest(BaseModel):
    title: str = Field("Nuova conversazione", max_length=120)
    project_id: Optional[str] = None
    model_mode: str = Field("reasoning", max_length=32)


class ThreadUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=120)
    pinned: Optional[bool] = None
    model_mode: Optional[str] = Field(None, max_length=32)


class AttachmentPayload(BaseModel):
    name: str
    size: int
    mime_type: str
    kind: str
    path: str
    data_url: Optional[str] = None


class MessageSendRequest(BaseModel):
    content: str = Field(..., min_length=1)
    attachments: Optional[List[AttachmentPayload]] = None


class MemoryLearnRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    source: str = Field("written_chat", max_length=32)
    speaker: str = Field("", max_length=64)
    tags: Optional[List[str]] = None


class SmbSaveRequest(BaseModel):
    folder: str = Field(..., max_length=255)
    filename: str = Field(..., max_length=120)
    content: str


@public_routes.get("/projects")
async def list_projects() -> List[Dict[str, Any]]:
    return [p.to_dict() for p in service.store.list_projects()]


@admin_routes.post("/projects")
async def create_project(body: ProjectCreateRequest, _=Depends(require_admin)) -> Dict[str, Any]:
    project = service.create_project(
        name=body.name,
        description=body.description,
        instructions=body.instructions,
        smb_folder=body.smb_folder,
    )
    return project.to_dict()


@admin_routes.put("/projects/{project_id}")
async def update_project(project_id: str, body: ProjectUpdateRequest, _=Depends(require_admin)) -> Dict[str, Any]:
    updated = service.update_project(
        project_id=project_id,
        name=body.name,
        description=body.description,
        instructions=body.instructions,
        smb_folder=body.smb_folder,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    return updated.to_dict()


@admin_routes.delete("/projects/{project_id}")
async def delete_project(project_id: str, _=Depends(require_admin)) -> Dict[str, str]:
    service.store.delete_project(project_id)
    return {"status": "ok"}


@public_routes.get("/threads")
async def list_threads(project_id: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    return [t.to_dict() for t in service.store.list_threads(project_id=project_id)]


@admin_routes.post("/threads")
async def create_thread(body: ThreadCreateRequest, _=Depends(require_admin)) -> Dict[str, Any]:
    thread = service.create_thread(
        title=body.title,
        project_id=body.project_id,
        model_mode=body.model_mode,
    )
    return thread.to_dict()


@admin_routes.put("/threads/{thread_id}")
async def update_thread(thread_id: str, body: ThreadUpdateRequest, _=Depends(require_admin)) -> Dict[str, Any]:
    updated = service.update_thread(
        thread_id=thread_id,
        title=body.title,
        pinned=body.pinned,
        model_mode=body.model_mode,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Conversazione non trovata")
    return updated.to_dict()


@admin_routes.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str, _=Depends(require_admin)) -> Dict[str, str]:
    service.store.delete_thread(thread_id)
    return {"status": "ok"}


@public_routes.get("/threads/{thread_id}/messages")
async def list_messages(thread_id: str) -> List[Dict[str, Any]]:
    return [m.to_dict() for m in service.store.list_messages(thread_id)]


@admin_routes.post("/threads/{thread_id}/messages")
async def send_message(thread_id: str, body: MessageSendRequest, _=Depends(require_admin)) -> Dict[str, Any]:
    attachments: List[Attachment] = []
    if body.attachments:
        for a in body.attachments:
            attachments.append(
                Attachment(
                    id=f"att_{int(time.time())}",
                    name=a.name,
                    size=a.size,
                    mime_type=a.mime_type,
                    kind=a.kind,
                    path=a.path,
                    data_url=a.data_url,
                )
            )

    msg = await service.send_message(
        thread_id=thread_id,
        content=body.content,
        attachments=attachments,
    )
    return msg.to_dict()


@public_routes.get("/memory/facts")
async def list_memory_facts(q: str = Query("")) -> List[Dict[str, Any]]:
    if q.strip():
        facts = service.memory.recall(q, limit=20)
    else:
        facts = service.memory.get_all_facts()[:50]
    return [f.to_dict() for f in facts]


@admin_routes.post("/memory/learn")
async def learn_memory(body: MemoryLearnRequest, _=Depends(require_admin)) -> Dict[str, Any]:
    fact = service.memory.learn(
        content=body.content,
        source=body.source,
        speaker=body.speaker,
        tags=body.tags,
    )
    return fact.to_dict()


@public_routes.get("/smb/tree")
async def smb_tree(folder: str = Query("")) -> List[Dict[str, Any]]:
    try:
        items = service.smb.list_folder(folder)
        return [i.to_dict() for i in items]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@admin_routes.post("/smb/save")
async def smb_save(body: SmbSaveRequest, _=Depends(require_admin)) -> Dict[str, Any]:
    try:
        rel_path = service.smb.save_file(body.folder, body.filename, body.content)
        unc = service.smb.get_unc_path(rel_path)
        return {"status": "ok", "relative_path": rel_path, "unc_path": unc}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@admin_routes.post("/upload")
async def upload_attachment(file: UploadFile = File(...), _=Depends(require_admin)) -> Dict[str, Any]:
    from config import STATE_DIR
    target_dir = STATE_DIR / "uploads"
    target_dir.mkdir(parents=True, exist_ok=True)
    clean_name = re.sub(r"[^A-Za-z0-9._ -]+", "_", file.filename or "file.bin")
    file_path = target_dir / f"{int(time.time())}_{clean_name}"
    content = await file.read()
    file_path.write_bytes(content)
    return {
        "name": file.filename,
        "size": len(content),
        "mime_type": file.content_type or "application/octet-stream",
        "path": str(file_path),
    }
