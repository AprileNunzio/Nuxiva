#!/usr/bin/env bash
. "$(dirname "$0")/../lib.sh"

BT_PKGS=(bluez pulseaudio-module-bluetooth)
BT_FIRMWARE=(firmware-realtek firmware-iwlwifi firmware-atheros firmware-brcm80211 firmware-mediatek firmware-misc-nonfree linux-firmware)
BT_DRIVER_RE='^(btusb|btsdio|hci_uart|btmtksdio|btnxpuart)$'

bt_enabled() { [ "${NUXIVA_BLUETOOTH:-1}" != "0" ]; }
bt_adapter() { compgen -G "/sys/class/bluetooth/hci*" >/dev/null; }
bt_controller() { timeout 8 bluetoothctl list 2>/dev/null | grep -q '^Controller '; }

bt_rfkill() {
    local dev
    for dev in /sys/class/rfkill/rfkill*; do
        [ "$(cat "$dev/type" 2>/dev/null)" = bluetooth ] || continue
        [ "$(cat "$dev/$1" 2>/dev/null)" = 1 ] && return 0
    done
    return 1
}

bt_unblock() {
    local dev
    rfkill unblock bluetooth 2>/dev/null && return 0
    for dev in /sys/class/rfkill/rfkill*; do
        [ "$(cat "$dev/type" 2>/dev/null)" = bluetooth ] && { echo 0 > "$dev/soft"; } 2>/dev/null || true
    done
    return 0
}

bt_driver() {
    local link drv
    for link in /sys/class/bluetooth/hci*/device/driver; do
        [ -e "$link" ] || continue
        drv=$(basename "$(readlink -f "$link")")
        [[ "$drv" =~ $BT_DRIVER_RE ]] && { echo "$drv"; return 0; }
    done
    return 1
}

bt_kernel_report() {
    dmesg 2>/dev/null | grep -iE 'bluetooth|hci[0-9]|btusb|btrtl|btintel|btmtk' | grep -iE 'fail|error|timeout|firmware|not found' \
        | tail -n 4 | sed 's/^/[bluetooth] /'
}

bt_firmware() {
    local wanted=() pkg
    for pkg in "${BT_FIRMWARE[@]}"; do
        pkgs_present "$pkg" && continue
        apt-cache show "$pkg" >/dev/null 2>&1 && wanted+=("$pkg")
    done
    [ ${#wanted[@]} -gt 0 ] || return 1
    detail "Firmware dell'adattatore: ${wanted[*]}"
    apt_install "${wanted[@]}"
}

bt_reload_driver() {
    local drv
    drv=$(bt_driver) || return 1
    detail "Ricarico il driver $drv"
    modprobe -r "$drv" 2>/dev/null || return 1
    sleep 2
    modprobe "$drv" 2>/dev/null || return 1
    wait_for 15 bt_adapter
}

bt_restart_service() {
    systemctl reset-failed bluetooth >/dev/null 2>&1 || true
    systemctl restart bluetooth >/dev/null 2>&1 || return 1
    wait_for 12 bt_controller
}

bt_recover() {
    bt_controller && return 0
    warn "L'adattatore Bluetooth non risponde: provo a riattivarlo"
    bt_unblock
    bt_restart_service && return 0
    if bt_firmware; then
        bt_reload_driver
        bt_restart_service && return 0
    fi
    bt_reload_driver && bt_unblock && bt_restart_service && return 0
    bt_kernel_report
    return 1
}

kiosk_pactl() {
    local uid
    uid=$(id -u "$NUXIVA_KIOSK_USER" 2>/dev/null) || return 1
    runuser -u "$NUXIVA_KIOSK_USER" -- env "XDG_RUNTIME_DIR=/run/user/$uid" pactl "$@"
}

pulse_ready() {
    kiosk_pactl list short modules 2>/dev/null | grep -q module-bluetooth-discover
}

step_check() {
    bt_enabled || return 0
    bt_adapter || return 0
    pkgs_present "${BT_PKGS[@]}" || return 1
    systemctl is-active --quiet bluetooth || return 1
    id -nG "$NUXIVA_KIOSK_USER" 2>/dev/null | grep -qw bluetooth || return 1
    ! id "$NUXIVA_KIOSK_USER" >/dev/null 2>&1 || pulse_ready
}

step_apply() {
    if ! bt_enabled; then
        progress 100 "Bluetooth disattivato"
        return 0
    fi
    if ! bt_adapter; then
        progress 100 "Nessun adattatore Bluetooth: collega una chiavetta USB e Nuxiva la configurerà"
        return 0
    fi
    progress 20 "Installazione di BlueZ e del supporto audio Bluetooth"
    apt_install "${BT_PKGS[@]}" || fail "Pacchetti Bluetooth non installati"
    progress 50 "Attivazione dell'adattatore"
    mkdir -p /etc/bluetooth
    if [ -f /etc/bluetooth/main.conf ] && ! grep -q '^AutoEnable=true' /etc/bluetooth/main.conf; then
        if grep -q '^\[Policy\]' /etc/bluetooth/main.conf; then
            sed -i '/^\[Policy\]/a AutoEnable=true' /etc/bluetooth/main.conf
        else
            printf '\n[Policy]\nAutoEnable=true\n' >> /etc/bluetooth/main.conf
        fi
    fi
    bt_unblock
    systemctl unmask bluetooth >/dev/null 2>&1 || true
    systemctl enable --now bluetooth || fail "Servizio Bluetooth non avviato"
    if bt_rfkill hard; then
        warn "Bluetooth spento dall'interruttore del computer (tasto modalità aereo o BIOS)"
        progress 100 "Bluetooth spento dall'interruttore del computer: riaccendilo e Nuxiva lo attiverà"
        return 0
    fi
    if ! wait_for 20 bt_controller && ! bt_recover; then
        warn "L'adattatore Bluetooth non ha risposto neanche dopo la riparazione: il resto di Nuxiva funziona normalmente"
        progress 100 "Adattatore Bluetooth non pronto: si accenderà da solo appena risponde, anche dopo un riavvio"
        return 0
    fi
    timeout 8 bluetoothctl power on >/dev/null 2>&1 || warn "Accensione dell'adattatore non confermata"
    progress 75 "Permessi per il display"
    getent group bluetooth >/dev/null || groupadd --system bluetooth
    if id "$NUXIVA_KIOSK_USER" >/dev/null 2>&1; then
        usermod -aG bluetooth "$NUXIVA_KIOSK_USER"
        progress 85 "Collegamento dell'audio Bluetooth"
        pulse_ready || kiosk_pactl load-module module-bluetooth-policy >/dev/null 2>&1 || true
        pulse_ready || kiosk_pactl load-module module-bluetooth-discover >/dev/null \
            || warn "Il modulo audio Bluetooth sarà attivo al prossimo avvio del display"
    fi
    progress 100 "Bluetooth pronto"
}

step_main "$@"
