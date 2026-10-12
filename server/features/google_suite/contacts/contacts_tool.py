import hashlib
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ContactPhoneNumber(BaseModel):
    number: str
    type: str = "mobile" # mobile, work, home

class ContactEmail(BaseModel):
    address: str
    type: str = "work" # work, home, other

class ContactFullRecord(BaseModel):
    contact_id: str = ""
    given_name: str
    family_name: str = ""
    organization: str = ""
    job_title: str = ""
    emails: List[ContactEmail] = Field(default_factory=list)
    phones: List[ContactPhoneNumber] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    notes: str = ""

class ContactsTool:
    def __init__(self) -> None:
        self.tool_id = "google_contacts_tool"
        self.name = "Google Contacts Expert"
        self._directory: Dict[str, ContactFullRecord] = {}

    def create_contact(self, record: ContactFullRecord) -> Dict[str, Any]:
        cid = record.contact_id or f"cnt_{hashlib.sha256((record.given_name + record.family_name + str(record.emails)).encode()).hexdigest()[:14]}"
        record.contact_id = cid
        self._directory[cid] = record
        return {"status": "success", "contact": record.model_dump()}

    def find_contact(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        matched = []
        for c in self._directory.values():
            if (q in c.given_name.lower() or 
                q in c.family_name.lower() or 
                q in c.organization.lower() or 
                any(q in e.address.lower() for e in c.emails) or
                any(q in p.number for p in c.phones)):
                matched.append(c.model_dump())
        return {"status": "success", "query": query, "count": len(matched), "contacts": matched}

    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if contact_id not in self._directory:
            return {"status": "error", "message": "Contatto non trovato"}
        curr = self._directory[contact_id].model_dump()
        curr.update(updates)
        new_c = ContactFullRecord(**curr)
        self._directory[contact_id] = new_c
        return {"status": "success", "contact": new_c.model_dump()}

    def delete_contact(self, contact_id: str) -> Dict[str, Any]:
        if contact_id in self._directory:
            del self._directory[contact_id]
            return {"status": "success", "contact_id": contact_id, "deleted": True}
        return {"status": "error", "message": "Contatto non trovato"}

    def list_all_contacts(self, limit: int = 50) -> Dict[str, Any]:
        items = list(self._directory.values())
        return {"status": "success", "count": len(items), "contacts": [i.model_dump() for i in items[:limit]]}

contacts_tool = ContactsTool()
