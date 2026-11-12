import re
import shutil


def pci_address(value):
    match = re.fullmatch(r"0*([0-9a-f]{4}):([0-9a-f]{2}):([0-9a-f]{2})\.([0-7])", value.strip().lower())
    return ":".join(match.groups()[:3]) + "." + match[4] if match else ""


async def verified_capabilities(device, run):
    if device.vendor_id != "10de" or device.driver != "nvidia" or not shutil.which("nvidia-smi"):
        return []
    code, output = await run(["nvidia-smi", "--query-gpu=pci.bus_id", "--format=csv,noheader"], timeout=30)
    expected = pci_address(device.sys_id)
    if code == 0 and expected and expected in {pci_address(line) for line in output.splitlines()}:
        return ["compute.accelerator"]
    return []
