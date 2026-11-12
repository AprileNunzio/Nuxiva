import base64
import hashlib
import os
import re
import tempfile
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from server.config.env import settings
from server.features.repair_workbench.errors import SessionAccessException
from server.features.repair_workbench.session_models import WorkbenchSession

_CONTEXT = b"nuxiva.repair_workbench.v1"


def _cipher() -> Fernet:
    digest = hashlib.sha256(settings.NUXIVA_SECRET_KEY.encode("utf-8") + _CONTEXT).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


class EncryptedSessionStore:
    def __init__(self, root: Optional[str] = None) -> None:
        self._root = root or os.path.join(settings.DATA_DIR, "repair_workbench")

    def _path(self, owner_id: str, session_id: str) -> str:
        for identifier in (owner_id, session_id):
            if not re.fullmatch(r"[A-Za-z0-9_\-][A-Za-z0-9_.\-]{0,63}", identifier):
                raise SessionAccessException(session_id)
        directory = os.path.join(self._root, owner_id)
        os.makedirs(directory, exist_ok=True)
        return os.path.join(directory, f"{session_id}.enc")

    def save(self, session: WorkbenchSession) -> None:
        token = _cipher().encrypt(session.model_dump_json().encode("utf-8"))
        path = self._path(session.owner_id, session.session_id)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=os.path.dirname(path), delete=False) as handle:
                temporary = handle.name
                handle.write(token)
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.remove(temporary)

    def load(self, owner_id: str, session_id: str) -> Optional[WorkbenchSession]:
        path = self._path(owner_id, session_id)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as handle:
            token = handle.read()
        try:
            data = _cipher().decrypt(token)
        except InvalidToken as exc:
            raise SessionAccessException(session_id) from exc
        session = WorkbenchSession.model_validate_json(data)
        if session.owner_id != owner_id or session.session_id != session_id:
            raise SessionAccessException(session_id)
        return session
