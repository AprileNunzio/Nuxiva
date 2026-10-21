import json
import logging
from pathlib import Path
from threading import Lock
from typing import Mapping, Optional

from features.locale.colocated.domain import parse_dictionary, parse_meta
from features.locale.colocated.errors import BundleCorrupted, BundleUnreadable

MAX_FILE_BYTES = 512 * 1024
Stamp = tuple[int, int]
log = logging.getLogger("nuxiva.i18n")


class LanguageFileRepository:
    def __init__(self, max_bytes: int = MAX_FILE_BYTES) -> None:
        self._max_bytes = max_bytes
        self._cache: dict[Path, tuple[Stamp, Optional[Mapping[str, str]]]] = {}
        self._lock = Lock()

    def dictionary(self, path: Path) -> Optional[Mapping[str, str]]:
        if not path.is_file():
            return None
        info = path.stat()
        stamp = (info.st_mtime_ns, info.st_size)
        with self._lock:
            cached = self._cache.get(path)
        if cached is not None and cached[0] == stamp:
            return cached[1]
        parsed = self._parse(path, info.st_size)
        with self._lock:
            self._cache[path] = (stamp, parsed)
        return parsed

    def _parse(self, path: Path, size: int) -> Optional[Mapping[str, str]]:
        origin = f"{path.parent.parent.name}/{path.name}"
        if size > self._max_bytes:
            log.error("i18n file too large: %s (%d bytes)", path, size)
            raise BundleCorrupted(f"{origin}: file too large")
        payload = self._decode(path, origin)
        if not isinstance(payload, dict):
            raise BundleCorrupted(f"{origin}: root must be an object")
        if "dictionary" not in payload:
            return None
        parse_meta(payload.get("meta"), path.stem, origin)
        return parse_dictionary(payload["dictionary"], origin)

    @staticmethod
    def _decode(path: Path, origin: str) -> object:
        try:
            raw = path.read_bytes()
        except OSError as exc:
            log.error("i18n file unreadable: %s", path, exc_info=exc)
            raise BundleUnreadable(f"{origin}: unreadable") from exc
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            log.error("i18n file malformed: %s", path, exc_info=exc)
            raise BundleCorrupted(f"{origin}: malformed JSON") from exc
