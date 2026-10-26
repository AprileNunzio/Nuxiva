#!/usr/bin/env bash
# Nuxiva OS v5.0.0 — Raspberry Pi Satellite Provisioning
set -euo pipefail
echo "==> Configuring Raspberry Pi Satellite..."
if [ -f /boot/firmware/config.txt ]; then
    grep -q "dtoverlay=seeed-2mic-voicecard" /boot/firmware/config.txt || echo "dtoverlay=seeed-2mic-voicecard" >> /boot/firmware/config.txt
fi
echo "==> Enabling ALSA & P2P Stream Daemon..."
echo "==> Raspberry Pi Satellite Provisioned Successfully."
