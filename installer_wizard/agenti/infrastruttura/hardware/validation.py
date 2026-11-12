import re
from pathlib import PurePosixPath


MODULE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_-]{0,63}")
PACKAGE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9+_.:-]{0,127}")
INTERFACE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,14}")


def firmware_path(name):
    path = PurePosixPath(name)
    return bool(name and len(name) <= 240 and not path.is_absolute()
                and ".." not in path.parts and re.fullmatch(r"[A-Za-z0-9_./+-]+", name))


def packages_valid(packages):
    return len(packages) <= 128 and all(isinstance(p, str) and PACKAGE.fullmatch(p) for p in packages)
