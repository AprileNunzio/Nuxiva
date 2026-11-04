import re

from features.hardware.validation import firmware_path


ERROR = re.compile(r"(?:failed to load|Direct firmware load for)\s+([A-Za-z0-9_./+-]+)")


def missing_for_device(output, device, exists):
    token = device.sys_id or device.driver
    if not token:
        return []
    pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])")
    missing = []
    for line in output.splitlines():
        if not pattern.search(line):
            continue
        match = ERROR.search(line)
        if match and firmware_path(match[1]) and not exists(match[1]) and match[1] not in missing:
            missing.append(match[1])
    return missing
