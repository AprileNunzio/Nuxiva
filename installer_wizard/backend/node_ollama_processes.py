import os
import subprocess


def local_processes() -> list:
    import psutil

    markers = {"ollama", "llama-server", "llama_server"}
    found = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            command = proc.info.get("cmdline") or []
            names = [proc.info.get("name") or "", command[0] if command else ""]
            executables = {name.replace("\\", "/").rsplit("/", 1)[-1].lower().removesuffix(".exe") for name in names}
            if executables.intersection(markers) and proc.pid != os.getpid():
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def stop_local_ollama() -> None:
    import psutil

    if os.name != "nt":
        for action in ("stop", "disable"):
            try:
                subprocess.run(["systemctl", action, "ollama"], capture_output=True, timeout=30)
            except (OSError, subprocess.TimeoutExpired):
                continue
    for proc in local_processes():
        try:
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
