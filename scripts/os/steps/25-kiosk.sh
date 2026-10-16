#!/usr/bin/env bash
. "$(dirname "$0")/../lib.sh"

USER_NAME="$NUXIVA_KIOSK_USER"
GETTY_OVERRIDE=/etc/systemd/system/getty@tty1.service.d/override.conf
POLICY=/etc/chromium/policies/managed/nuxiva.json
SESSION="$NUXIVA_DIR/scripts/os/kiosk/session.sh"
LAUNCH="$NUXIVA_DIR/scripts/os/kiosk/launch.sh"
XWRAPPER=/etc/X11/Xwrapper.config

kiosk_enabled() { [ "${NUXIVA_KIOSK:-1}" != "0" ]; }
user_home() { getent passwd "$USER_NAME" | cut -d: -f6; }

getty_conf() {
    printf '%s\n' \
        '# Gestito da Nuxiva OS' \
        '[Service]' \
        'ExecStart=' \
        "ExecStart=-/sbin/agetty --autologin $USER_NAME --noclear %I \$TERM" \
        'Restart=always' \
        'RestartSec=2'
}

bash_profile() {
    printf '%s\n' \
        '# Gestito da Nuxiva OS: avvia la sessione grafica kiosk su tty1' \
        'if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then' \
        "    exec /bin/bash $LAUNCH" \
        'fi'
}

chromium_policy() {
    printf '%s\n' \
        '{' \
        '  "TranslateEnabled": false,' \
        '  "PasswordManagerEnabled": false,' \
        '  "AutofillAddressEnabled": false,' \
        '  "AutofillCreditCardEnabled": false,' \
        '  "BrowserSignin": 0,' \
        '  "SyncDisabled": true,' \
        '  "DefaultBrowserSettingEnabled": false,' \
        '  "PromotionalTabsEnabled": false,' \
        '  "MetricsReportingEnabled": false,' \
        '  "SpellcheckEnabled": false,' \
        '  "DefaultNotificationsSetting": 2,' \
        '  "DefaultGeolocationSetting": 1,' \
        '  "AutoplayAllowed": true,' \
        '  "AudioCaptureAllowed": true,' \
        '  "AudioCaptureAllowedUrls": ["http://127.0.0.1", "http://localhost"],' \
        '  "VideoCaptureAllowed": false,' \
        '  "ApplicationLocaleValue": "it"' \
        '}'
}

xwrapper_conf() {
    printf '%s\n' \
        '# Gestito da Nuxiva OS' \
        'allowed_users=anybody' \
        'needs_root_rights=yes'
}

legacy_root_session() {
    grep -qs 'startx' /root/.bash_profile
}

step_check() {
    kiosk_enabled || return 0
    id "$USER_NAME" >/dev/null 2>&1 || return 1
    getty_conf | same_content "$GETTY_OVERRIDE" || return 1
    bash_profile | same_content "$(user_home)/.bash_profile" || return 1
    [ -x "$SESSION" ] && [ -x "$LAUNCH" ] || return 1
    xwrapper_conf | same_content "$XWRAPPER" || return 1
    chromium_policy | same_content "$POLICY" || return 1
    code_current kiosk "$SESSION" "$LAUNCH" || return 1
    ! legacy_root_session
}

step_apply() {
    if ! kiosk_enabled; then
        progress 100 "Kiosk disabilitato da configurazione"
        return 0
    fi
    progress 15 "Creazione utente kiosk dedicato"
    if ! id "$USER_NAME" >/dev/null 2>&1; then
        useradd --create-home --shell /bin/bash --comment "Nuxiva Kiosk" "$USER_NAME"
        passwd -l "$USER_NAME" >/dev/null
    fi
    local group
    for group in tty video audio input render; do
        getent group "$group" >/dev/null && usermod -aG "$group" "$USER_NAME"
    done

    progress 40 "Configurazione sessione grafica"
    chmod +x "$SESSION" "$LAUNCH"
    xwrapper_conf | write_if_changed "$XWRAPPER" 0644 && changed=1
    local home changed=0
    home=$(user_home)
    mkdir -p "$home/.cache"
    bash_profile | write_if_changed "$home/.bash_profile" 0644 && changed=1
    chown -R "$USER_NAME:$USER_NAME" "$home"

    progress 60 "Rimozione sessione legacy di root"
    if legacy_root_session; then
        sed -i '/startx/d' /root/.bash_profile
        [ -f /root/.xinitrc ] && mv -f /root/.xinitrc /root/.xinitrc.nuxiva-legacy
        changed=1
    fi

    progress 70 "Criteri di Chromium (niente traduttore né popup)"
    if chromium_policy | write_if_changed "$POLICY" 0644; then changed=1; fi

    progress 80 "Autologin su tty1"
    getty_conf | write_if_changed "$GETTY_OVERRIDE" && changed=1
    code_current kiosk "$SESSION" "$LAUNCH" || changed=1
    systemctl daemon-reload
    systemctl set-default multi-user.target >/dev/null 2>&1 || true

    if [ "$changed" -eq 1 ]; then
        info "Riavvio della console tty1 per attivare il kiosk"
        pkill -t tty1 >/dev/null 2>&1 || true
        sleep 1
        systemctl restart getty@tty1 || true
    fi
    code_mark kiosk "$SESSION" "$LAUNCH"
    progress 100 "Display kiosk configurato (una finestra per ogni monitor collegato)"
}

step_main "$@"
