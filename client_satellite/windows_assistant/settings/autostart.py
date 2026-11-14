import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from settings import paths

log = logging.getLogger("nuxiva.autostart")
TASK_NAME = "Nuxiva"
LEGACY_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
LEGACY_RUN_NAME = "NUXIVA Assistente"
NO_WINDOW = 0x08000000
TASK_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Author>NunzioTech</Author><Description>Nuxiva</Description></RegistrationInfo>
  <Triggers><LogonTrigger><Enabled>true</Enabled><UserId>{user}</UserId></LogonTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>{user}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>HighestAvailable</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>5</Priority>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author"><Exec><Command>{command}</Command>{arguments}<WorkingDirectory>{directory}</WorkingDirectory></Exec></Actions>
</Task>
"""


def launch() -> tuple[str, str, str]:
    if paths.FROZEN:
        exe = Path(sys.executable).resolve()
        return str(exe), "", str(exe.parent)
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    interpreter = pythonw if pythonw.exists() else Path(sys.executable)
    return str(interpreter), f'"{paths.APP_DIR / "nuxiva_assistant.py"}"', str(paths.APP_DIR)


def current_user() -> str:
    name = os.environ.get("USERNAME", "")
    domain = os.environ.get("USERDOMAIN", "")
    return f"{domain}\\{name}" if domain and name else name


def task_xml(command: str, arguments: str, directory: str, user: str) -> str:
    args = f"<Arguments>{escape(arguments)}</Arguments>" if arguments else ""
    return TASK_XML.format(user=escape(user), command=escape(command), arguments=args, directory=escape(directory))


def _schtasks(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "schtasks.exe"), *args],
                          capture_output=True, creationflags=NO_WINDOW, check=False, timeout=30)


def _drop_legacy() -> bool:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, LEGACY_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, LEGACY_RUN_NAME)
    except FileNotFoundError:
        return False
    return True


def enabled() -> bool:
    return _schtasks("/Query", "/TN", TASK_NAME).returncode == 0


def set_enabled(on: bool, had_legacy: bool = False) -> bool:
    had_legacy = _drop_legacy() or had_legacy
    if not on:
        if enabled():
            _schtasks("/Delete", "/TN", TASK_NAME, "/F")
        return True
    command, arguments, directory = launch()
    body = task_xml(command, arguments, directory, current_user())
    with tempfile.TemporaryDirectory() as folder:
        target = Path(folder) / "nuxiva_task.xml"
        target.write_text(body, encoding="utf-16")
        result = _schtasks("/Create", "/TN", TASK_NAME, "/XML", str(target), "/F")
    if result.returncode != 0:
        log.error("Avvio automatico non creato: %s", result.stderr.decode(errors="replace").strip())
        return False
    return True


def refresh() -> None:
    if not paths.FROZEN:
        return
    legacy = _drop_legacy()
    if legacy or enabled():
        set_enabled(True, legacy)
