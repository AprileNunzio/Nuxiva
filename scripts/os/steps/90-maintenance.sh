#!/usr/bin/env bash
. "$(dirname "$0")/../lib.sh"

AUTO_UPGRADES=/etc/apt/apt.conf.d/20auto-upgrades
JOURNAL_CONF=/etc/systemd/journald.conf.d/nuxiva.conf
LOGROTATE=/etc/logrotate.d/nuxiva
CTL=/usr/local/bin/nuxivactl

auto_upgrades() {
    printf '%s\n' \
        '// Gestito da Nuxiva OS: aggiornamenti di sicurezza automatici' \
        'APT::Periodic::Update-Package-Lists "1";' \
        'APT::Periodic::Unattended-Upgrade "1";' \
        'APT::Periodic::AutocleanInterval "7";'
}

journal_conf() {
    printf '%s\n' '# Gestito da Nuxiva OS' '[Journal]' 'SystemMaxUse=500M' 'MaxRetentionSec=1month'
}

logrotate_conf() {
    printf '%s\n' \
        '/var/log/nuxiva/*.log {' \
        '    weekly' \
        '    rotate 8' \
        '    maxsize 50M' \
        '    compress' \
        '    missingok' \
        '    notifempty' \
        '    copytruncate' \
        '}'
}

step_check() {
    auto_upgrades | same_content "$AUTO_UPGRADES" \
        && journal_conf | same_content "$JOURNAL_CONF" \
        && logrotate_conf | same_content "$LOGROTATE" \
        && [ "$(readlink -f "$CTL")" = "$NUXIVA_DIR/scripts/os/nuxivactl" ] && [ -x "$CTL" ]
}

step_apply() {
    progress 30 "Aggiornamenti di sicurezza automatici"
    apt_install unattended-upgrades
    auto_upgrades | write_if_changed "$AUTO_UPGRADES" || true
    progress 60 "Limiti del journal di sistema"
    if journal_conf | write_if_changed "$JOURNAL_CONF"; then
        systemctl restart systemd-journald || true
    fi
    progress 85 "Rotazione dei log Nuxiva"
    logrotate_conf | write_if_changed "$LOGROTATE" || true
    chmod +x "$NUXIVA_DIR/scripts/os/nuxivactl" "$NUXIVA_DIR/scripts/os/force-upgrade.sh"
    ln -sfn "$NUXIVA_DIR/scripts/os/nuxivactl" "$CTL"
    ln -sfn "$NUXIVA_DIR/scripts/os/force-upgrade.sh" /usr/local/bin/nuxiva-upgrade
    progress 100 "Manutenzione autonoma attiva (comandi nuxivactl e nuxiva-upgrade disponibili)"
}

step_main "$@"
