import re

DETAIL_RE = re.compile(r"[^A-Za-z0-9 ._:/-]+")
DETAIL_LIMIT = 80


def clean_detail(text: object) -> str:
    return DETAIL_RE.sub(" ", str(text or "")).strip()[:DETAIL_LIMIT].strip()


class UpdateFailure(Exception):
    def __init__(self, code: str, detail: object = "", transient: bool = False) -> None:
        self.code = code
        self.detail = clean_detail(detail)
        self.transient = transient
        super().__init__(f"{code}: {self.detail}" if self.detail else code)


class UpdateCancelled(Exception):
    pass
