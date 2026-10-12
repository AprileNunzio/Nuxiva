import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class DrivePermission(BaseModel):
    role: str = "reader" # owner, writer, commenter, reader
    type: str = "user" # user, group, domain, anyone
    email_address: str = ""

class DriveFileItem(BaseModel):
    file_id: str = ""
    name: str
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0
    parent_folder_id: str = "root"
    is_folder: bool = False
    download_url: str = ""
    web_view_link: str = ""
    permissions: List[DrivePermission] = Field(default_factory=list)

class DriveTool:
    def __init__(self) -> None:
        self.tool_id = "google_drive_tool"
        self.name = "Google Drive Expert"
        self._drive_store: Dict[str, DriveFileItem] = {}

    def upload_file(self, item: DriveFileItem, content_bytes: bytes = b"") -> Dict[str, Any]:
        fid = item.file_id or f"drv_{hashlib.sha256((item.name + item.parent_folder_id).encode()).hexdigest()[:16]}"
        item.file_id = fid
        item.size_bytes = len(content_bytes) if content_bytes else item.size_bytes
        item.web_view_link = f"https://drive.google.com/file/d/{fid}/view"
        self._drive_store[fid] = item
        return {"status": "success", "file": item.model_dump()}

    def create_folder(self, name: str, parent_id: str = "root") -> Dict[str, Any]:
        folder_item = DriveFileItem(
            name=name,
            mime_type="application/vnd.google-apps.folder",
            parent_folder_id=parent_id,
            is_folder=True,
        )
        return self.upload_file(folder_item)

    def list_files(self, folder_id: str = "root", query: str = "") -> Dict[str, Any]:
        matched = []
        for f in self._drive_store.values():
            if folder_id and f.parent_folder_id != folder_id:
                continue
            if query and query.lower() not in f.name.lower():
                continue
            matched.append(f.model_dump())
        return {"status": "success", "folder_id": folder_id, "count": len(matched), "files": matched}

    def share_file(self, file_id: str, permission: DrivePermission) -> Dict[str, Any]:
        if file_id not in self._drive_store:
            return {"status": "error", "message": "File non trovato"}
        self._drive_store[file_id].permissions.append(permission)
        return {"status": "success", "file_id": file_id, "permission": permission.model_dump()}

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        if file_id in self._drive_store:
            del self._drive_store[file_id]
            return {"status": "success", "file_id": file_id, "deleted": True}
        return {"status": "error", "message": "File non trovato"}

drive_tool = DriveTool()
