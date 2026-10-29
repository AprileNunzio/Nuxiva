import re
from urllib.parse import urlsplit


HOSTS = {"debian": ("debian.org", "debian.net"), "ubuntu": ("ubuntu.com",)}


def official(uri, os_info):
    try:
        parsed = urlsplit(uri)
        host = (parsed.hostname or "").lower()
        return parsed.scheme in ("http", "https") and not parsed.username and not parsed.password and any(
            host == domain or host.endswith("." + domain) for domain in HOSTS.get(os_info.family, ())
        )
    except ValueError:
        return False


def source_lines(text, components, os_info):
    added, lines = [], []
    for line in text.splitlines():
        active, separator, comment = line.partition("#")
        tokens = active.split()
        if not tokens or tokens[0] not in ("deb", "deb-src"):
            lines.append(line)
            continue
        if any(option in active.lower() for option in ("trusted=yes", "allow-insecure=yes", "allow-weak=yes")):
            lines.append(line)
            continue
        index = 1
        if index < len(tokens) and tokens[index].startswith("["):
            while index < len(tokens) and not tokens[index].endswith("]"):
                index += 1
            index += 1
        if len(tokens) < index + 3 or not official(tokens[index], os_info) or "main" not in tokens[index + 2:]:
            lines.append(line)
            continue
        missing = [c for c in components if c not in tokens[index + 2:]]
        if missing:
            line = " ".join(tokens + missing) + (" #" + comment if separator else "")
            added.extend(c for c in missing if c not in added)
        lines.append(line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else ""), added


def fields(stanza):
    result, current = {}, ""
    for line in stanza.splitlines():
        if line.startswith("#"):
            continue
        if line[:1].isspace() and current:
            result[current] += " " + line.strip()
        elif ":" in line:
            key, value = line.split(":", 1)
            current = key.lower()
            result[current] = value.strip()
    return result


def trusted_stanza(stanza, os_info):
    data = fields(stanza)
    if any(data.get(option, "no").lower() == "yes" for option in ("trusted", "allow-insecure", "allow-weak")):
        return False
    uris = data.get("uris", "").split()
    return data.get("enabled", "yes").lower() != "no" and "deb" in data.get("types", "").split() and bool(uris) and all(
        official(uri, os_info) for uri in uris
    )


def deb822(text, components, os_info):
    added, result = [], []
    for stanza in re.split(r"\n\s*\n", text.strip("\n")):
        data = fields(stanza)
        missing = [c for c in components if c not in data.get("components", "").split()]
        if trusted_stanza(stanza, os_info) and "main" in data.get("components", "").split() and missing:
            lines, replacing = [], False
            for line in stanza.splitlines():
                if line.lower().startswith("components:"):
                    lines.append("Components: " + " ".join(data["components"].split() + missing))
                    replacing = True
                elif replacing and line[:1].isspace():
                    continue
                else:
                    replacing = False
                    lines.append(line)
            stanza = "\n".join(lines)
            added.extend(c for c in missing if c not in added)
        result.append(stanza)
    return "\n\n".join(result) + ("\n" if text.endswith("\n") else ""), added


def active_components(text, suffix, os_info):
    if suffix == ".sources":
        return {c for stanza in re.split(r"\n\s*\n", text) if trusted_stanza(stanza, os_info)
                for c in fields(stanza).get("components", "").split()}
    result = set()
    for line in text.splitlines():
        clean = line.partition("#")[0]
        tokens = clean.split()
        if tokens and tokens[0] == "deb" and not any(option in clean.lower() for option in ("trusted=yes", "allow-insecure=yes", "allow-weak=yes")) and any(official(t, os_info) for t in tokens):
            result.update(tokens)
    return result
