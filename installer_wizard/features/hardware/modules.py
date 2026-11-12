import asyncio
import re
from pathlib import Path

from features.hardware.atomic import write_text
from features.hardware.validation import MODULE


PANIC = re.compile(r"BUG:|Oops|Call Trace|general protection fault|kernel panic", re.I)


async def load_module(module, run, quarantine):
    if not isinstance(module, str) or not MODULE.fullmatch(module):
        return False, "Invalid module identifier"
    code, output = await run(["modprobe", "--dry-run", module], timeout=30)
    if code:
        return False, output[-200:]
    existing = Path("/sys/module", module.replace("-", "_")).exists()
    code, before = await run(["dmesg", "--raw"], timeout=10)
    if code:
        return False, "Kernel diagnostics unavailable; module loading refused"
    code, output = await run(["modprobe", module], timeout=60)
    if code:
        return False, output[-200:]
    await asyncio.sleep(0.1)
    code, after = await run(["dmesg", "--raw"], timeout=10)
    if code:
        return False, "Module loaded but kernel diagnostics unavailable"
    fresh = after[len(before):] if after.startswith(before) else after
    if PANIC.search(fresh):
        if existing:
            return False, "Kernel error detected; pre-existing module preserved"
        code, output = await run(["modprobe", "-r", module], timeout=30)
        if code:
            return False, "Kernel error detected; unloading failed: " + output[-200:]
        try:
            quarantine.mkdir(parents=True, exist_ok=True)
            write_text(quarantine / f"nuxiva-blacklist-{module}.conf", f"blacklist {module}\n")
        except OSError as exc:
            return False, f"Module unloaded; quarantine failed: {exc}"
        return False, "Module unloaded and quarantined until reboot"
    return True, "loaded"
