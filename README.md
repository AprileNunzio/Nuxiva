<div align="center">

# NUXIVA

**A self-hosted, local-first home and work assistant that runs on your own hardware.**

Voice, vision, home automation, agents and tools in one modular platform. Local language models by default, cloud models only when you add them.

[🇬🇧 English](README.md) · [🇮🇹 Italiano](README_IT.md) · [🇫🇷 Français](README_FR.md) · [🇪🇸 Español](README_ES.md)

[![CI](https://github.com/AprileNunzio/Nuxiva/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/AprileNunzio/Nuxiva/actions/workflows/ci.yml)
![Platform](https://img.shields.io/badge/platform-Debian%20%7C%20Ubuntu-0A1A2F)
![Arch](https://img.shields.io/badge/arch-x86__64%20%7C%20arm64-0A1A2F)
[![License](https://img.shields.io/badge/license-Nuxiva%20Personal%20%26%20Commercial-0A1A2F)](LICENSE)

<img src=".github/readme/display-home.webp" alt="Nuxiva home display" width="100%">

</div>

---

## Contents

1. [Overview](#1-overview)
2. [Screenshots](#2-screenshots)
3. [Capabilities](#3-capabilities)
4. [Architecture](#4-architecture)
5. [Security model](#5-security-model)
6. [Installation](#6-installation)
7. [Operations](#7-operations)
8. [Configuration](#8-configuration)
9. [Extending Nuxiva](#9-extending-nuxiva)
10. [Engineering standards](#10-engineering-standards)
11. [Project](#11-project)

---

## 1. Overview

Nuxiva turns a Linux machine, or a small group of machines, into a private assistant for the household and the workplace. Everything it needs runs on hardware you own: speech recognition, speech synthesis, face recognition, language models, automations and storage. Nothing leaves the network unless you connect an external service on purpose.

Design principles:

| Principle | What it means in practice |
| :--- | :--- |
| **Local first** | Language models run through Ollama on the host or on a node you control. Cloud providers are optional and sit in the same priority list as local models. |
| **Modular** | Every capability is a self-describing module that the supervisor discovers at start-up. Adding a module requires no central registration. |
| **Adaptive to hardware** | Features that need a camera, a microphone or a GPU enable themselves only when that hardware is present and fast enough. |
| **Secure by default** | Admin access through Linux PAM, approval gates for risky actions, sandboxed execution of generated code, an allow-listed egress proxy and hardened systemd units. |
| **Self-maintaining** | Staged installation, CI-gated updates, automatic rollback, nightly self-tests and a safe-mode recovery page. |
| **Multilingual** | The interfaces are localised in English, Italian, French and Spanish, and the assistant answers in the language it is spoken to. |

---

## 2. Screenshots

All screenshots are taken from an unmodified build of the `main` branch.

| | |
| :---: | :---: |
| <img src=".github/readme/setup-wizard.webp" alt="First-run setup wizard"><br>**First-run setup wizard** | <img src=".github/readme/admin-control-panel.webp" alt="Admin control panel"><br>**Admin desktop: control panel** |
| <img src=".github/readme/admin-brain.webp" alt="Brain: model routing"><br>**Brain: model routing and profiles** | <img src=".github/readme/admin-applications.webp" alt="Applications"><br>**Applications launcher** |
| <img src=".github/readme/admin-network.webp" alt="Network and nodes"><br>**Network, devices and nodes** | <img src=".github/readme/admin-studio-3d.webp" alt="3D studio"><br>**3D studio** |
| <img src=".github/readme/display-widgets.webp" alt="Widget display on desktop and mobile"><br>**Widget display on desktop and mobile** | <img src=".github/readme/admin-mcp-tools.webp" alt="MCP tools: servers, consents and verifiable log"><br>**MCP tools: servers, consents and verifiable log** |

<p align="center"><img src=".github/readme/display-mobile.webp" alt="Widgets of the display on mobile" width="280"><br><b>Widgets of the display on mobile</b></p>

---

## 3. Capabilities

Capabilities are grouped by area. Each area is made of independent modules under `installer_wizard/features/`; the list of modules grows over time, so this section describes what each area covers rather than enumerating every module.

### Conversation and voice
Offline wake word and speech recognition, neural speech synthesis in many languages, speaker recognition, continuous conversation, voice cloning and voice design, automatic media ducking while the user speaks, and remote text, voice and photo chat through messaging bridges.

### Models and reasoning
A single priority list that mixes local Ollama models with optional cloud providers (OpenAI-compatible endpoints included) and falls back automatically when a model fails. Per-task model routing, privacy profiles, usage limits, a fast path for requests that were already confirmed, a library of verified algorithms, and an idle-time study loop that feeds what it learns back into answers.

### Agents and automation
A tool-using agent that plans step by step and asks for confirmation before risky actions; a team of specialist agents selected by relevance; a project agency that turns a request into a planned task graph executed by parallel agents in an isolated workspace; background tasks that survive restarts; scheduled autonomy with human approval for sensitive actions; and a forge that composes new tools, widgets and modules.

### Home and environment
Home Assistant integration (rooms, floors, devices, presence), an automation engine with triggers, conditions, branches, loops, parallel steps and run traces, habit detection, a digital twin that simulates commands before execution, emergency alerting, floor and room mapping, location, weather and maps.

### People, vision and security
Per-person profiles with private data shown only to the recognised person, local face recognition, camera management with live view and per-camera sensors, NVR event archive with natural-language search, hand-gesture control, a network explorer, a firewall fed by native packet analysis, multi-protocol VPN management, an encrypted vault, verifiable backups and a guarded factory reset.

### Display, media and creativity
A widget desktop where information appears when it is relevant, a display director that arranges screens across devices, a kiosk mode, an animated assistant presence, media playback with casting, IPTV, live sports, a music studio, a shared whiteboard, 3D model generation and viewing, 3D scene composition and games.

### Work and productivity
Per-person Google account linking (calendar, mail, tasks, contacts, Drive), office document generation (Word, Excel, PowerPoint, OpenDocument, PDF), a software development studio with isolated test runs, protected network shares, printers and CNC devices, repair-bench integration and Proxmox management.

### System and maintenance
Service supervision with backoff and stall detection, cron-style scheduling with catch-up, a resource governor that defers background work under load, hardware and driver management, Bluetooth and audio device management, multi-node pairing and control, system logs with protected export, and a modular store for optional capabilities.

### Clients
| Client | Path | Role |
| :--- | :--- | :--- |
| Web | `client_web/` | Admin desktop on port 8080 (React, TypeScript, Vite, Tailwind) |
| Display | `installer_wizard/web/` | Kiosk display, setup wizard and activation pages on port 80 |
| Android | `client_apk/` | Wake word, voice match, camera stream, server discovery, health data from BLE devices and Health Connect |
| Windows | `client_satellite/windows_assistant/` | Desktop assistant with voice or hotkey activation, permission-gated file and app control, signed updates |
| Edge | `client_satellite/linux_edge/`, `client_satellite/microcontrollers/` | Linux edge nodes and ESP32 satellites |
| Context bridge | `client_satellite/context_bridge/` | Desktop sensor bridge |

---

## 4. Architecture

```mermaid
flowchart LR
    subgraph Clients
        D[Display :80]
        W[Admin desktop :8080]
        M[Android / Windows / Edge]
    end
    subgraph Host
        S[Supervisor<br/>FastAPI]
        F[(Feature modules)]
        C[Core<br/>routing and reasoning]
        N[Native Rust services]
        X[Sandbox broker]
        O[Ollama]
    end
    CL[(Optional cloud models)]
    D --> S
    W --> S
    M --> S
    S --> F
    F --> C
    F --> O
    F -.-> CL
    C --> O
    F --> X
    S --> N
    X --> N
```

| Component | Path | Technology | Responsibility |
| :--- | :--- | :--- | :--- |
| Supervisor | `installer_wizard/backend/` | Python, FastAPI, Uvicorn | Installation, lifecycle, HTTP and WebSocket APIs, authentication, updates, module discovery |
| Feature modules | `installer_wizard/features/` | Python | Capabilities: routes, voice and chat commands, agent tools, translations |
| Widgets | `installer_wizard/agenti/<category>/<agent>/widget/` | JavaScript, CSS | Plain-language display widgets, shipped inside each agent |
| Core | `server/` | Python | Request routing, reasoning engines, decision engine, plasticity, event sourcing, skill generation |
| Native layer | `native/crates/` | Rust (edition 2024) | Performance- and security-critical code, exposed to Python through PyO3 |
| Sandbox broker | `sandbox_broker/` | Python, Rust | Isolated execution of generated code, egress control |
| Installer | `scripts/os/` | Bash, systemd | Bootstrap, installation steps, units, `nuxivactl` |
| Web client | `client_web/` | React, TypeScript | Admin desktop |

### 4.1 Request flow

A text or voice request is handled by the chat router in `installer_wizard/agenti/cognizione/chat/`. It passes through an ordered chain of stages (automations, direct commands, intent skills, connectors, home control, actions, conversation). The first stage that recognises the request answers it; the others are skipped. Requests that need current information are delegated to the agent, which searches before it answers. Generation walks the model priority list and skips any model that fails, so one unavailable model never blocks an answer.

### 4.2 Core reasoning, Active Inference and Gödelian self-improvement

The Core (`server/core/`) and the native Rust cognitive crates (`native/crates/agency-thought/`, `native/crates/agency-forge/`, `native/crates/reflex-core/`) implement a dual-system neuro-symbolic architecture grounded in computational neuroscience:

```mermaid
flowchart TD
    In["Request / Sensory Event"] --> R1{"System 1: Reflex Core (Rust)\nFormal Oracle & Plasticity Memory"}
    R1 -- "Guarantee >= 0.82 (0 Tokens, <1ms)" --> OutFast["Instant Response / Action"]
    R1 -- "Cache Miss" --> Epistemic["Epistemic & Socratic Engine (VOI)\nLocal self-probing before asking the user"]
    Epistemic --> EFE["Minimal Expected Free Energy (EFE) Policy\nBalances Pragmatic Value vs Epistemic Gain"]
    EFE --> Exec["Multi-Agent / Parallel DAG Execution"]
    Exec --> Check{"Outcome?"}
    Check -- "Runtime Failure" --> Heal["Self-Healing Governor & Tool Forge\nAST Guard + Deterministic Sandbox Verification (fnv64)"]
    Heal --> Exec
    Check -- "Confirmed Success" --> Distill["Shortcut Compiler & Gödelian Upgrade\nZero-Token Reflex Promotion via Pareto Dominance"]
    Distill --> OutFast
```

- **Active Epistemic Inquiry and VOI Scoring (`agency-thought/src/socratic/inquiry.rs`)**: before interrupting the user with clarification questions, Nuxiva computes the mathematical *Value of Information* (`VOI` in basis points) of open hypotheses and schedules local self-inspection probes (`Filesystem`, `CodeIndex`, `NetworkDiscovery`, `MemoryGraph`, `EnvironmentConfig`). Only high-impact, irreversible decisions are escalated to the user.
- **Active Inference & Intrinsic Goal Generation (`agency-thought/src/agi/mod.rs`)**: on every state-action transition (`WorldTransition`), the kernel compares the predicted outcome against the observed state, measures Bayesian surprise (`surprise_bps`) and epistemic uncertainty, and autonomously spawns an `IntrinsicGoal` when surprise exceeds the threshold. Policies are selected by minimising *Expected Free Energy*, balancing pragmatic utility, information gain, latency and token cost.
- **Pareto-Dominant Gödelian Self-Improvement (`AutonomousAgiKernel::evaluate_godel_upgrade`)**: a newly synthesised algorithmic strategy replaces the active incumbent only when backed by a deterministic sandbox verification digest (`fnv64`) and strict mathematical Pareto dominance (non-inferior accuracy, non-inferior latency and token cost, and strict improvement on at least one axis or Kolmogorov byte complexity).
- **Sandboxed Tool Forge and Self-Healing Loop (`agency-forge/src/sandbox/`, `agency-forge/src/healing/`, `server/features/continuous_learning/learning_loop.py`)**: when an agent fails at runtime or a capability is missing, Nuxiva classifies the root cause (`MissingCapability`, `SchemaDrift`, `EndpointRelocated`, `AuthExpired`, `SandboxGuardViolation`), synthesises code, validates it through the AST Guard, and activates it only if all deterministic test cases pass within `4000 ms` inside the isolated sandbox.
- **Zero-Token Shortcut Compiler (`reflex-core/src/shortcut_compiler.rs`)**: slow-path language-model resolutions that recur with confirmed outcomes are clustered using L2-normalised 1024-dimensional n-gram embeddings and automatically promoted to instant reflexes in plasticity memory, consuming zero tokens on future invocations.

### 4.3 Native Rust layer (93 Crates with `unsafe_code = "forbid"`)

The Rust workspace in `native/` comprises **93 native crates** compiled with workspace-wide `unsafe_code = "forbid"` and strict Clippy lints denying `unwrap`, `expect`, `panic`, `indexing_slicing` and `arithmetic_side_effects`: message bus, packet analysis for the firewall (`netguard`), egress proxy (`egress`), CRDT replication between nodes (`crdt-core`), audio DSP (`audio-dsp`), wake-word and full-duplex speech processing (`wakeword-core`, `ear-core`, `duplex-core`), face and gesture recognition (`face-core`, `gesture-core`), zero-hallucination formal oracle and reflex engine (`reflex-core`), interruption-cost initiative and reflection engines (`initiative-core`, `proactivity-core`, `reflect-core`), the project agency engine (`agency-domain`, `agency-planner`, `agency-scheduler`, `agency-thought`, `agency-forge`, `agency-foresight`, HMAC-chained `agency-ledger`, `agency-codeindex`, `agency-daemon`) and `core_brain`. The full list of crates is in `native/Cargo.toml`.

### 4.4 Installation pipeline

```mermaid
flowchart LR
    A[install.sh] --> B[nuxiva-supervisor]
    B --> C[Hardware analysis]
    C --> D[System packages]
    D --> E[Isolation]
    E --> F[Native build]
    F --> G[Senses and models]
    G --> H[Core and services]
    H --> I[(Assistant online)]
```

`install.sh` installs only the supervisor. The supervisor then executes the installation steps defined in `installer_wizard/backend/steps.py` (scripts in `scripts/os/steps/`), shows progress on the display, and makes the assistant usable as early as possible while large downloads continue in the background. Non-critical steps can fail without blocking the others and are retried or repaired automatically.

---

## 5. Security model

| Layer | Mechanism |
| :--- | :--- |
| Authentication | Admin login through Linux PAM (service `nuxiva-admin`), restricted to administrative accounts; HMAC-signed, HTTP-only session cookies with expiry; login rate limiting |
| Request integrity | Origin and host validation, custom request header on state-changing calls, strict Content Security Policy with Trusted Types |
| First-run protection | The setup wizard is reachable only from the local network and only until setup is complete |
| Authorisation | Approval gates for risky actions, optional voice biometrics, per-person visibility of private data |
| Code execution | Generated code runs only inside the sandbox broker, with no network or host access by default, optionally under gVisor or Firecracker micro-VMs |
| Network | Outbound sandbox traffic through the Rust egress proxy (allow-listed hosts, private and loopback ranges refused); native packet analysis feeding the firewall; firewall rules tested against real `nftables` in CI |
| Secrets | Cloud credentials stored in an encrypted vault under `/etc/nuxiva/`; secrets zeroised in native code |
| Services | Isolated services (Core, agency, netguard) run under dedicated or dynamic users with `NoNewPrivileges`, restricted capability sets and `ProtectSystem` hardening |
| Updates | Only revisions whose CI checks passed are installed; failed revisions are rolled back automatically |
| Native code | Workspace-wide `unsafe_code = "forbid"`; Clippy denies `unwrap`, `expect` and `panic` |

Vulnerabilities should be reported privately as described in [SECURITY.md](SECURITY.md).

---

## 6. Installation

### Requirements

| | Minimum | Recommended |
| :--- | :--- | :--- |
| Operating system | Debian 12 or Ubuntu 22.04+ | Latest Debian stable or Ubuntu LTS |
| Architecture | x86_64 or arm64 | x86_64 with AVX2 |
| CPU | 4 cores | 8+ cores |
| Memory | 8 GB | 16–32 GB |
| Storage | 30 GB | 100+ GB NVMe |
| GPU | Not required (quantised CPU models) | NVIDIA with 8 GB+ VRAM |
| Peripherals | None (headless) | Microphone, speakers, webcam, display |

Smaller machines can use a remote Ollama node or cloud models. On Windows, use WSL2 or the experimental `install.ps1`.

### One-command install

```bash
curl -fsSL https://raw.githubusercontent.com/AprileNunzio/Nuxiva/main/install.sh | sudo bash
```

Without `curl` (minimal systems):

```bash
wget -qO- https://raw.githubusercontent.com/AprileNunzio/Nuxiva/main/install.sh | sudo bash
```

The installer checks the system first (release, architecture, administrator rights, free space, connection and package sources) and stops with a clear, translated message when something is missing. It pins the exact commit to install and verifies the downloaded installer against the fingerprint published by GitHub before running it: if they do not match, nothing is executed. Running it again is safe and resumes or repairs the installation.

### Inspect before running

```bash
curl -fsSLo install.sh https://raw.githubusercontent.com/AprileNunzio/Nuxiva/main/install.sh
less install.sh
sudo bash install.sh --check   # system checks only, installs nothing
sudo bash install.sh
```

Options: `--check` runs only the checks, `--branch <name>` installs another branch, `--ref <commit>` installs an exact commit, `--sha256 <hash>` also requires a hash obtained independently.

### Install from a clone

```bash
sudo git clone https://github.com/AprileNunzio/Nuxiva.git /opt/Nuxiva
cd /opt/Nuxiva
sudo bash install.sh
```

### Uninstall

```bash
sudo nuxivactl uninstall           # removes program, services and system files, keeps your data
sudo nuxivactl uninstall --purge   # also deletes data, keys and service accounts
```

If `nuxivactl` is not available:

```bash
curl -fsSL https://raw.githubusercontent.com/AprileNunzio/Nuxiva/main/install.sh | sudo bash -s -- --uninstall
```

Ollama, Docker and system packages stay installed, because other programs may use them.

### First boot

1. Open `http://<host>/` on any device in the local network. The display shows installation progress and becomes the assistant once ready; no reboot is required.
2. Complete the optional first-run wizard at `http://<host>/setup`: language, network, components, AI engine (local, remote or cloud), assistant name, microphone and voice. Installation choices are persisted atomically and survive power loss.
3. Open the admin desktop at `http://<host>:8080/` and sign in with a Linux administrator account.

---

## 7. Operations

### Command line

```bash
nuxivactl status          # phase, progress and step status
nuxivactl background      # queued background downloads
nuxivactl logs [source]   # install, supervisor, core, ollama, voice, vision, ear
nuxivactl setup-code      # pairing code for the first-run wizard
nuxivactl version         # installed revision
sudo nuxivactl update     # install the latest revision that passed CI
sudo nuxivactl force-upgrade [branch]
sudo nuxivactl repair     # repair a damaged installation
sudo nuxivactl uninstall  # remove Nuxiva (add --purge to delete data)
```

### Updates and recovery

The updater (`installer_wizard/backend/updater.py`) installs a revision only after its CI checks have succeeded. A revision that fails to start is marked as bad and `nuxiva-rollback.service` restores the last known good revision. If the system cannot start at all, a safe-mode page and a repair script are served instead.

### Network ports

| Port | Service |
| :---: | :--- |
| 80 | Display, kiosk, setup wizard, chat |
| 8080 | Admin desktop, REST API, MCP server (`/mcp`) |
| 443 | Optional HTTPS with locally generated certificates |
| 8443 | Core API (internal) |
| 11434 | Ollama, bound to loopback |

### Services and paths

systemd units are defined in `scripts/os/systemd/` (supervisor, core, sandbox, netguard, agency, ear, vision, voice, rollback).

| Path | Content |
| :--- | :--- |
| `/opt/Nuxiva` | Application code |
| `/etc/nuxiva/nuxiva.env` | Configuration (`NUXIVA_*` variables) |
| `/etc/nuxiva/` | Keys, certificates and encrypted vault |
| `/var/lib/nuxiva/` | Application state |
| `/var/log/nuxiva/` | Installation and audit logs |

---

## 8. Configuration

Configuration is stored as `NUXIVA_*` variables in `/etc/nuxiva/nuxiva.env` and is editable from the admin desktop (Control panel → System settings). Every module declares its own settings in its `feature.json`, so new options appear in the interface automatically.

Common settings:

| Variable | Purpose |
| :--- | :--- |
| `NUXIVA_UI_LANG` | Interface language (`en`, `it`, `fr`, `es`) |
| `NUXIVA_OLLAMA_URL` | Use a remote Ollama node instead of the local one |
| `NUXIVA_ALLOWED_HOSTS` | Extra host names accepted by the origin guard |
| `NUXIVA_PUBLIC_PORT`, `NUXIVA_ADMIN_PORT` | Override the default ports |

Cloud model providers are added from the **Brain** application. They are optional, are mixed into the same priority list as local models, and can be restricted per task through privacy profiles.

---

## 9. Extending Nuxiva

A module is a folder in `installer_wizard/features/<id>/`, or in `/var/lib/nuxiva/features/<id>/` for locally installed modules:

```text
features/<id>/
├── feature.json     metadata, category, settings, capabilities, icon
├── api.py           HTTP routes                    (optional)
├── commands.py      voice and chat commands        (optional)
├── tools.py         tools exposed to agents and MCP (optional)
└── language/        en.json, it.json, fr.json, es.json
```

Widgets follow the same pattern in `installer_wizard/agenti/<…>/<agent>/widget/<id>/` (`widget.json`, `widget.js`, `widget.css`, `language/`). The supervisor discovers modules and widgets at start-up; tools are made available to the agent, to the specialist team and to external MCP clients without further wiring.

External MCP servers can be connected as tool sources, and Nuxiva exposes its own tools, resources and prompts as an MCP server on port 8080 (see `installer_wizard/MCP.md`).

---

## 10. Engineering standards

| Area | Standard |
| :--- | :--- |
| Architecture | Clean Architecture, separation of concerns, feature-based colocation, files kept small and single-purpose |
| Python | Python 3.11+, typed FastAPI services, syntax and `pyflakes` checks on every push |
| Rust | Edition 2024, `unsafe_code` forbidden workspace-wide, Clippy `all` denied, `rustfmt` enforced |
| Web | React and TypeScript, strict CSP, full i18n with no hardcoded strings, responsive layouts |
| Error handling | Exceptions handled at I/O, network and storage boundaries; global handlers; errors are never silently discarded |
| Testing | Unit and API tests for the supervisor, Core and sandbox; native parity tests; Rust tests; firewall rules on real `nftables`; web client tests |
| CI | `.github/workflows/ci.yml` runs all checks on every push; dedicated workflows build the web bundle and the Windows assistant |

---

## 11. Project

- **Contributing:** see [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).
- **Security:** see [SECURITY.md](SECURITY.md).
- **Third-party software:** see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **License:** [Nuxiva Personal and Commercial License 1.0](LICENSE). Earlier revisions distributed under MIT remain covered by [LICENSE-MIT-LEGACY](LICENSE-MIT-LEGACY).

### Support the project

If Nuxiva is useful to you, you can support its development:

<p align="center">
  <a href="https://www.paypal.com/paypalme/NunzioAprile">
    <img src="https://img.shields.io/badge/Donate-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Donate with PayPal">
  </a>
</p>
