#!/usr/bin/env bash
. "$(dirname "$0")/lib.sh"
set +e

step=${1:-generic}
info "Diagnosi e riparazione per lo step: $step"

case "$step" in
    system|gpu|security|maintenance|docker) need_apt=1 ;;
    *) need_apt=0 ;;
esac
if [ -n "$(dpkg --audit 2>/dev/null)" ]; then need_apt=1; fi
if [ "$need_apt" -eq 1 ] && ! pgrep -x apt-get >/dev/null && ! pgrep -x dpkg >/dev/null; then
    apt_heal
fi

free_mb=$(df -Pm / | awk 'NR==2 {print $4}')
if [ "${free_mb:-0}" -lt 4096 ]; then
    warn "Spazio disco basso (${free_mb} MB): pulizia"
    apt-get clean
    journalctl --vacuum-size=200M >/dev/null 2>&1
    command -v docker >/dev/null && docker system prune -f >/dev/null 2>&1
fi

if ! curl -fsS --max-time 8 -o /dev/null https://github.com; then
    warn "Rete non raggiungibile: riavvio risoluzione DNS"
    systemctl restart systemd-resolved >/dev/null 2>&1 || true
    sleep 5
fi

if [ -f /etc/nuxiva/nuxiva.env ]; then
    python3 -c '
from pathlib import Path
import re
p = Path("/etc/nuxiva/nuxiva.env")
if p.exists():
    out = []
    seen = set()
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            out.append(line)
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip().strip("\"").strip("\x27").strip()
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", k) or k in seen:
                continue
            seen.add(k)
            v = v.strip()
            while len(v) >= 2 and ((v.startswith("\"") and v.endswith("\"")) or (v.startswith("\x27") and v.endswith("\x27"))):
                v = v[1:-1].strip()
            escaped = v.replace("\\", "\\\\").replace("\"", "\\\"")
            out.append(f"{k}=\"{escaped}\"")
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
' 2>/dev/null || true
fi

case "$step" in
    docker|core|services|gpu)
        if command -v docker >/dev/null && ! docker info >/dev/null 2>&1; then
            warn "Docker non risponde: riavvio"
            systemctl restart docker
            sleep 5
        fi
        ;;
    ollama|models|warmup)
        if systemctl list-unit-files ollama.service >/dev/null 2>&1; then
            warn "Diagnosi e ripristino del motore neurale Ollama"
            getent group ollama >/dev/null || groupadd -r ollama 2>/dev/null || true
            id -u ollama >/dev/null 2>&1 || useradd -r -g ollama -s /bin/false -m -d /usr/share/ollama ollama 2>/dev/null || true
            mkdir -p /usr/share/ollama/.ollama/models
            chown -R ollama:ollama /usr/share/ollama 2>/dev/null || true
            chmod 755 /usr/share/ollama 2>/dev/null || true
            systemctl daemon-reload
            systemctl restart ollama
            sleep 4
            if ! curl -fsS --max-time 3 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
                journalctl -u ollama -n 15 --no-pager 2>/dev/null || true
            fi
        fi
        ;;
esac
info "Riparazione completata"
