import asyncio
import logging
import os
import shutil

log = logging.getLogger("nuxiva.voice.playback")
KIOSK_USER = os.environ.get("NUXIVA_KIOSK_USER", "nuxiva-kiosk")


def _get_kiosk_uid() -> int | None:
    try:
        import pwd
        return pwd.getpwnam(KIOSK_USER).pw_uid
    except (KeyError, ImportError):
        return None


def get_playback_commands() -> list[list[str]]:
    cmds: list[list[str]] = []
    custom = os.environ.get("NUXIVA_PLAY_CMD")
    if custom:
        cmds.append(custom.split())
    uid = _get_kiosk_uid()
    if shutil.which("paplay"):
        if os.name != "nt" and hasattr(os, "getuid") and os.getuid() == 0 and uid is not None and shutil.which("runuser"):
            cmds.append(["runuser", "-u", KIOSK_USER, "--", "env", f"XDG_RUNTIME_DIR=/run/user/{uid}", "paplay"])
        cmds.append(["paplay"])
    if shutil.which("pw-play"):
        cmds.append(["pw-play", "-"])
    if shutil.which("aplay"):
        cmds.append(["aplay", "-q", "-"])
    return cmds


async def play_host_audio(wav: bytes) -> bool:
    if not wav:
        return False
    cmds = get_playback_commands()
    if not cmds:
        log.warning("Nessun comando di riproduzione audio disponibile")
        return False
    for cmd in cmds:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            _, err = await asyncio.wait_for(proc.communicate(input=wav), timeout=25.0)
            if proc.returncode == 0:
                return True
            err_msg = err.decode("utf-8", "replace").strip() if err else f"codice {proc.returncode}"
            log.warning("Riproduzione audio con %s non riuscita: %s", cmd[0], err_msg)
        except (OSError, asyncio.TimeoutError) as exc:
            log.warning("Tentativo esecuzione %s fallito: %s", cmd[0], exc)
    return False
