import re

from features.hardware.validation import MODULE, firmware_path, packages_valid


def validate_catalog(data):
    if not isinstance(data, dict):
        raise ValueError("Hardware catalog must be an object")
    for raw in data.get("recipes", []):
        if not isinstance(raw, dict) or not re.fullmatch(r"[a-z0-9-]{1,64}", raw.get("id", "")):
            raise ValueError("Invalid driver recipe")
        if any(not MODULE.fullmatch(module) for module in raw.get("modules", [])):
            raise ValueError("Invalid catalog module")
        if any(not firmware_path(firmware) for firmware in raw.get("firmware", [])):
            raise ValueError("Invalid catalog firmware path")
        for bus, pairs in raw.get("match", {}).items():
            if bus not in ("usb", "pci", "acpi", "i2c", "spi", "thunderbolt") or any(
                not re.fullmatch(r"[0-9a-fA-F]{4}:[0-9a-fA-F]{4}", pair) for pair in pairs
            ):
                raise ValueError("Invalid catalog identifier")
        spec = raw.get("dkms")
        if spec:
            from features.hardware.dkms import validate_git_url
            if not validate_git_url(spec.get("git")) or not re.fullmatch(r"[0-9a-f]{40}", spec.get("revision", "")):
                raise ValueError("Untrusted catalog driver source")
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "packages" and (not isinstance(child, dict) or any(not packages_valid(p) for p in child.values())):
                    raise ValueError("Invalid catalog package names")
                if key == "verify" and child not in ([], ["nvidia-smi", "-L"]):
                    raise ValueError("Untrusted catalog verifier")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(data)
    return data
