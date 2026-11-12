import platform
import re


async def ensure_repositories(run, os_info, result):
    family = os_info.family
    if family not in ("fedora", "rhel"):
        result.ok = False
        result.notes.append("Unsupported RPM distribution")
        return result
    release = os_info.version_id if family == "fedora" else str(os_info.major)
    if not re.fullmatch(r"[0-9]{1,3}", release) or release == "0":
        result.ok = False
        result.notes.append("Invalid distribution release")
        return result
    if family == "rhel":
        code, output = await run(["dnf", "install", "-y", "epel-release", "dnf-plugins-core"], timeout=300)
        if code:
            result.ok = False
            result.notes.append(output[-200:])
            return result
        if os_info.distro_id == "rhel":
            architecture = platform.machine()
            if architecture not in ("x86_64", "aarch64", "ppc64le", "s390x"):
                result.ok = False
                result.notes.append("Unsupported repository architecture")
                return result
            command = ["subscription-manager", "repos", "--enable",
                       f"codeready-builder-for-rhel-{release}-{architecture}-rpms"]
        else:
            repository = "powertools" if os_info.major == 8 else "crb"
            command = ["dnf", "config-manager", "--set-enabled", repository]
        code, output = await run(command, timeout=60)
        if code:
            result.ok = False
            result.notes.append(output[-200:])
            return result
        result.changed = True
        result.enabled.extend(["epel", "builder"])
    for kind in ("free", "nonfree"):
        package = f"rpmfusion-{kind}-release"
        code, output = await run(["rpm", "-q", package], timeout=20)
        if code == 0:
            result.already.append(package)
            continue
        distribution = "fedora" if family == "fedora" else "el"
        url = f"https://mirrors.rpmfusion.org/{kind}/{distribution}/{package}-{release}.noarch.rpm"
        code, output = await run(["dnf", "--setopt=localpkg_gpgcheck=1", "install", "-y", url], timeout=300)
        if code:
            result.ok = False
            result.notes.append(f"{package}: {output[-200:]}")
            return result
        result.changed = True
        result.enabled.append(package)
    return result
