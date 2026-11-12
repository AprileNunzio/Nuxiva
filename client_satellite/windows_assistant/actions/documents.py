from io import BytesIO
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from lxml.etree import XMLSyntaxError

from actions.common import ActionError, Outcome, PathGuard, Request
from actions.files import write_new
from i18n.strings import t
from permissions.gate import Gate


class Documents:
    def __init__(self, gate: Gate, guard: PathGuard) -> None:
        self.gate, self.guard = gate, guard

    def create_docx(self, action: dict) -> Outcome:
        path = self.guard.resolve(action.get("path", ""), t("documents.create"))
        content = self._content(path, action)
        self.gate.check(Request("files.create", t("documents.create"), f"{path}\n\n{content[:1500]}"))
        return self._save(Document(), path, content)

    def append_docx(self, action: dict) -> Outcome:
        path = self.guard.resolve(action.get("path", ""), t("documents.append"))
        content = self._content(path, action)
        destination = self.guard.resolve(action.get("destination", ""), t("documents.append"))
        if destination.suffix.lower() != ".docx":
            raise ActionError(t("documents.invalid"))
        self.gate.check(Request("files.read", t("documents.append"), str(path)))
        self.gate.check(Request("files.create", t("documents.append"), f"{path}\n→ {destination}\n\n{content[:1500]}"),
                        always_ask=True)
        try:
            with path.open("rb") as source:
                data = source.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024:
                raise ActionError(t("documents.invalid"))
            buffer = BytesIO(data)
            with ZipFile(buffer) as archive:
                entries = archive.infolist()
                if (len(entries) > 4096 or sum(entry.file_size for entry in entries) > 64 * 1024 * 1024
                        or any(entry.flag_bits & 1 or entry.compress_type not in (ZIP_STORED, ZIP_DEFLATED)
                               for entry in entries)):
                    raise ActionError(t("documents.invalid"))
            buffer.seek(0)
            document = Document(buffer)
        except (BadZipFile, PackageNotFoundError, XMLSyntaxError, KeyError, ValueError) as exc:
            raise ActionError(t("documents.invalid")) from exc
        return self._save(document, destination, content)

    @staticmethod
    def _content(path, action: dict) -> str:
        content = action.get("content", "")
        if path.suffix.lower() != ".docx" or not isinstance(content, str) or len(content) > 400_000:
            raise ActionError(t("documents.invalid"))
        return content

    @staticmethod
    def _save(document, path, content: str) -> Outcome:
        try:
            for paragraph in content.splitlines():
                document.add_paragraph(paragraph)
        except ValueError as exc:
            raise ActionError(t("documents.invalid")) from exc
        buffer = BytesIO()
        document.save(buffer)
        path.parent.mkdir(parents=True, exist_ok=True)
        target = write_new(path, buffer.getvalue())
        return Outcome(f"📄 {target}", {"path": str(target)})
