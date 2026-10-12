import sys
from cx_Freeze import setup, Executable

# Definisci le dipendenze che cx_Freeze deve includere obbligatoriamente
build_exe_options = {
    "packages": [
        "os", "sys", "fastapi", "uvicorn", "uiautomation", 
        "mss", "cryptography", "customtkinter", "pydantic"
    ],
    "excludes": ["tkinter.test", "unittest"],
    "include_msvcr": True,  # Include i runtime Microsoft necessari
}

# Win32GUI nasconde la console nera del terminale su Windows
base = "Win32GUI" if sys.platform == "win32" else None

# Configurazione dell'eseguibile
executables = [
    Executable(
        script="gui.py",
        base=base,
        target_name="NuxivaSatellite.exe",
        # icon="nuxiva_icon.ico", # Decommenta se aggiungi un file .ico nella cartella
        shortcut_name="NUXIVA Satellite",
        shortcut_dir="DesktopFolder"
    )
]

setup(
    name="NUXIVA Satellite",
    version="4.1.53",
    description="Client Desktop Interattivo e Context Bridge per NUXIVA",
    author="NunzioTech",
    options={"build_exe": build_exe_options},
    executables=executables
)
