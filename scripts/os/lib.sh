#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export LC_ALL=C.UTF-8

NUXIVA_DIR="${NUXIVA_DIR:-/opt/Nuxiva}"
NUXIVA_ETC="${NUXIVA_ETC:-/etc/nuxiva}"
NUXIVA_STATE="${NUXIVA_STATE:-/var/lib/nuxiva}"
NUXIVA_ENV_FILE="$NUXIVA_ETC/nuxiva.env"
NUXIVA_KIOSK_USER="${NUXIVA_KIOSK_USER:-nuxiva-kiosk}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
CORE_URL="${CORE_URL:-http://127.0.0.1:8443}"

load_env_file() {
    local file="$1" line key val
    [ -f "$file" ] || return 0
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%$'\r'}"
        case "$line" in ""|\#* ) continue ;; *=*) ;; *) continue ;; esac
        key="${line%%=*}"
        val="${line#*=}"
        key="${key#"${key%%[![:space:]]*}"}"
        key="${key%"${key##*[![:space:]]}"}"
        [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
        val="${val#"${val%%[![:space:]]*}"}"
        val="${val%"${val##*[![:space:]]}"}"
        if [[ "$val" =~ ^\"(.*)\"$ ]]; then
            val="${BASH_REMATCH[1]}"
        elif [[ "$val" =~ ^\'(.*)\'$ ]]; then
            val="${BASH_REMATCH[1]}"
        fi
        export "$key=$val"
    done < "$file"
}

load_env_file "$NUXIVA_ENV_FILE"

if [ -n "${NUXIVA_OLLAMA_URL:-}" ]; then
    OLLAMA_URL="${NUXIVA_OLLAMA_URL%/}"
    case "$OLLAMA_URL" in http://*|https://*) ;; *) OLLAMA_URL="http://$OLLAMA_URL" ;; esac
    case "${OLLAMA_URL#*//}" in *:*) ;; *) OLLAMA_URL="$OLLAMA_URL:11434" ;; esac
fi

ollama_remote() {
    local host="${OLLAMA_URL#*//}"
    host="${host%%:*}"
    case "$host" in 127.0.0.1|localhost|"") return 1 ;; *) return 0 ;; esac
}

truthy() { case "${1,,}" in 1|true|yes|on|si|sì) return 0 ;; *) return 1 ;; esac; }
commercial() { truthy "${NUXIVA_COMMERCIAL:-0}"; }
unofficial_ok() { truthy "${NUXIVA_UNOFFICIAL_SERVICES:-0}"; }

progress() { echo "@@PROGRESS $1 ${*:2}"; }
detail()   { echo "@@DETAIL $*"; }
speed()    { echo "@@SPEED $*"; }
info()     { echo "[INFO] $*"; }
warn()     { echo "[WARN] $*"; }
fail()     { echo "[FAIL] $*"; exit 1; }

