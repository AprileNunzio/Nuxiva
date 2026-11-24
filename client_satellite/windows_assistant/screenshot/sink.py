import os
import secrets
import stat
from pathlib import Path

from screenshot import rules


class SinkError(Exception):
    pass


class AuthError(SinkError):
    pass


class UnreachableError(SinkError):
    pass


def unc_root(config: rules.Config) -> Path:
    if config.drive:
        return Path(config.drive + "\\")
    return Path(f"\\\\{config.host}\\{config.share}")


def resolve(root: Path, subdir: str) -> Path:
    if not rules.valid_subdir(subdir):
        raise SinkError("subdir")
    base = Path(os.path.realpath(root))
    if not base.is_dir():
        raise SinkError("root")
    current = base
    for part in [p for p in subdir.split("/") if p]:
        current = current / part
        if current.exists():
            info = os.lstat(current)
            reparse = getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            if stat.S_ISLNK(info.st_mode) or reparse or not stat.S_ISDIR(info.st_mode):
                raise SinkError("unsafe")
        else:
            current.mkdir()
    real = Path(os.path.realpath(current))
    if real != base and base not in real.parents:
        raise SinkError("escape")
    return real


def put(directory: Path, name: str, data: bytes) -> None:
    if not rules.is_managed(name):
        raise SinkError("name")
    final = directory / name
    if final.exists():
        return
    temp = directory / f".tmp-{secrets.token_hex(8)}"
    try:
        with open(temp, "xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, final)
    except OSError as exc:
        raise SinkError(str(exc)) from exc
    finally:
        if temp.exists():
            temp.unlink()


def listing(directory: Path) -> list:
    out = []
    for entry in directory.iterdir():
        when = rules.stamp(entry.name)
        if when is not None and entry.is_file() and not entry.is_symlink():
            out.append((entry.name, when))
    return out


def remove(directory: Path, name: str) -> None:
    if not rules.is_managed(name):
        raise SinkError("name")
    (directory / name).unlink()
