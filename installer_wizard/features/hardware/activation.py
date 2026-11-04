import shutil

from features.hardware.validation import INTERFACE


async def activate(device, run):
    commands = []
    if device.category == "wifi":
        if device.interface and not INTERFACE.fullmatch(device.interface):
            return False
        if shutil.which("rfkill"):
            commands.append(["rfkill", "unblock", "wifi"])
        if device.interface:
            commands.append(["ip", "link", "set", "dev", device.interface, "up"])
        if shutil.which("nmcli"):
            commands.append(["nmcli", "radio", "wifi", "on"])
    elif device.category == "bluetooth":
        if shutil.which("rfkill"):
            commands.append(["rfkill", "unblock", "bluetooth"])
        if shutil.which("systemctl"):
            commands.append(["systemctl", "start", "bluetooth"])
        if shutil.which("bluetoothctl"):
            commands.append(["bluetoothctl", "power", "on"])
    elif device.category == "printer" and shutil.which("systemctl"):
        commands.append(["systemctl", "start", "cups"])
    for command in commands:
        code, output = await run(command, timeout=30)
        device.add_step("activation", command[0], code == 0, output[-200:])
        if code:
            return False
    return True