download_file() {
    local target=$1 url=$2 label=${3:-$(basename "$target")} base_pct=${4:-0} span_pct=${5:-100}
    mkdir -p "$(dirname "$target")"
    local tmp="${target}.part"
    if command -v python3 >/dev/null 2>&1; then
        python3 - "$url" "$tmp" "$target" "$label" "$base_pct" "$span_pct" <<'PY' && return 0
import os, sys, time, urllib.request

url, tmp, target, label = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
base_pct, span_pct = int(sys.argv[5]), int(sys.argv[6])

def fmt_size(n):
    if n >= 1e9: return f"{n / 1e9:.2f} GB"
    if n >= 1e6: return f"{n / 1e6:.1f} MB"
    if n >= 1e3: return f"{n / 1e3:.0f} KB"
    return f"{n} B"

req = urllib.request.Request(url, headers={"User-Agent": "Nuxiva/1.0"})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        last_t = time.time()
        last_bytes = 0
        last_emit = 0.0
        with open(tmp, "wb") as out:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                now = time.time()
                if now - last_emit >= 0.5 or (total and done == total):
                    dt = max(now - last_t, 0.001)
                    spd = max(0, (done - last_bytes) / dt)
                    spd_str = f"{fmt_size(spd)}/s"
                    if total > 0:
                        pct = min(100, int(done * 100 / total))
                        eta_s = int((total - done) / spd) if spd > 0 else 0
                        eta_str = f"{eta_s // 60}m{eta_s % 60:02d}s"
                        prog = base_pct + int(pct * span_pct / 100)
                        print(f"@@PROGRESS {prog} Download {label}: {pct}%", flush=True)
                        print(f"@@DETAIL {label} — {fmt_size(done)}/{fmt_size(total)} — {spd_str} — ETA {eta_str}", flush=True)
                    else:
                        print(f"@@DETAIL {label} — {fmt_size(done)} — {spd_str}", flush=True)
                    print(f"@@SPEED {spd_str}", flush=True)
                    last_emit, last_bytes, last_t = now, done, now
    os.replace(tmp, target)
except Exception as e:
    if os.path.exists(tmp):
        try: os.remove(tmp)
        except OSError: pass
    print(f"[FAIL] Download {label} fallito: {e}", flush=True)
    sys.exit(1)
PY
    fi
    progress "$base_pct" "Download $label..."
    curl -fL --progress-bar -o "$tmp" "$url" || { rm -f "$tmp"; return 1; }
    mv -f "$tmp" "$target"
    progress "$((base_pct + span_pct))" "$label pronto"
}

retry() {
    local attempts=$1 delay=$2 i
    shift 2
    for ((i = 1; i <= attempts; i++)); do
        "$@" && return 0
        if [ "$i" -lt "$attempts" ]; then
            warn "Tentativo $i/$attempts fallito: $*. Nuovo tentativo tra ${delay}s"
            sleep "$delay"
            delay=$((delay * 2))
        fi
    done
    return 1
}

wait_for() {
    local timeout=$1 t=0
    shift
    until "$@" >/dev/null 2>&1; do
        t=$((t + 2))
        [ "$t" -ge "$timeout" ] && return 1
        sleep 2
    done
}

apt_heal() {
    warn "Auto-riparazione del gestore pacchetti…"
    rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock 2>/dev/null || true
    dpkg --configure -a || true
    apt-get -f install -y -q || true
}

pkgs_present() {
    local p
    for p in "$@"; do
        dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "install ok installed" || return 1
    done
}

