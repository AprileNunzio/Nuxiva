import sys
from pathlib import Path

TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=({a}, {b}, {c}, {d}), prodvers=({a}, {b}, {c}, {d}), mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'NunzioTech'),
      StringStruct('FileDescription', 'Nuxiva'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'Nuxiva'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 NunzioTech'),
      StringStruct('OriginalFilename', 'Nuxiva.exe'),
      StringStruct('ProductName', 'Nuxiva'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def parts(version: str) -> tuple[int, int, int, int]:
    numbers = [int(p) for p in version.split(".")][:4]
    return tuple(numbers + [0] * (4 - len(numbers)))


def main(version: str, target: str) -> None:
    a, b, c, d = parts(version)
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE.format(a=a, b=b, c=c, d=d, version=version), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
