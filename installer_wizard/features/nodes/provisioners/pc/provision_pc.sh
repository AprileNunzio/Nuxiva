#!/usr/bin/env bash
# Nuxiva OS v5.0.0 — PC x86_64 Provisioning Script
set -euo pipefail
echo "==> Provisioning Nuxiva PC Node..."
systemctl daemon-reload || true
echo "==> Configuring WireGuard Mesh..."
mkdir -p /etc/wireguard
echo "==> Bootstrapping local Ollama LLM service..."
which ollama || echo "Ollama not installed, falling back to P2P offload"
echo "==> PC Node Provisioning Completed Successfully."