apt_install() {
    local missing=() p
    for p in "$@"; do
        pkgs_present "$p" || missing+=("$p")
    done
    [ ${#missing[@]} -eq 0 ] && return 0
    info "Pacchetti da installare: ${missing[*]}"
    retry 3 5 apt-get update -q || { apt_heal; apt-get update -q; }
    if ! retry 2 5 apt-get install -y -q --no-install-recommends "${missing[@]}"; then
        apt_heal
        apt-get install -y -q --no-install-recommends "${missing[@]}"
    fi
}

set_env() {
    local key=$1 value=$2
    mkdir -p "$NUXIVA_ETC"
    touch "$NUXIVA_ENV_FILE"
    chmod 600 "$NUXIVA_ENV_FILE"
    python3 -c '
import sys, re
from pathlib import Path
k, v, f = sys.argv[1], sys.argv[2], Path(sys.argv[3])
lines = f.read_text(encoding="utf-8", errors="ignore").splitlines() if f.exists() else []
out = []
found = False
while len(v) >= 2 and ((v.startswith("\"") and v.endswith("\"")) or (v.startswith("\x27") and v.endswith("\x27"))):
    v = v[1:-1].strip()
esc = v.replace("\\", "\\\\").replace("\"", "\\\"")
formatted = f"{k}=\"{esc}\""
for line in lines:
    stripped = line.strip()
    if not stripped:
        continue
    if stripped.startswith("#"):
        out.append(stripped)
        continue
    if "=" in stripped:
        cur_k, cur_v = stripped.split("=", 1)
        cur_k = cur_k.strip().strip("\"'\t ")
        if cur_k == k:
            found = True
            out.append(formatted)
        elif re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", cur_k):
            out.append(line)
if not found:
    out.append(formatted)
f.write_text("\n".join(out) + "\n", encoding="utf-8")
' "$key" "$value" "$NUXIVA_ENV_FILE" 2>/dev/null || echo "${key}=\"${value}\"" >> "$NUXIVA_ENV_FILE"
    export "$key=$value"
}

write_if_changed() {
    local path=$1 mode=${2:-0644} tmp
    tmp=$(mktemp)
    cat > "$tmp"
    if [ -f "$path" ] && cmp -s "$tmp" "$path"; then
        rm -f "$tmp"
        return 1
    fi
    install -D -m "$mode" "$tmp" "$path"
    rm -f "$tmp"
    return 0
}

same_content() {
    local tmp rc=0
    tmp=$(mktemp)
    cat > "$tmp"
    [ -f "$1" ] && cmp -s "$tmp" "$1" || rc=1
    rm -f "$tmp"
    return $rc
}

_code_hash() { cat "$@" 2>/dev/null | sha1sum | cut -c1-16; }
code_current() { local name=$1; shift; [ "$(cat "$NUXIVA_STATE/.code-$name" 2>/dev/null)" = "$(_code_hash "$@")" ]; }
code_mark() { local name=$1; shift; mkdir -p "$NUXIVA_STATE"; _code_hash "$@" > "$NUXIVA_STATE/.code-$name"; }

compose() {
    docker compose \
        --project-name nuxiva \
        --project-directory "$NUXIVA_DIR/docker" \
        -f "$NUXIVA_DIR/docker/docker-compose.yml" \
        --env-file "$NUXIVA_ENV_FILE" "$@"
}

has_nvidia_gpu() {
    command -v lspci >/dev/null 2>&1 && lspci | grep -qiE '(vga|3d).*nvidia'
}

has_usable_gpu() {
    command -v nvidia-smi >/dev/null 2>&1 || return 1
    local info cap vram
    info=$(nvidia-smi --query-gpu=compute_cap,memory.total --format=csv,noheader,nounits 2>/dev/null | head -1) || return 1
    cap=$(echo "$info" | cut -d, -f1 | tr -d ' ')
    vram=$(echo "$info" | cut -d, -f2 | tr -d ' ')
    [ -n "$cap" ] && [ -n "$vram" ] || return 1
    awk -v c="$cap" -v v="$vram" 'BEGIN { exit !(c + 0 >= 5.0 && v + 0 >= 4000) }'
}

hw_profile() { if has_usable_gpu; then echo gpu; else echo cpu; fi; }

ram_mb() { awk '/MemTotal/ {printf "%d", $2 / 1024}' /proc/meminfo; }
board_model() { [ -r /proc/device-tree/model ] && tr -d '\0' < /proc/device-tree/model || true; }

machine_class() {
    local ram
    ram=$(ram_mb)
    if board_model | grep -qi raspberry; then echo pi
    elif [ "$ram" -lt 7680 ]; then echo small
    elif has_usable_gpu || [ "$ram" -ge 28672 ]; then echo powerful
    else echo standard
    fi
}

core_runtime() {
    case "${NUXIVA_CORE_RUNTIME:-}" in native|docker) echo "$NUXIVA_CORE_RUNTIME"; return 0 ;; esac
    case "${NUXIVA_MACHINE:-$(machine_class)}" in pi|small) echo native ;; *) echo docker ;; esac
}
native_core() { [ "$(core_runtime)" = native ]; }
docker_needed() {
    native_core || return 0
    case "${NUXIVA_SANDBOX:-0}" in 1|on|yes|true|auto) return 0 ;; *) return 1 ;; esac
}

core_src_hash() {
    (
        cd "$NUXIVA_DIR"
        git -c safe.directory='*' rev-parse HEAD:server HEAD:docker/core 2>/dev/null | sha1sum | cut -c1-16
    )
}

step_main() {
    case "${1:-}" in
        check) step_check ;;
        apply) step_apply ;;
        *) echo "Uso: $0 check|apply" >&2; exit 2 ;;
    esac
}
