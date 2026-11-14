from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

ROOT = Path(SPECPATH).parent
datas, binaries, hiddenimports = collect_data_files("customtkinter"), [], []
datas += collect_data_files("docx")
datas += [(str(path), "i18n") for path in (ROOT / "i18n").glob("*.json")]
for package in ("uiautomation", "comtypes"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

analysis = Analysis(
    [str(ROOT / "nuxiva_assistant.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tests", "pytest", "matplotlib"],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Nuxiva",
    console=False,
    uac_admin=True,
    icon=str(ROOT / "build" / "nuxiva.ico"),
    version=str(ROOT / "build" / "version_info.txt"),
)
COLLECT(exe, analysis.binaries, analysis.datas, name="Nuxiva")
