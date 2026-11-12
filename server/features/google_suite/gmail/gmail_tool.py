import os
import base64
import mimetypes
import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class EmailAttachment(BaseModel):
    filename: str
    content_base64: str = ""
    file_path: str = ""
    mime_type: str = ""
    size_bytes: int = 0

class EmailDraft(BaseModel):
    draft_id: str = ""
    to: List[str]
    cc: List[str] = Field(default_factory=list)
    bcc: List[str] = Field(default_factory=list)
    subject: str
    body_text: str
    body_html: str = ""
    attachments: List[EmailAttachment] = Field(default_factory=list)

class EmailFilterCriteria(BaseModel):
    query: str = ""
    sender: str = ""
    recipient: str = ""
    has_attachment: bool = False
    unread_only: bool = False
    label: str = "INBOX"
    max_results: int = 20

class GmailTool:
    def __init__(self) -> None:
        self.tool_id = "google_gmail_tool"
        self.name = "Google Gmail Expert"
        self._sent_mailbox: List[Dict[str, Any]] = []
        self._drafts: Dict[str, EmailDraft] = {}

    def send_email(self, draft: EmailDraft) -> Dict[str, Any]:
        processed_attachments = self._process_attachments(draft.attachments)
        msg_id = f"msg_{hashlib.sha256((draft.subject + str(draft.to)).encode()).hexdigest()[:16]}"
        record = {
            "message_id": msg_id,
            "to": draft.to,
            "cc": draft.cc,
            "bcc": draft.bcc,
            "subject": draft.subject,
            "body_text": draft.body_text,
            "body_html": draft.body_html or f"<p>{draft.body_text}</p>",
            "attachments": processed_attachments,
            "attachment_count": len(processed_attachments),
            "status": "SENT",
        }
        self._sent_mailbox.append(record)
        return {"status": "success", "message": record}

    def create_draft(self, draft: EmailDraft) -> Dict[str, Any]:
        draft_id = draft.draft_id or f"draft_{hashlib.md5(draft.subject.encode()).hexdigest()[:12]}"
        draft.draft_id = draft_id
        processed_attachments = self._process_attachments(draft.attachments)
        draft.attachments = [EmailAttachment(**a) for a in processed_attachments]
        self._drafts[draft_id] = draft
        return {"status": "success", "draft_id": draft_id, "draft": draft.model_dump()}

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        d = self._drafts.get(draft_id)
        return d.model_dump() if d else None

    def search_emails(self, criteria: EmailFilterCriteria) -> Dict[str, Any]:
        results = []
        for msg in self._sent_mailbox:
            match = True
            if criteria.sender and criteria.sender.lower() not in msg.get("from", "").lower():
                match = False
            if criteria.has_attachment and msg["attachment_count"] == 0:
                match = False
            if criteria.query:
                q = criteria.query.lower()
                if q not in msg["subject"].lower() and q not in msg["body_text"].lower():
                    match = False
            if match:
                results.append(msg)
        return {"status": "success", "count": len(results), "messages": results[:criteria.max_results]}

    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        return {"status": "success", "message_id": message_id, "marked_read": True}

    def delete_email(self, message_id: str) -> Dict[str, Any]:
        self._sent_mailbox = [m for m in self._sent_mailbox if m["message_id"] != message_id]
        return {"status": "success", "message_id": message_id, "deleted": True}

    def _process_attachments(self, attachments: List[EmailAttachment]) -> List[Dict[str, Any]]:
        processed = []
        for att in attachments:
            name = att.filename
            data_b64 = att.content_base64
            size = att.size_bytes
            mime = att.mime_type or mimetypes.guess_type(name)[0] or "application/octet-stream"

            if att.file_path and os.path.exists(att.file_path):
                size = os.path.getsize(att.file_path)
                with open(att.file_path, "rb") as fp:
                    data_b64 = base64.b64encode(fp.read()).decode()

            processed.append({
                "filename": name,
                "mime_type": mime,
                "size_bytes": size or (len(data_b64) * 3 // 4 if data_b64 else 0),
                "content_hash": hashlib.sha256(data_b64.encode()).hexdigest()[:16] if data_b64 else "",
            })
        return processed

gmail_tool = GmailTool()
