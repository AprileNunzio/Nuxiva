# NUXIVA - Neural Unified eXperience for Interactive Vision & Automation

[🇬🇧 English](README.md) | [🇮🇹 Italiano](README_IT.md) | [🇫🇷 Français](README_FR.md)

## 🚀 What's New in Version 5.3.0 (Autonomous Games Framework, WebOS 47 Apps, Anti-Collision Desktop & Hardened Routing)

Nuxiva 5.3.0 delivers a generational leap in distributed AI operating systems, fusing autonomous desktop orchestration, collision-free widget placement, dedicated game engines, and deterministic cognitive routing:

- **Autonomous Games Framework & Dedicated GamesScanner (`installer_wizard/features/games/games_scanner.py`)**:
  - Dynamic discovery of native games in `giochi/` via declarative manifests (`manifest.json`), eliminating conflicting wizard wrappers and ensuring immediate availability of authentic experiences.
  - Native **Scacchi 3D (Wizard Chess 3D)**: High-fidelity Three.js Gothic Cathedral environment with real-time shadow casting, custom wood/marble GLB pieces, legal move enforcement via `wizardChessEngine.js`, and voice-driven gameplay.
  - Dual presentation model: Full-screen WebOS window mode or dedicated desktop widget with automatic assistant compression to maintain focus on the board.
- **Universal Collision-Free Desktop Widget Engine (`desk.js`)**:
  - Geometric anti-collision solver guaranteeing widgets never overlap across arbitrary screen resolutions, aspect ratios, and multi-display setups.
  - Strict Zero-Trust UI isolation: complete removal of management entrypoints ("Gestisci Nuxiva") from public-facing kiosk screens (Port 80).
- **Deterministic Cognitive Routing & Protected Tool Dispatch (`assistant.py`)**:
  - Intent-first dispatching pipeline prioritizing explicit user commands before falling back to probabilistic tools, preventing erroneous interception (e.g. preventing TV or IoT controllers from hijacking system time or power-off commands).
  - Robust prompt sanitization preventing unterminated JSON / string formatting exceptions in remote cloud LLM calls (Gemini 3.8 Flash).
- **WebOS 47 Autonomous Applications Ecosystem**: Dynamic discovery of 47 autonomous desktop applications across categories, multi-window tiling, snap-to-edge, maximize/minimize, per-user state persistence, and account isolation.
- **Omni-Cortical Engine 6.5 & Modular Reasoning Engines**: Full decoupling under the Open/Closed Principle with dynamic auto-discovery via `EngineScanner`. Six distinct cognitive engines from ultra-low latency Liquid LNN to 64-branch latent MCTS.
- **Leaky Integrate-and-Fire (LIF) & Hebbian STDP Plasticity**: Spiking Neural Network core (`native/crates/bus-core/src/spike.rs`) modeling membrane potential decay ($\tau_m$), dynamic refractory periods, limbic-modulated firing thresholds, and Spike-Timing-Dependent Plasticity ($A^+$, $A^-$, $\tau_{\text{stdp}}$) with dopamine reward signals.
- **Limbic Modulator & Real-Time Sensory-Limbic Binding**: Continuous 7-axis emotional vector (Valence, Arousal, Dominance, Dopamine, Noradrenaline, Serotonin, Cortisol) dynamically tuning cognitive budgets.
- **Universal Dynamic Scanner with Rust Native Engine (`bus-core`)**: High-throughput `FastScanner` in Rust exposed via PyO3 with FNV-1a hashing, parallel traversal, Zero-Trust AST security validation, and hot-reload watchers.
- **Modular Dynamic Widgets & Reactive Web Deck**: Dedicated directory architecture (`server/web/widgets/<widget_id>/`) with `manifest.json`, `widget.py`, REST/WebSocket controllers, and live telemetry streaming.
- **CEO Multi-Agent Orchestrator & Dynamic AgentScanner**: Dynamic orchestration analyzing live manifests and semantic token indexes without hardcoded rosters.
- **Clinical Tri-Agent Cognitive Triage**: Medical, psychological, and deterministic safety interlocks (`triage_safety_interlock`).
- **100% Green CI & Clean Architecture Purity**: Zero comments in source code, strict $\le 500$ line modularity limits, and synchronized versioning across all 22 components.

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-Clean%20Architecture-00f0ff?style=for-the-badge" alt="Clean Architecture">
  <img src="https://img.shields.io/badge/Cognitive-Omni%20Cortical%206.5-purple?style=for-the-badge" alt="Omni-Cortical">
  <img src="https://img.shields.io/badge/Security-Zero%20Trust%20Wasm-red?style=for-the-badge" alt="Zero Trust">
  <img src="https://img.shields.io/badge/Resilience-eBPF%20Self%20Healing-blue?style=for-the-badge" alt="eBPF">
  <img src="https://img.shields.io/badge/State-Event%20Sourcing-emerald?style=for-the-badge" alt="Event Sourcing">
  <img src="https://img.shields.io/badge/Compute-P2P%20Mesh%20Swarm-amber?style=for-the-badge" alt="Swarm Compute">
  <a href="https://www.paypal.com/paypalme/NunzioAprile"><img src="https://img.shields.io/badge/Donate-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="PayPal"></a>
</p>

```text
 ███╗   ██╗██╗   ██╗██╗  ██╗██╗██╗   ██╗ █████╗ 
 ████╗  ██║██║   ██║╚██╗██╔╝██║██║   ██║██╔══██╗
 ██╔██╗ ██║██║   ██║ ╚███╔╝ ██║██║   ██║███████║
 ██║╚██╗██║██║   ██║ ██╔██╗ ██║╚██╗ ██╔╝██╔══██║
 ██║ ╚████║╚██████╔╝██╔╝ ██╗██║ ╚████╔╝ ██║  ██║
 ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝  ╚═╝  ╚═╝
 DISTRIBUTED AI OPERATING SYSTEM - ENTERPRISE v5.3.0
      Designed and developed by NunzioTech
```

## ❤️ Nuxiva is free, and it stays free

Nuxiva is a **completely free** project, designed, written, and maintained by **Nunzio Aprile (NunzioTech)** in his own time:
no subscriptions, no paywalled features, no data sold. Every line of code is yours to inspect, modify, and deploy.

If Nuxiva runs your home, manages your infrastructure, helps you study, or empowers your research, **a donation is what keeps it growing**: it pays for test hardware (cameras, ESP32 boards, GPUs, edge devices), cloud model API credits for development, and the thousands of hours required for pioneering new autonomous architectures.
Even the price of a coffee makes a tangible difference, and every contribution directly funds Nuxiva's open-source evolution.

<p align="center">
  <a href="https://www.paypal.com/paypalme/NunzioAprile">
    <img src="https://img.shields.io/badge/Donate-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Donate with PayPal">
  </a>
</p>

<p align="center"><b>👉 <a href="https://www.paypal.com/paypalme/NunzioAprile">paypal.me/NunzioAprile</a> — thank you for supporting independent open-source engineering!</b></p>

---

## Enterprise-Grade Architecture (The 5 Pillars)

Nuxiva is not a simple script or monolithic chatbot wrapper, but a **Distributed, Self-Healing Operating System** engineered upon five foundational pillars:

1. **Self-Healing Kernel (eBPF & Landlock):** Low-level kernel monitoring via C eBPF probes in the Linux Kernel to detect memory leaks, socket anomalies, and unauthorized syscalls, triggering runtime LLM self-repair and sandboxing.
2. **Isolated Execution (Zero-Trust Wasm & MicroVMs):** No third-party plugin or synthesized tool runs natively on the host. Code is sandboxed inside WebAssembly (Wasmtime) with strict capability-based WASI policies (< 5ms cold start), user-space gVisor runtimes, or dedicated Firecracker MicroVMs.
3. **Time-Travel (Event Sourcing & Immutable Ledger):** No mutable direct state. Every perception, thought step, biometric delta, and system decision is recorded in an append-only, HMAC hash-chained Ledger, enabling millisecond-accurate mathematical state rewind, auditing, and deterministic debugging.
4. **Swarm Computing (P2P Mesh Swarm):** Nuxiva scales horizontally across local and remote nodes. Automatic UDP beaconing and gRPC mesh discovery enable distributed offloading of vision tensors, audio features, and neural inference across specialized LAN GPU worker nodes.
5. **Dynamic SDK & Contract Generation:** Automatic generation of client contracts, API routes, and SDKs in TypeScript, Rust, and Python via dynamic reflection, OpenAPI, and Protobuf schemas for seamless interoperability.

---

## 1. At a Glance

| Aspect | Implementation Details |
| :--- | :--- |
| **Installation** | One command on Debian/Ubuntu: clones repository into `/opt/Nuxiva` and launches the autonomous supervisor daemon. |
| **Supervisor** | `nuxiva-supervisor` daemon (Python 3.11+, FastAPI, asyncio). Manages 31 OS deployment steps, health watchdogs, auto-recovery, and background tasks. |
| **Display (Port 80)** | Interactive kiosk: 3D holographic wireframe face (Orb), natural voice interaction, live audio perception, dynamic widget desktop, and reasoning mode selector. |
| **Admin Cockpit (Port 8080)** | Comprehensive administrative interface with PAM system authentication, real-time telemetry, model assignments, feature toggles, and system logs. |
| **Cognitive Brain** | 6 Modular Reasoning Engines (Legacy 4.2 to Ultra 6.5), LIF Spiking Neural Network, Limbic Modulator, local Ollama, distributed remote nodes, and 22 encrypted cloud LLM providers. |
| **Features Ecosystem** | 72 self-discovered feature packages in `installer_wizard/features/`. Each package automatically activates based on hardware (`auto`) or explicit flags (`1`/`0`). |
| **Continuous Updates** | Automated git synchronization every 5 minutes from `main` (only passing CI builds), with automated test verification and instant rollback. Emergency upgrade via `nuxivactl update --force`. |
| **CEO Orchestrator & Team** | Dynamic CEO multi-agent orchestrator backed by `AgentScanner`. Zero hardcoded agents: scans `/features` and `/widgets` dynamically, delegating via semantic token indexing. |
| **Understanding & Triage** | Multi-candidate intent scoring with contextual arbitration, verified outcome feedback loops, and clinical tri-agent cognitive triage (medical, psychological, safety interlock). |
| **Reliability & Quality** | Deterministic post-execution effect verification, automatic retry, and over 1,200 automated unit and integration tests across supervisor, core, and native Rust crates. |
| **Interoperability (MCP)** | Full Model Context Protocol (MCP) server (Port 8080) and client, OpenAPI schema exports, Anthropic/OpenAI function calling, and REST/WebSocket endpoints. |
| **Multilingual (i18n)** | 100% complete localization in English, Italian, and French across all UI decks, modal wizards, widgets, and console error messages. Dynamic voice download for spoken interaction. |

---

## 2. Architectural Evolution & Version History

### Version 5.3.0: The Autonomous Games Framework & Anti-Collision Desktop Era
- **Autonomous Games Ecosystem & GamesScanner**: Decoupled discovery of native games in `giochi/` via `games_scanner.py`, standalone Three.js WebGL rendering, and responsive desktop integration.
- **Scacchi 3D (Wizard Chess 3D)**: High-performance gothic cathedral environment, authentic 3D pieces, position validation via `wizardChessEngine.js`, and voice controls.
- **Collision-Free Desktop Solver**: Anti-overlap geometric layout manager (`desk.js`) ensuring pristine widget organization on any display.
- **Zero-Trust UI Hardening**: Complete removal of management links from public-facing kiosk screens (Port 80).
- **Deterministic Cognitive Routing**: Intent-first priority pipeline preventing command crosstalk and misdirection in `assistant.py`.
- **WebOS 47 Applications**: Full window management, state isolation, snap tiling, and localized categorization.

### Version 4.1.53: The Neuro-Cognitive & Universal Dynamic Era
- **Modular Omni-Cortical Engine**: Decoupled reasoning engines (`BaseReasoningEngine`) in `server/core/reasoning/engines/` with dynamic auto-discovery via `EngineScanner`.
- **Neuro-Biological Brain Dynamics**: Leaky Integrate-and-Fire (LIF) spiking neural network with refractory period, STDP synaptic plasticity, and 7-dimensional limbic modulation.
- **Sensory-Limbic Real-Time Binding**: Vocal acoustic stress, facial valence, and occupancy presence streamed into the cortical limbic vector and broadcasted as `biometrics.*` events on `nuxiva_bus`.
- **Default Mode Network (DMN)**: Autonomous background cognitive cycle running during 10-minute idle intervals for memory consolidation and foresight simulation.
- **Nightly Synaptic REM Consolidation**: Nightly STDP weight decay and stabilization mitigating the Ebbinghaus forgetting curve.
- **Universal Dynamic Scanner & Rust Acceleration**: High-throughput `FastScanner` in Rust (`bus-core`) with FNV-1a fingerprinting, paired with Python `UniversalScanner`, AST Zero-Trust validation, and `DirectoryWatcher`.
- **Dedicated Directory Widgets & Agent Tools**: Modular directory layout for dynamic widgets (`server/web/widgets/`) and agent tools (`server/features/agent_tools/`) with auto-discovery and WebSocket streaming.
- **CEO Multi-Agent Orchestrator**: Head of conversation turns with dynamic `AgentScanner` analyzing live manifests and semantic token indexes without hardcoding.
- **Clinical Cognitive Triage**: Medical, psychological, and safety interlock triage agents protecting user interactions.
- **Ordered Background Queue**: Package installation sorted strictly by ascending GB size with real-time download speed meters (MB/s or KB/s).
- **Emergency SSH Force Upgrade**: Hard-reset script `force-upgrade.sh` and CLI command `nuxivactl update --force`.
- **Robustness**: Non-blocking initial setup wizard and sanitized `/etc/nuxiva/nuxiva.env` parsing.

### Version 4.0.0: Enterprise Swarm & Spatial RBAC
- **Spatial-Temporal RBAC**: Fine-grained access control combining physical room/zone awareness with scheduled time windows.
- **Autonomous Multi-Agent Swarm**: Isolated persistent workspaces (`data/agents/<agent_id>`), dedicated instructions, knowledge repositories, and tool bindings.
- **Chief Supervisor & War Room HUD**: 24/7 executive watchdog preventing infinite loops and broadcasting live thought graphs.
- **Extended Tool Arsenal**: Native CAD (DXF 2D/3D), Google Workspace (Gmail, Calendar, Drive, Sheets, Docs), and Social Media orchestration.
- **Ternary Reasoning**: System 1 (reactive edge router), System 2 (ReAct loop with self-critique), and System 3 (Byzantine consensus jury).
- **Proximity HUD & Chatbot Mesh**: P2P mesh for multi-agent synchronization and ambient radar presence.
- **Proxmox VE Integration**: Automated hypervisor administration for VMs and LXC containers.

### Version 3: Modular Feature Rewriting & MCP
- **Dual-Brain Architecture**: Fast non-autoregressive System 1 (< 50ms) and deliberative System 2 with `<thinking>` scratchpad.
- **Reorganized Brain Cockpit**: Brains Dashboard, Component Assignments, and Add/Manage Brains.
- **Distributed Neural Cluster**: Mixed priority lists combining local Ollama, remote OpenAI-compatible nodes, and 22 cloud providers.
- **Model Context Protocol (MCP)**: Native MCP server and client integration.
- **Verified Outcome Engine**: Post-execution verification for media, smart home, and UI actions.
- **Autonomous Forge**: Zero-code synthesis of composite tools and widgets.

---

## 3. System Requirements

| Component | Minimum Requirement | Recommended Specification |
| :--- | :--- | :--- |
| **Operating System** | Debian 12 (Bookworm) or Ubuntu 22.04+ LTS (x86_64 / arm64) | Debian 12 Minimal (x86_64) |
| **Processor** | 4 CPU cores (x86_64 with AVX or ARM64 v8.2+) | 8+ CPU cores with AVX2 / AVX-512 |
| **Memory (RAM)** | 8 GB System RAM | 16–32 GB DDR4/DDR5 System RAM |
| **Graphics (GPU)** | None (pure CPU inference supported) | NVIDIA RTX (8 GB+ VRAM) with CUDA 12+ or Apple Silicon |
| **Storage** | 30 GB available disk space | 100+ GB NVMe SSD (models, voices, recordings) |
| **Network** | Broadband internet connection for initial setup | Dedicated Gigabit Ethernet connection |
| **Peripherals** | Optional headless deployment | Microphone, stereo speakers, USB/IP webcam, display |

> [!NOTE]
> - The installation and package bootstrapping use `apt-get`: **only Debian, Ubuntu, and direct derivatives** are supported natively.
> - On systems without a dedicated GPU, Nuxiva automatically selects optimized lightweight quantized models (e.g. Q4_K_M, 1.5B–3B parameters).
> - Modest hardware can offload neural computation entirely by setting `NUXIVA_OLLAMA_URL` to a remote GPU node or relying on cloud providers.

In Cervello, saving an individual LLM role binds its Ollama model to the selected server, so fast
conversation can use local Ollama while reasoning uses a remote machine. The binding is stored in the
existing server vault and survives changes to `NUXIVA_OLLAMA_URL`; older unqualified model settings
continue to use that global endpoint. **Sync all modules** explicitly replaces every role with the
global default. Per-role remote assignments keep local models loaded for other roles.
> - Hardware-dependent features (webcam perception, audio beamforming, CUDA acceleration) gracefully self-disable when physical devices are absent.

---

## 4. Installation

### One-Liner (Recommended for Debian/Ubuntu)

Execute the following command in a clean terminal session with sudo privileges:

```bash
curl -fsSL https://raw.githubusercontent.com/AprileNunzio/Nuxiva/main/install.sh | sudo bash
```

The script performs pre-flight checks, clones the repository into `/opt/Nuxiva`, configures system permissions, installs Python and basic build tools, and registers the `nuxiva-supervisor` systemd service. The supervisor immediately takes over and automates the rest of the setup.

### Manual Installation from Repository Clone

```bash
# 1. Clone the repository
sudo git clone https://github.com/AprileNunzio/Nuxiva.git /opt/Nuxiva
cd /opt/Nuxiva

# 2. Run the automated installer script
sudo bash install.sh
```

### Windows Deployment

For Windows workstations, Nuxiva is officially supported via **WSL2 (Windows Subsystem for Linux)** running Ubuntu 22.04 or Debian 12:

```powershell
# In PowerShell (Administrator):
wsl --install -d Ubuntu-22.04
wsl
```
Inside the WSL2 Linux environment, simply execute the standard one-liner:
```bash
curl -fsSL https://raw.githubusercontent.com/AprileNunzio/Nuxiva/main/install.sh | sudo bash
```
For native Windows experimentation, an administrative PowerShell script is provided:
```powershell
.\install.ps1
```

---

## 5. First Boot, Access, and Background Installations

### Access Ports & Interfaces

Once the supervisor starts, Nuxiva serves two dedicated web portals:

1. **Interactive Display / Kiosk (Port 80):** `http://<server-ip>/`
   - Interactive 3D wireframe face (Orb) reacting to speech, audio, and camera feeds.
   - Dynamic widget desktop displaying widgets in real time.
   - Cognitive Engine UI Selector: switch active reasoning modes directly on the fly.
   - Fullscreen kiosk session automatically launched on physical displays connected to the server.
2. **Administration Cockpit (Port 8080):** `http://<server-ip>:8080/`
   - Complete system management authenticated via Linux PAM system credentials (root or sudoers).
   - Real-time telemetry, model management, priority chains, dynamic feature configuration, and log viewer.

### Optional Initial Awakening Setup

The initial configuration wizard (`/setup` on Port 80) is **fully optional and non-blocking**. You can:
- Walk through the interactive steps: assistant name customization, Wi-Fi/Ethernet configuration, microphone calibration, and initial voice preference.
- Freely skip the wizard and proceed directly to the default interactive desktop.
- Re-run or reset the setup at any time from the administration cockpit without interrupting running services.

### Background Installations Queue with Real-Time Speed & Size Ordering

Heavy components (neural models, vision classifiers, voice models, containers) are deployed asynchronously in the background so the assistant is usable immediately:
- **Real-Time Speed Metering**: The background queue (`bgqueue.js/css`) displays current download speeds (in MB/s or KB/s), dynamic progress bars, and percentage completion.
- **Ascending Size Ordering**: The download queue is sorted strictly from the smallest component in GB to the largest. Lightweight tools and models become functional in seconds, while multi-gigabyte neural weights download gracefully in the background.
- **CLI Inspection**: Inspect the background queue status anytime via:
  ```bash
  nuxivactl background
  ```

---

## 6. System Architecture

```text
+---------------------------------------------------------------------------------------+
|                                    NUXIVA RUNTIME                                     |
+---------------------------------------------------------------------------------------+
|  CLIENT INTERFACES                                                                    |
|  - Kiosk Display (Port 80): 3D Orb, Audio STT/TTS, Dynamic Widget Desktop, Engine UI  |
|  - Admin Cockpit (Port 8080): PAM Auth, Telemetry, Model Assign, Logs, Step Control   |
|  - React Web Client (client_web): Control Deck, 3D Core Visualizer, DynamicWidgetDeck |
|  - P2P Satellites & Android APK: Audio/Vision Edge Nodes, Proximity Radar HUD         |
+---------------------------------------------------------------------------------------+
|  SUPERVISOR & AUTONOMOUS ENGINE (installer_wizard/backend/ - Python / FastAPI)       |
|  - Supervisor Service (nuxiva-supervisor.service)                                     |
|  - 31 Step OS Orchestrator & State Store (state.json, ledger.log)                     |
|  - Background Loops Watchdog & Default Mode Network (DMN 10-min reflection loop)      |
|  - Dynamic AgentScanner & CEO Multi-Agent Orchestrator (features/team/ceo.py)         |
|  - 72 Dynamic Features & Dynamic Widgets Controller (/widgets, /widgets/ws)          |
+---------------------------------------------------------------------------------------+
|  COGNITIVE KERNEL & REASONING ENGINES (server/core/ & server/features/)               |
|  - Omni-Cortical Engine 6.5 & BaseReasoningEngine Dynamic Registry                    |
|    [ Legacy 4.2 | Veloce 5.0 | Empatico 5.0 | Pro 6.0 | Ultra 6.5 | Auto 6.5 ]      |
|  - Leaky Integrate-and-Fire (LIF) Spiking Neural Core & Hebbian STDP Plasticity       |
|  - 7-Axis Limbic Modulator (Valence, Arousal, Dominance, DA, NE, 5-HT, Cortisol)     |
|  - Real-Time Sensory-Limbic Binding (Ear acoustic stress, Scene pressure, Presence)  |
|  - Global Neuronal Workspace (GNW): Speculative Parallelism & GABAergic Inhibition   |
|  - Clinical Tri-Agent Cognitive Triage (Medical, Psychological, Safety Interlock)     |
|  - Dynamic Agent Tools (CAD, 3D Gen, Google Suite, Image, Maps, Music, Social, Web)   |
|  - Nightly REM Sleep Synaptic Weight Consolidation & Ebbinghaus Decay Mitigation      |
+---------------------------------------------------------------------------------------+
|  EVENT BUS & HIGH-PERFORMANCE NATIVE LAYER (native/crates/ - Rust & PyO3)             |
|  - bus-core: Zero-copy event dispatching, Spiking RingBufferLockFree, FastScanner     |
|  - egress: Cross-platform Zero-Trust Landlock sandbox & network egress proxy          |
|  - netguard: Packet inspection and network security gating                            |
|  - nuxiva-native: PyO3 bridge exposing native Rust structs to Python runtime          |
+---------------------------------------------------------------------------------------+
|  ISOLATED WORKSPACES & OS RUNTIME (Linux Kernel & Container Sandbox)                  |
|  - Zero-Trust Wasm Runtime (Wasmtime) & MicroVMs (Firecracker / gVisor)               |
|  - Persistent Workspaces (data/agents/<agent_id>/) & Event Sourcing Ledger            |
|  - Linux Kernel eBPF Probes, ZRAM/Swap, Docker CE, Ollama Runtime, PipeWire/ALSA      |
+---------------------------------------------------------------------------------------+
```

### The Cognitive Cycle of a Request

1. **Perception & Edge Ingestion**: Audio waveform is captured by `features/ear/` (Whisper STT) or vision frame by `features/vision/` (YOLO/VLM).
2. **Sensory-Limbic Modulation**: The speaker's acoustic stress and facial valence update the 7-axis `LimbicModulator`. Biometrics are emitted to `nuxiva_bus`.
3. **CEO Orchestration & Intent Classification**: The CEO Orchestrator (`features/team/ceo.py`) consults `AgentScanner` to match the request against live agents, capabilities, tools, and semantic tokens.
4. **Cognitive Engine Selection**: The Omni-Cortical Engine chooses the active reasoning profile (e.g. `nuxiva-6.5-auto` dynamically routes based on prompt complexity $\psi$, limbic arousal, and hardware VRAM).
5. **Speculative Parallel Execution (GNW)**: Candidate reasoning branches run concurrently. If a branch achieves confidence $\ge$ ignition threshold, it ignites the Global Workspace, triggering immediate **GABAergic lateral inhibition** to cancel remaining branches.
6. **Safety Interlock & Byzantine Consensus**: Clinical or physical actions pass through deterministic safety interlocks and multi-model consensus juries.
7. **Action Execution in Sandboxed Environment**: Dynamic tools or verified system commands execute inside isolated sandboxes.
8. **Outcome Verification & Feedback**: `runner.py` verifies the real-world outcome (e.g. device state, audio playback) and updates the shared whiteboard.
9. **Synaptic STDP Learning**: Synapses connecting the activating neurons update their weights via STDP plasticity, persisting state for future recall.

---

## 7. Repository Structure

```text
/opt/Nuxiva/
├── client_apk/                  # Native Android companion application (Kotlin)
├── client_satellite/            # Lightweight edge satellite daemon for ESP32/Raspberry Pi
├── client_web/                  # Next-gen React 18 + Vite + Tailwind + Three.js web application
│   ├── src/features/
│   │   ├── cognitive_engine/    # Reasoning Engine Selector UI and hooks (useCognitiveEngine)
│   │   ├── control_deck/        # Operational control cockpit & Neural Analysis Flow
│   │   ├── core_visualizer_3d/  # 3D Spiking neural visualizer & telemetry HUD
│   │   ├── dynamic_widgets/     # DynamicWidgetDeck & dynamic widget rendering
│   │   └── studio_3d/           # Parametric 3D CAD/model editing studio
│   └── src/shared/i18n/         # Full localization catalogs (EN, IT, FR)
├── data/                        # Persistent application state, agent workspaces, vaults
│   └── agents/<agent_id>/       # Isolated persistent agent workspaces
├── docker/                      # Production container definitions
├── installer_wizard/            # Supervisor daemon & administrative core
│   ├── backend/                 # FastAPI supervisor, loops, nuxiva_bus, background queue
│   ├── features/                # 72 modular self-discovered system features
│   │   ├── brain/               # Brain presets, LIF components, assignments, residency
│   │   ├── chat/                # Assistant pipeline, brain_chain (GNW), API endpoints
│   │   ├── team/                # CEO Orchestrator, dynamic AgentScanner, shared board
│   │   ├── ear/                 # STT transcription, acoustic stress, voiceprint biometrics
│   │   ├── vision/              # VLM, YOLO object detection, nightly consolidation
│   │   └── ...                  # 67 additional specialized features
│   └── web/                     # Web portal frontends (display, admin, nexus, monitor, setup)
├── native/                      # High-performance compiled Rust crates
│   └── crates/
│       ├── bus-core/            # FastScanner (FNV-1a), Spiking Neural Core, RingBufferLockFree
│       ├── egress/              # Cross-platform Zero-Trust Landlock network proxy
│       ├── langid/              # Sub-millisecond natural language identification
│       ├── netguard/            # Deep packet inspection firewall
│       └── nuxiva-native/       # PyO3 bindings exposing Rust crates to Python
├── sandbox_broker/              # Zero-Trust MicroVM and container execution broker
├── scripts/os/                  # 31 deployment step scripts, maintenance, and force-upgrade
│   ├── steps/                   # Numbered scripts from 10-preflight.sh to 95-warmup.sh
│   ├── force-upgrade.sh         # Emergency SSH hard-reset and direct GitHub upgrade script
│   └── nuxivactl                # Central system management CLI executable
├── server/                      # Nuxiva Cognitive Core (Python 3.11+)
│   ├── cmd/                     # API routers, main entrypoint, FeatureRouteScanner
│   ├── core/
│   │   ├── kernel/              # Byzantine consensus, limbic state domain, swarm lanes
│   │   ├── orchestrator/        # System 1 router, DAG task planner, skill acquisition
│   │   ├── reasoning/           # Omni-Cortical Engine & modular reasoning engines
│   │   │   └── engines/         # auto_6_5, ultra_6_5, pro_6_0, empatico_5_0, veloce_5_0, legacy_4_2
│   │   └── scanner/             # UniversalScanner, ZeroTrustValidator, DirectoryWatcher
│   ├── features/
│   │   ├── agent_tools/         # Modular tools: cad, 3d, google, image, maps, music, social, web
│   │   ├── cognitive_triage_agents/ # Clinical tri-agent triage (medical, psychological, safety)
│   │   └── multimodal_surveillance/ # Affective fusion, wearable vitals hub, audio enhancer
│   └── web/widgets/             # Modular dynamic widgets (manifest.json, BaseWidget, controller)
├── install.sh                   # Automated bootstrap script for Debian/Ubuntu
├── install.ps1                  # PowerShell bootstrap script for Windows
├── docker-compose.yml           # Multi-container orchestration definition
└── VERSION                      # System version identifier (5.3.0)
```

---

## 8. The Supervisor & Background Engine

The supervisor (`nuxiva-supervisor.service`) operates continuously in the background to ensure absolute system resilience and self-healing:

### Background Loops Watchdog (`installer_wizard/backend/loops.py`)
- **Fault Detection & Auto-Restart**: Periodically inspects all running background services. If a service becomes unresponsive or crashes, the supervisor restarts it with exponential backoff (`NUXIVA_LOOPS_BACKOFF_MAX`).
- **Heartbeat Tracking**: Every loop reports execution heartbeats. If a task exceeds its stale limit ($5 \times \text{period}$), the supervisor terminates and re-instantiates the thread.

### Default Mode Network (DMN) Autonomous Reflection
- **Idle Inactivity Trigger**: When the user has not interacted with Nuxiva for 10 minutes (`idle_threshold_s = 600.0`), the DMN activates automatically.
- **Autonomous Memory Consolidation**: The DMN queries `LongTermMemory` for recent episodic traces and cross-references them against proactive habit predictions in `features/habits/foresight.py`.
- **Foresight Simulation**: Runs an autonomous speculative thought cycle via `cortical_chain.execute_parallel_thought()`, pre-generating recommended automations and priming system caches.
- **Activity Reset**: Any incoming chat, voice command, or UI event immediately resets the DMN timer to guarantee zero interference with active user tasks.

---

## 9. Operating System Installation Steps

Nuxiva automates operating system provisioning via 31 modular, numbered scripts located in `scripts/os/steps/`. Each step is idempotent and tracked in `state.json`:

| Step Script | Title | Description & Responsibilities |
| :--- | :--- | :--- |
| `10-preflight.sh` | Pre-flight Diagnostics | Validates OS release, architecture (x86_64/arm64), CPU cores, RAM, and disk space. |
| `15-memory.sh` | Memory & ZRAM | Configures compressed ZRAM swap and optimizes kernel memory management (`vm.swappiness`). |
| `20-system.sh` | Base Packages | Installs core Linux utilities, build essentials, curl, git, jq, and Python headers. |
| `25-kiosk.sh` | Display Kiosk | Provisions lightweight X11/Cage/Chromium kiosk environment on physical displays (Port 80). |
| `30-docker.sh` | Container Runtime | Installs and configures Docker CE engine and containerd daemon. |
| `32-sandbox.sh` | Execution Sandboxes | Prepares isolated root filesystems and sandbox runners for dynamic code execution. |
| `33-display-driver.sh` | Display Drivers | Configures GPU rendering drivers (Mesa, DRM/KMS, Xorg acceleration). |
| `34-gvisor.sh` | gVisor Sandbox | Sets up Google's `runsc` userspace kernel container runtime for network-capable sandboxes. |
| `35-gpu.sh` | GPU Acceleration | Detects NVIDIA CUDA, AMD ROCm, or Intel oneAPI; configures container pass-through. |
| `36-firecracker.sh` | MicroVM Hypervisor | Installs Firecracker KVM hypervisor for sub-second isolated microVM tool execution. |
| `38-native.sh` | Native Rust Crates | Compiles Rust crates (`bus-core`, `egress`, `langid`, `netguard`, `nuxiva-native`) via Cargo. |
| `40-security.sh` | Security Hardening | Configures AppArmor profiles, PAM policies, firewall rules (UFW/nftables), and file permissions. |
| `42-netguard.sh` | Netguard DPI | Deploys deep packet inspection engine for local network defense and anomaly mitigation. |
| `43-vpn.sh` | Mesh VPN | Configures WireGuard and Tailscale peer-to-peer encrypted mesh networking. |
| `50-ollama.sh` | Ollama LLM Service | Provisions Ollama systemd daemon with sanitized environment variables and deferred start. |
| `55-voice.sh` | Speech Synthesis | Deploys Piper TTS and Kokoro high-speed neural speech synthesis engines. |
| `56-bluetooth.sh` | Bluetooth Peripheral | Configures BlueZ and PipeWire audio stack for wireless microphone/speaker pairing. |
| `57-vision.sh` | Computer Vision | Installs OpenCV, OpenVINO, YOLO models, and VLM acceleration pipelines. |
| `58-ear.sh` | Audio Perception | Sets up Whisper STT transcription, acoustic stress detection, and voiceprint extraction. |
| `59-music.sh` | Media Library | Sets up local music indexing, fingerprinting, DLNA streaming, and Chromecast server. |
| `60-models.sh` | Model Downloader | Downloads initial neural weights ordered by ascending GB size with bandwidth monitoring. |
| `61-brain.sh` | Cognitive Brain | Configures model assignment routes and initializes the Omni-Cortical reasoning pipeline. |
| `62-convert3d.sh` | 3D CAD Tools | Deploys 2D/3D DXF conversion tools, mesh processing utilities, and parametric libraries. |
| `63-shares.sh` | Network Shares | Provisions Samba (SMB/CIFS) network shares compatible with Windows 11 and macOS. |
| `64-office.sh` | Document Services | Installs headless LibreOffice and document conversion filters for document analysis. |
| `66-voicestudio.sh` | Voice Studio | Configures optional XTTS voice cloning container with dynamic disk space validation. |
| `67-soup.sh` | Model Souping | Sets up weight interpolation and fine-tuning tools for offline autonomous study. |
| `70-core.sh` | Nuxiva Core | Builds and installs `server/` Python dependencies, Alembic schemas, and service daemons. |
| `80-services.sh` | Daemon Orchestration | Enables and starts all systemd services (`nuxiva-core`, `nuxiva-supervisor`, etc.). |
| `90-maintenance.sh` | Auto Maintenance | Installs cron maintenance scripts for log rotation, journal hygiene, and temporary cleanup. |
| `95-warmup.sh` | Model Pre-Warming | Performs test inferences to preload active neural weights into RAM/VRAM cache. |

---

## 10. The Cognitive Brain: Architecture, Reasoning Engines & Neuro-Biology

### The 6 Modular Reasoning Engines (`server/core/reasoning/engines/`)

Nuxiva's cognitive kernel operates under the Open/Closed Principle. Each reasoning engine is an isolated module inheriting from `BaseReasoningEngine`, automatically discovered by `EngineScanner`:

| Engine Version | Codename | Architecture & Underlying Strategy | SLA Latency | VRAM Budget | Default Profile |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `nuxiva-4.2-legacy` | **Legacy Chain-Sync** | Sequential token pipeline with serial fallback | 2500 ms | 2048 MB | Fallback |
| `nuxiva-5.0-veloce` | **Veloce Synapse-Flash** | Ternary 1.58-bit Liquid LNN with zero-copy spiking bus | 25 ms | 512 MB | Edge/Chat |
| `nuxiva-5.0-empatico`| **Empatico Synapse-Limbic** | Global Workspace 8 parallel lanes with 10Hz biometric fusion | 120 ms | 4096 MB | Social/Voice |
| `nuxiva-6.0-pro` | **Pro Omni-Latent** | Continuous Latent Space JEPA/Coconut with live VRAM TTT | 15 ms | 8192 MB | Coding/Logic |
| `nuxiva-6.5-ultra` | **Ultra DeepThink-MCTS** | 64-branch latent MCTS with dopaminergic Process Reward Model | 650 ms | 16384 MB | Research/CAD |
| `nuxiva-6.5-auto` | **Auto Thalamic-Adaptive** | Thalamic meta-orchestrator on Free Energy Principle ($\psi$) | 45 ms | Dynamic | **Active Default** |

#### Dynamic Meta-Orchestration Logic (`nuxiva-6.5-auto`)
When operating in automatic mode, the Thalamic Meta-Orchestrator calculates the cognitive complexity parameter $\psi \in [0.0, 1.0]$ based on prompt token entropy and free energy surprise:
- $\psi < 0.25$: routes immediately to `nuxiva-5.0-veloce` (instant reactive response).
- $\psi < 0.50$ or high emotional arousal: routes to `nuxiva-5.0-empatico` (empathetic, limbic-aligned dialogue).
- $0.50 \le \psi < 0.75$: routes to `nuxiva-6.0-pro` (deep structured reasoning with tool execution).
- $\psi \ge 0.75$: routes to `nuxiva-6.5-ultra` (full MCTS tree search with adversarial self-critique).

### Leaky Integrate-and-Fire (LIF) Spiking Neural Core

The neuro-biological engine (`installer_wizard/features/brain/components.py` and `native/crates/bus-core/src/spike.rs`) simulates biological neural transmission using the Leaky Integrate-and-Fire model:

$$\tau_m \frac{dV(t)}{dt} = -(V(t) - V_{\text{rest}}) + R \cdot I(t)$$

- **Decaying Potential**: When a synaptic spike arrives, the neuron integrates incoming potential weighted by synaptic strength $w_{ij}$ and membrane resistance $R$.
- **Dynamic Noradrenaline Refractory Period**: Upon firing, the neuron resets its membrane potential to $V_{\text{reset}}$ and enters an absolute refractory period during which it cannot fire:
  $$t_{\text{refractory}} = t_{\text{now}} + \max(0.005, 0.04 \cdot (1.0 - 0.6 \cdot \text{Noradrenaline}))$$
  Higher noradrenaline (urgency/stress) drastically shortens refractory periods, accelerating cognitive throughput.
- **Limbic-Modulated Firing Threshold**: Firing sensitivity adapts continuously according to neurochemical levels:
  $$\theta = \max\left(0.12, \theta_{\text{base}} \cdot (1.0 - 0.45 \cdot \text{Noradrenaline}) + 0.15 \cdot \text{Cortisol}\right)$$
- **Hebbian STDP Synaptic Plasticity**: Synapses adapt dynamically according to the relative timing between pre-synaptic and post-synaptic spikes ($\Delta t = t_{\text{post}} - t_{\text{pre}}$):
  $$\Delta w = \begin{cases} A^+ e^{-\Delta t / \tau_{\text{stdp}}} \cdot R_{\text{dopamine}} & \text{if } \Delta t > 0 \quad (\text{Long-Term Potentiation / LTP}) \\ -A^- e^{\Delta t / \tau_{\text{stdp}}} & \text{if } \Delta t < 0 \quad (\text{Long-Term Depression / LTD}) \end{cases}$$

### 7-Axis Limbic Modulator & Real-Time Sensory Binding

The emotional and physiological state of the system is tracked across seven continuous neurochemical dimensions:

| Axis | Range | Modulated By | Cognitive Function |
| :--- | :---: | :--- | :--- |
| **Valence** | $[-1.0, +1.0]$ | Facial sentiment analysis (vision), conversational tone | General positivity/negativity of cognitive state |
| **Arousal** | $[0.0, 1.0]$ | Acoustic vocal stress (ear), speech cadence, urgency | Alertness and computational alertness level |
| **Dominance** | $[0.0, 1.0]$ | Command directness, confidence, authority | Conversational assertiveness |
| **Dopamine** | $[0.05, 1.0]$ | Task success, positive reinforcement, curiosity | Exploration budget and STDP LTP reward amplification |
| **Noradrenaline**| $[0.05, 1.0]$ | Environmental pressure, alarms, urgent requests | Accelerates firing rates, shortens refractory times |
| **Serotonin** | $[0.05, 1.0]$ | Conversational stability, long-term habit satisfaction | Emotional resilience and branch diversity |
| **Cortisol** | $[0.05, 1.0]$ | System errors, unverified outcomes, security threats | Constricts branch exploration, enforces strict safety gates |

#### Real-Time Sensory Binding
- **Ear / Voiceprint**: Evaluates vocal pitch tremor and spectral distribution to measure acoustic vocal stress, continuously updating `arousal` and `noradrenaline`.
- **Scene / Fusion**: Analyzes facial expressions and environmental motion to estimate `facial_valence` and `system_pressure`.
- **People / Presence**: Fuses spatial presence and biometric telemetry, broadcasting updates over `nuxiva_bus` as `biometrics.vocal_stress`, `biometrics.facial_valence`, and `biometrics.limbic_vector`.

### Global Neuronal Workspace (GNW) & GABAergic Inhibition

In `installer_wizard/features/chat/brain_chain.py`, complex queries trigger the Global Neuronal Workspace:
1. **Speculative Parallelism**: Up to 16 concurrent reasoning hypotheses are spawned across available models and internal agents.
2. **Branch Ignition**: Each branch refines its thoughts through MCTS steps, evaluated by the Digital Twin predictive critic (`predict_user_impact`).
3. **GABAergic Lateral Inhibition**: As soon as any hypothesis achieves a cumulative confidence score exceeding the ignition threshold ($\ge 0.85$), the system triggers an immediate inhibitory GABA event. Competing lagging branches are cancelled instantly via `task.cancel()`, eliminating wasted inference compute.
4. **Thought Output**: The winning branch's text, latency, and limbic snapshot are recorded and emitted.

### REM Sleep Synaptic Consolidation

During the nightly maintenance cycle (`features/vision/nightly.py` and `features/soup/trainer.py`):
- Synapses that were heavily stimulated during the day undergo homeostatic normalization:
  $$w_{t+1} = w_t \cdot \gamma + (1 - \gamma) \cdot w_{\text{baseline}}$$
- Synapses associated with emotionally salient memories (`compute_emotional_salience`) are permanently stabilized into long-term memory, preventing decay along the theoretical Ebbinghaus forgetting curve.

---

## 11. Features Catalog (72 Self-Discovered Modules)

Nuxiva includes 72 modular features located in `installer_wizard/features/`. Each feature contains a `feature.json` manifest and automatically activates in `auto` mode when compatible hardware is detected:

### Assistant & Cognitive Dialogue
- `chat`: Multi-engine conversational pipeline, GNW speculative execution, and streaming responses.
- `brain`: Cognitive engine selector, LIF neural components, priority lists, and VRAM retention.
- `mind`: Long-term memory store, semantic recall, daily journal, and Ebbinghaus retention scoring.
- `understanding`: Multi-feature phrase claim scoring, semantic intent arbitration, and contextual routing.
- `team`: Dynamic CEO Multi-Agent Orchestrator and dynamic `AgentScanner`.
- `capabilities`: Dynamic prompt generator broadcasting system abilities, MCP tools, and team roster to all models.
- `habits`: Autonomous user habit observation, proactive suggestions, and undo-based penalty feedback.
- `autonomy`: Scheduled background tasks, periodic maintenance autopilot, and proactive summaries.
- `laws`: Immutable four core laws and customizable behavioral directives injected into all reasoning prompts.
- `soup`: Model fine-tuning, weight interpolation, and offline study consolidation.
- `study`: Autonomous resting-state study: document digestion, synthetic exercise generation, and self-testing.
- `twin`: Digital Twin simulation environment; validates smart home plans before physical execution.
- `forge`: Dynamic runtime tool and widget synthesis without writing code.

### Perception & Biometrics
- `ear`: Audio input, microphone beamforming, Whisper STT, voiceprint extraction, and acoustic stress scoring.
- `voices`: Neural voice synthesis with over 600 voices in 60+ languages (Kokoro, Piper, Edge TTS).
- `voicestudio`: Optional XTTS voice cloning container with dynamic audio sample synthesis.
- `ducking`: Intelligent audio ducking: temporarily attenuates background music during speech synthesis.
- `vision`: Computer vision pipeline, YOLO object detection, VLM scene understanding, and OCR.
- `cameras`: Real-time camera feeds, RTSP/MJPEG streaming, and conversational visual queries.
- `nvr`: Network video recorder, motion alerts, MQTT event ingestion, and natural language video search.
- `scene`: 3D spatial scene graph; locates objects and furniture relative to camera viewports.
- `biometrics`: Real-time biometric fusion (vocal stress, facial sentiment, heart rate telemetry).
- `hands`: Real-time webcam hand gesture recognition (pinch, drag, swipe, zoom) via GPU.
- `people`: Face recognition, liveness verification, and spatial presence probability tracking.
- `presence`: Multi-sensor fusion determining room-by-room human occupancy.

### Smart Home & Spatial Robotics
- `home_assistant`: Bidirectional integration with Home Assistant via REST and WebSocket APIs.
- `automations`: Multi-stage visual and verbal automation builder with nested logic and branching.
- `devices`: Local device discovery (mDNS, UPnP, SSDP, Zigbee, Z-Wave).
- `bluetooth`: Bluetooth LE peripheral management, beacon scanning, and audio device pairing.
- `tv`: Smart TV discovery and control (Android TV, LG webOS, Samsung Tizen).
- `printers`: IPP Everywhere and CUPS driverless network printer management and 3D print dispatch.
- `places`: Geographic zones, geofencing, and proximity presence detection.
- `proxmox`: Native Proxmox VE hypervisor management for VMs and LXC containers.
- `rpa`: Cognitive computer automation: visual UI element detection, mouse clicking, and keyboard automation.

### Media & Knowledge
- `music`: Complete music library management, audio fingerprinting, metadata scraping, DLNA/Chromecast streaming.
- `sounds`: Sound effect soundboard and ambient auditory feedback.
- `documents`: Document analysis (PDF, DOCX, TXT), semantic indexing, and automated report generation.
- `models3d`: Parametric 3D CAD modeling, STL/OBJ generation, and interactive WebGL viewer.
- `shares`: Samba (SMB/CIFS) and NFS network shares management.
- `sports`: Real-time sports scores, league standings, and fixture notifications.
- `whiteboard`: Interactive shared 2D/3D whiteboard with live mathematical problem solving.

### System, Security & Infrastructure
- `authz`: Spatial-Temporal Role-Based Access Control (RBAC) with zone fencing and schedule gates.
- `vault`: AES-256 encrypted credentials store for cloud keys, passwords, and tokens.
- `secure`: System security posture auditing, permission verification, and intrusion mitigation.
- `firewall`: Dynamic firewall management and packet inspection.
- `netguard`: Deep packet inspection and malicious traffic prevention.
- `vpn`: Encrypted mesh VPN (WireGuard, Tailscale) configuration.
- `network`: Network interface telemetry, DNS configuration, and bandwidth monitoring.
- `kiosk`: Fullscreen display management, X11/Cage session control, and DPMS screen blanking.
- `desktop`: Multi-window widget manager and dynamic desktop canvas.
- `appearance`: UI theme management (cyberpunk, glassmorphism, dark/light modes).
- `avatars`: 3D holographic avatar customizer (wireframe, realistic, robotic).
- `nexus`: Next-gen futuristic admin cockpit and Control Deck interface.
- `nodes`: P2P mesh node discovery and edge satellite pairing via single-use tokens.
- `mcpclient`: Client connector for external Model Context Protocol (MCP) servers.
- `google`: Google Workspace integration (Gmail, Calendar, Drive, Contacts).
- `maps`: Geographic mapping, route calculation, and Points of Interest (POI) search.
- `telegram`: Bidirectional Telegram bot interface with voice message transcription and photos.
- `redalert`: Critical emergency protocol: sounds alarms, broadcasts alerts, and locks secure zones.
- `governor`: Hardware resource governor: monitors thermals, CPU load, and throttles heavy tasks.
- `scheduler`: Precision cron and event-driven task execution engine.
- `selftest`: Automated diagnostic self-testing suite verifying system health post-boot.
- `auto_update`: Automated 5-minute GitHub synchronizer with CI verification and instant rollback.

---

## 11 bis. Collaborative Intelligence, Dynamic Swarm & Triage

### Dynamic CEO Multi-Agent Orchestrator (`features/team/ceo.py`)
Nuxiva eliminates hardcoded agent lists. Every conversational turn is evaluated by the CEO Orchestrator:
- **Zero Hardcoding**: The CEO initializes with an `AgentScanner` instance that inspects physical system and user feature directories (`features/` and `/var/lib/nuxiva/features`).
- **Semantic Token Indexing**: The scanner parses manifests, docstrings, declared tools, and associated widgets, constructing a real-time semantic token index.
- **Dynamic Delegation Plan**: The CEO evaluates incoming user queries against agent keywords and tool parameters, formulating a multi-step delegation plan (`ceo_delegate`). If specialized sub-tasks are identified, the CEO delegates them to domain agents (DevOps, Coder, Home Automation, Vision, Audio, Research, Security) and synthesizes their responses into a unified answer.

### Clinical Tri-Agent Cognitive Triage (`server/features/cognitive_triage_agents/`)
For health-sensitive, psychological, or critical emergency requests, Nuxiva routes thoughts through a specialized clinical triage architecture:
1. **Medical Agent**: Evaluates symptoms, queries medical knowledge graphs, and identifies acute physiological warning signs.
2. **Psychological Agent**: Analyzes affective valence, acoustic distress, and linguistic markers to provide empathetic de-escalation and emotional support.
3. **Safety Interlock (`triage_safety_interlock`)**: Enforces non-negotiable safety guardrails. If a query suggests self-harm, medical emergencies, or dangerous physical actions, the interlock overrides standard LLM output with validated emergency protocol instructions and regional helpline contacts.

### Continuous Multimodal Surveillance & Affective Engine
- **Vision Telemetry**: Cameras continuously track movement trajectories and body language without recording raw video to disk.
- **Wearable Vitals Hub (`WearableVitalsHub`)**: Ingests real-time heart rate, SpO2, and skin temperature from paired Bluetooth smartwatches and fitness trackers.
- **Affective Fusion Engine**: Fuses vocal prosody, facial expression vectors, and vitals into a unified user affective state, allowing Nuxiva to proactively adapt its voice tone, speaking speed, and lighting ambiance.

---

## 11 ter. Interoperability & Model Context Protocol (MCP)

Nuxiva provides bidirectional enterprise interoperability via the **Model Context Protocol (MCP)**:

### Nuxiva as an MCP Server (Port 8080)
External AI assistants (e.g. Claude Desktop, Cursor, custom agents) can securely utilize Nuxiva's system tools, cameras, and IoT devices:
- **Endpoints**: `POST /mcp` and `GET /mcp` (Streamable Server-Sent Events).
- **Authentication**: Secured via revocable API tokens generated in the Admin Cockpit (`Standard` or `Full Admin` permissions).
- **Schema Export**: `GET /api/capabilities/schema/mcp` exports all available system tools with complete JSON schema signatures automatically derived from Python type annotations.

### Nuxiva as an MCP Client
Nuxiva can connect to external third-party MCP servers, dynamically discovering their declared tools and incorporating them into its internal agent tool arsenal:
- External tools are treated as untrusted data inputs: strict Zero-Trust input sanitization prevents prompt injection.
- Potentially dangerous external actions (filesystem modification, external network calls) require explicit voice or UI user confirmation.

---

## 11 quater. Music Management & Media Engine

Nuxiva includes a complete local and distributed music management engine (`features/music/`):
- **Automated Library Sorting**: Scans audio folders (`/var/lib/nuxiva/musica` or network shares), automatically organizing tracks into `Artist/Album/Track.ext`. Unrecognized files are never discarded into "unknown" folders; acoustic fingerprinting matches them against MusicBrainz, Deezer, and iTunes databases.
- **Automatic Metadata & Artwork Scraping**: Downloads high-resolution album covers, synchronized lyrics (LRC), release years, and musical genres.
- **Multi-Room Playback**: Direct playback across local audio interfaces (ALSA/PipeWire), remote DLNA/UPnP media renderers, and Google Cast / Chromecast speakers.
- **Verified Playback Outcome**: After receiving a command like *"Play Jazz in the kitchen"*, `features/agent/verify_media.py` queries the audio stream state 400ms post-execution. If playback fails to start, it retries once before reporting an explicit error.

---

## 11 quinquies. Shared Whiteboard & Spatial Projects

- **Collaborative Whiteboard (`features/whiteboard/`)**: Fullscreen interactive canvas on Port 80. Users can draw, write mathematical equations, or sketch technical designs simultaneously with Nuxiva. The assistant inspects handwriting, performs step-by-step mathematical derivations, plots function graphs, and explains solutions verbally.
- **Project Mode & Dynamic Workspaces (`server/features/project_workspace/`)**: Creates isolated persistent development sandboxes in `data/agents/<agent_id>/`. Each project maintains dedicated context memory, file access rules, terminal PTY sessions, and a virtual filesystem (VFS) with automatic code self-healing.

---

## 12. Display, Hologram & Dynamic Modular Widgets

### Dynamic Modular Widget Architecture (`server/web/widgets/`)
Dynamic widgets follow a standardized, decoupled architecture:
- **Directory Layout**: Each widget resides in its own folder containing `manifest.json` and `widget.py` (inheriting from `BaseWidget`).
- **Dynamic Discovery**: Scanned at boot and in real time by `WidgetScanner` using the native Rust `FastScanner`.
- **REST & WebSocket Endpoints**:
  - `GET /widgets`: Lists all discovered widgets, metadata, and current states.
  - `GET /widgets/{widget_id}/state`: Retrieves real-time telemetry state for a specific widget.
  - `POST /widgets/{widget_id}/action`: Dispatches user interaction actions to the widget backend.
  - `WebSocket /widgets/ws`: Real-time bidirectional streaming channel broadcasting state mutations to connected clients.
- **Reactive UI Deck (`client_web/src/features/dynamic_widgets/DynamicWidgetDeck.tsx`)**: Auto-renders responsive widget cards with live indicators, action triggers, and grid span layouts.

#### Built-in Dynamic Widgets
1. **Brain Activity (`brain_activity`)**: Visualizes real-time spiking neural network activity, firing rates, and the 7-axis limbic vector.
2. **CAD Viewer (`cad_viewer`)**: Interactive 2D/3D DXF geometry inspector with pan, zoom, and layer toggles.
3. **Quick Actions (`quick_actions`)**: One-touch execution buttons for frequent household automations, routines, and system states.
4. **Smart Switch (`smart_switch`)**: Low-latency toggle switch controlling smart plugs, relays, and room lighting.
5. **System Status (`system_status`)**: Real-time hardware telemetry: CPU utilization, RAM usage, VRAM allocation, GPU temperatures, and container status.
6. **Weather (`weather`)**: Meteorological telemetry, localized barometric pressure, weather forecasts, and air quality indices.

### 3D Hologram & Kiosk Face
- **Holographic Wireframe Orb**: Built with Three.js / WebGL, displaying an animated face that tracks the user's position in front of the camera.
- **Visual Expression**: Face geometry shifts dynamically according to the Limbic Modulator: lips synchronize smoothly with speech synthesis, eyes express curiosity, focus, or empathy, and the background subtly reflects atmospheric weather conditions.
- **Privacy Mode**: Widgets containing private personal data automatically minimize or close when the recognized user walks out of camera view.

---

## 12 bis. Dynamic Modular Agent Tools (`server/features/agent_tools/`)

All agent tools reside in dedicated subdirectories under `server/features/agent_tools/`, inheriting from `BaseAgentTool` and discovered at runtime by `ToolScanner`:

| Tool Directory | Tool ID | Description & Capabilities |
| :--- | :--- | :--- |
| `cad/` | `cad_tool` | Generates 2D/3D DXF mechanical drawings, validates geometric intersections, and exports CAD files. |
| `generator_3d/`| `generator_3d` | Synthesizes 3D mesh geometry and volumetric models from natural language descriptions. |
| `google_suite/`| `google_suite` | Integrates with Google Workspace: reads/sends emails, schedules calendar events, manages Drive files. |
| `image/` | `image_tool` | Generates synthetic imagery via diffusion models and analyzes uploaded images via VLM. |
| `maps/` | `maps_tool` | Calculates optimal driving/walking routes, estimates travel durations, and retrieves POI details. |
| `music/` | `music_tool` | Queries local library, searches online tracks, controls volume, and manages multi-room audio queues. |
| `social/` | `social_tool` | Formulates social media marketing copy, generates multi-slide carousels, and schedules publications. |
| `web_scraper/` | `web_scraper` | Executes sandboxed, headless web scraping, extracts DOM text, and filters out noise. |
| `web_search/` | `web_search` | Queries search engines and academic repositories, returning synthesized summaries with citations. |

---

## 13. Algorithms & Zero-Shot Skill Synthesis

When a user requests a task for which no existing tool or feature is qualified, Nuxiva invokes **Zero-Shot Skill Synthesis** (`server/features/skill_synthesis/`):
1. **Dynamic Tool Formulation**: The synthesizer writes a Python implementation conforming to `BaseAgentTool`.
2. **Sandbox Validation**: The code is executed inside an isolated MicroVM (Firecracker) or user-space sandbox (gVisor). A test suite verifies that inputs yield expected outputs without raising unhandled exceptions.
3. **Cryptographic Signing**: Verified tools are compiled, HMAC-SHA256 signed with `NUXIVA_SECRET_KEY`, and written to the persistent user tools directory. Unsigned or tampered tools on disk are permanently rejected.
4. **Immediate Availability**: The newly synthesized tool is immediately discovered by `ToolScanner` and made available to all agents and MCP clients without restarting services.

---

## 14. Nodes, Satellites & Proximity Radar HUD

Nuxiva coordinates a decentralized network of edge satellites and companion devices:
- **Hardware Satellites**: Compact ESP32-S3 or Raspberry Pi Zero 2W units equipped with microphone arrays and speakers running `client_satellite`.
- **Single-Use Pairing**: Satellites pair with the central server via secure one-time pairing codes generated in the Admin Cockpit (`POST /api/nodes/pair`).
- **Proximity Radar HUD**: Fuses Wi-Fi RSSI, Bluetooth LE beacon signal strengths, and camera spatial scene graphs to estimate the user's distance from each node. Spoken responses are routed dynamically to the speaker physically closest to the user.

---

## 15. Configuration: `nuxiva.env` & Auto/1/0 Architecture

Configuration resides in `/etc/nuxiva/nuxiva.env` (permissions 600, root:root). Every feature and subsystem supports three operating modes:
- `auto` (Default): Nuxiva inspects system hardware (RAM, CPU cores, VRAM, cameras, audio devices). If prerequisites are met, the feature activates automatically; otherwise, it stays dormant without throwing errors.
- `1`: Forces the feature to active. The supervisor attempts initialization regardless of hardware detection.
- `0`: Forces the feature to completely disabled. Memory and CPU overhead are zero.

> [!NOTE]
> The configuration parser safely handles variable quoting, spaces, and multi-line strings, eliminating bash expansion anomalies and environment corruption.

---

## 16. Comprehensive Environment Variable Reference

```ini
# ==============================================================================
# NUXIVA CORE & NETWORK CONFIGURATION
# ==============================================================================
NUXIVA_ENV=production                  # Environment mode: production, development, demo
NUXIVA_PORT=80                         # Display kiosk and public Web deck HTTP port
NUXIVA_ADMIN_PORT=8080                 # Administration Cockpit HTTP port
NUXIVA_SECRET_KEY=                     # 64-char HMAC secret key for token & ledger signing
NUXIVA_UI_LANG=en                      # Default UI language: en (English), it (Italian), fr (French)
NUXIVA_ASSISTANT_NAME=Nuxiva           # Spoken wake-name of the autonomous assistant

# ==============================================================================
# COGNITIVE BRAIN & REASONING ENGINES
# ==============================================================================
NUXIVA_REASONING_MODE=nuxiva-6.5-auto  # Active engine: auto, ultra, pro, empatico, veloce, legacy
NUXIVA_OLLAMA_URL=                     # Empty = local Ollama; remote URL = offload entire LLM
NUXIVA_LLM_CHAT_ORDER=                 # Priority list for Fast Chat (e.g. qwen2.5:1.5b)
NUXIVA_LLM_DEEP_ORDER=                 # Priority list for Reasoning (e.g. qwen2.5:7b, cloud:anthropic)
NUXIVA_LLM_ROUTING=auto                # Routing behavior: auto, 1 (always dual), 0 (always deep)
NUXIVA_DMN_ENABLED=1                   # Enable Default Mode Network background reflection
NUXIVA_DMN_IDLE_SECONDS=600            # Inactivity threshold (seconds) before DMN cycle fires

# ==============================================================================
# NATIVE RUST & ZERO-TRUST SECURITY
# ==============================================================================
NUXIVA_NATIVE=1                        # Enable compiled native Rust crates (bus-core, fast_scanner)
NUXIVA_SANDBOX_RUNTIME=auto            # MicroVM/Sandbox engine: auto, firecracker, gvisor, wasm
NUXIVA_RBAC_SPATIAL=1                  # Enforce Spatial-Temporal Role-Based Access Control

# ==============================================================================
# PERCEPTION & SURVEILLANCE
# ==============================================================================
NUXIVA_EAR=auto                        # Speech transcription & voiceprint biometrics (auto, 1, 0)
NUXIVA_VOICES=auto                     # Neural speech synthesis (auto, 1, 0)
NUXIVA_VISION=auto                     # Computer vision & YOLO object detection (auto, 1, 0)
NUXIVA_TWIN=enforce                    # Digital Twin simulation mode: enforce, warn, off
NUXIVA_AFFECTIVE_ENGINE=1              # Multimodal affective fusion and vitals monitoring
```

---

## 17. Network Ports, systemd Services, and File System Paths

### Network Ports

| Port | Protocol | Purpose & Accessible Services | Access Level |
| :---: | :---: | :--- | :--- |
| **80** | HTTP / WS | Interactive Display, 3D Kiosk Face, Dynamic Widget Deck, SSE Chat Stream | Public / LAN |
| **8080**| HTTP / WS | Administration Cockpit, Dynamic Widgets API, MCP Server, REST API | Authenticated (PAM / Token) |
| **11434**| HTTP | Local Ollama LLM API (when running locally) | Localhost only |
| **554** | RTSP | Internal NVR camera streaming | LAN / Secure |
| **1883**| MQTT | Internal event bus bridge for IoT sensors and smart cameras | Localhost / LAN |

### systemd Daemons

- `nuxiva-supervisor.service`: Main system supervisor, loops manager, step executor, and background updater.
- `nuxiva-core.service`: Cognitive core daemon executing Omni-Cortical reasoning engines and agent tools.
- `nuxiva-kiosk.service`: Manages the physical display X11/Cage session and fullscreen Chromium browser.
- `ollama.service`: Local neural LLM weight execution server.

### File System Layout

- `/opt/Nuxiva`: Read-only application code repository, Python sources, and compiled Rust binaries.
- `/etc/nuxiva/`: Configuration store (`nuxiva.env`, `cloud.vault`, `cloud.key`, PAM rules).
- `/var/lib/nuxiva/`: Persistent application data, episodic memory (`memoria/`), music library (`musica/`), face databases, downloaded voice packs.
- `/var/log/nuxiva/`: System execution logs (`install.log`, `supervisor.log`, `core.log`).

---

## 18. HTTP & WebSocket API Reference

All REST endpoints return JSON. Administrative endpoints require system authentication via session cookies or `Authorization: Bearer <token>` headers:

### Core Supervisor & State Endpoints
- `GET /api/state`: Returns system phase, progress percentage, active cognitive engine, and component health.
- `GET /api/setup`: Inspects onboarding status and generates setup validation tokens.
- `POST /api/setup`: Submits initial onboarding configuration parameters.
- `GET /api/bus/stream`: Server-Sent Events (SSE) stream broadcasting real-time `nuxiva_bus` events.

### Dynamic Widgets Endpoints (`/widgets`)
- `GET /widgets`: Lists all dynamically discovered widgets and their current state payloads.
- `GET /widgets/{widget_id}/state`: Retrieves the real-time state of a specific widget.
- `POST /widgets/{widget_id}/action`: Dispatches an action payload to a widget backend:
  ```json
  { "action": "toggle_switch", "payload": { "device_id": "living_room_light" } }
  ```
- `WebSocket /widgets/ws`: Bidirectional WebSocket stream for zero-latency widget state updates.

### Model Context Protocol (MCP) Endpoints
- `POST /mcp`: JSON-RPC 2.0 endpoint handling MCP tool execution, prompt retrieval, and resource listing.
- `GET /mcp`: Server-Sent Events (SSE) streaming transport for MCP sessions.
- `GET /api/capabilities/schema/mcp`: Exports complete JSON schemas of all registered agent tools.

---

## 19. Updates, Maintenance & Emergency SSH Force Upgrade

### Automated Continuous Updates
The supervisor checks GitHub every 5 minutes. If a new commit exists on `origin/main`:
1. It verifies that the commit successfully passed all Continuous Integration (CI) automated workflows.
2. It fetches the code, verifies file integrity, and applies updates to `/opt/Nuxiva`.
3. It executes post-update automated tests (14 real-world checks). If any test fails, it **instantly rolls back** to the previous working commit, ensuring zero downtime.

### Emergency SSH Force Upgrade (`nuxivactl update --force`)
If the web supervisor crashes, a container becomes unresponsive, or Git state is locked, administrators can force an immediate direct upgrade over SSH bypassing the web stack:

```bash
# Execute either command with root privileges:
sudo nuxivactl update --force
# or directly:
sudo nuxiva-upgrade
```

The script `scripts/os/force-upgrade.sh`:
- Safely configures Git safe directory permissions.
- Hard-fetches the latest commit from `origin/main`, pruning stale tags and discarding local modifications (`git reset --hard origin/main`).
- Re-synchronizes supervisor and core Python virtual environment dependencies.
- Recompiles native Rust crates if source changes are detected.
- Re-executes Alembic database migrations.
- Safely restarts `nuxiva-supervisor` and `nuxiva-core` systemd services.

---

## 20. Security, Zero-Trust Wasm & Spatial-Temporal RBAC

- **Spatial-Temporal RBAC**: Access permissions are bounded by physical space (camera/presence zones) and time schedules. A user with the `guest` role cannot unlock doors or alter heating schedules, and actions are denied outside designated hours.
- **Landlock & eBPF Sandboxing**: Egress network calls from sandboxed tools pass through the compiled Rust proxy (`native/crates/egress`), restricted by Linux Landlock to prevent DNS rebinding, socket spoofing, and unauthorized outbound connections.
- **HMAC Audit Ledger**: Every administrative configuration change and security verdict is committed to an append-only, SHA-256 HMAC-signed ledger (`ledger.log`). Modifying or truncating previous entries breaks the cryptographic hash chain, triggering an immediate security lockdown.

---

## 21. `nuxivactl` CLI Command Reference

The command-line tool `nuxivactl` allows instant management of Nuxiva from any SSH or console terminal:

```bash
# Check system status, phase, active models, and component health:
nuxivactl status

# Check for software updates on GitHub:
nuxivactl update

# Perform an emergency force-upgrade directly from GitHub (bypassing web stack):
sudo nuxivactl update --force
sudo nuxivactl force-upgrade

# Run automated system repair on corrupted packages or configurations:
sudo nuxivactl repair

# Stream live journal logs for a specific subsystem:
nuxivactl logs supervisor    # Supervisor daemon logs
nuxivactl logs core          # Cognitive core logs
nuxivactl logs install       # OS installation step logs
nuxivactl logs ollama        # Ollama LLM logs
nuxivactl logs ear           # Speech recognition logs

# Inspect background installation queue status, download speeds, and progress:
nuxivactl background

# Display the current Git commit, timestamp, and version:
nuxivactl version
```

---

## 22. Developer Guide

Nuxiva adheres strictly to Clean Architecture, decoupling core cognitive logic from infrastructure protocols and UI frameworks:

### Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/AprileNunzio/Nuxiva.git
cd Nuxiva

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r server/requirements.txt

# Build native Rust crates
cd native
cargo build --release
cd ..
```

### Coding Conventions
- **Python**: Strict typing (`mypy --strict`), formatted with `black -l 120` and linted with `flake8`. All public methods must include type hints and docstrings.
- **Rust**: Formatted with `rustfmt`, checked with `cargo clippy --all-targets -- -D warnings`. Unsafe code is strictly forbidden (`#![forbid(unsafe_code)]`).
- **TypeScript**: React 18 functional components, typed props and return types, Tailwind CSS utility styling, strict ESLint rules.

---

## 23. How to Add a Feature

1. Create a dedicated directory: `installer_wizard/features/<feature_id>/`.
2. Add a `feature.json` manifest:
   ```json
   {
     "id": "my_feature",
     "name": "My Custom Feature",
     "icon": "⚡",
     "category": "system",
     "order": 150,
     "description": "Performs custom autonomous diagnostics.",
     "capabilities": ["Custom Diagnostic Evaluation"],
     "toggle": { "env": "NUXIVA_MY_FEATURE", "apply": [] },
     "requires": { "ram_gb": 4, "gpu_vram_gb": 0, "commands": [] }
   }
   ```
3. Implement business logic in `feature.py` or modular Python files.
4. Optionally provide `api.py` (FastAPI routes) and `admin.html` / `admin.js` for cockpit integration. The supervisor automatically discovers and mounts your feature within 20 seconds.

---

## 23 bis. How to Add an Agent Tool

1. Create a folder in `server/features/agent_tools/<tool_id>/`.
2. Add `tool.py` subclassing `BaseAgentTool`:
   ```python
   from server.features.agent_tools.base import BaseAgentTool
   from server.core.scanner.base import DiscoveryManifest

   class CustomDiagnosticTool(BaseAgentTool):
       @property
       def manifest(self) -> DiscoveryManifest:
           return DiscoveryManifest(
               id="custom_diagnostic",
               name="Custom Diagnostic",
               description="Runs hardware stress diagnostics.",
               category="system",
               parameters={
                   "type": "object",
                   "properties": {
                       "target": {"type": "string", "description": "Target subsystem"}
                   },
                   "required": ["target"]
               }
           )

       async def execute(self, target: str, **kwargs):
           return {"status": "success", "target": target, "result": "nominal"}
   ```
3. `ToolScanner` automatically validates your tool via AST security checks and registers it across all cognitive reasoning engines, the CEO Orchestrator, and MCP exports.

---

## 24. How to Add a Dynamic Widget

1. Create a directory in `server/web/widgets/<widget_id>/`.
2. Create `manifest.json`:
   ```json
   {
     "id": "my_widget",
     "name": "Custom Metric Widget",
     "category": "telemetry",
     "description": "Displays live sensor telemetry.",
     "icon": "📊",
     "metadata": {
       "render_type": "card",
       "grid_span": { "col": 1, "row": 1 }
     }
   }
   ```
3. Create `widget.py` subclassing `BaseWidget`:
   ```python
   from server.web.widgets.base import BaseWidget
   from server.core.scanner.base import DiscoveryManifest

   class CustomMetricWidget(BaseWidget):
       @property
       def manifest(self) -> DiscoveryManifest:
           return DiscoveryManifest(
               id="my_widget",
               name="Custom Metric Widget",
               category="telemetry",
               description="Live sensor telemetry",
               icon="📊",
               metadata={"render_type": "card"}
           )

       async def get_state(self, user_id: str = ""):
           return {"temperature_celsius": 24.5, "status": "optimal"}

       async def execute_action(self, action: str, payload: dict):
           if action == "reset":
               return {"status": "reset_complete"}
           return {"status": "unsupported"}
   ```
4. `WidgetScanner` discovers your widget immediately, mounting REST routes and streaming state updates over `/widgets/ws`.

---

## 25. How to Add an Installation Step

1. Add a numbered shell script to `scripts/os/steps/` (e.g. `scripts/os/steps/75-custom.sh`).
2. Make it executable (`chmod +x`) and ensure idempotency:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   source /opt/Nuxiva/scripts/os/lib.sh

   step_title "Configuring Custom Service"

   if [ -f /etc/custom_service.conf ]; then
       log_ok "Custom service already configured, skipping."
       exit 0
   fi

   # Installation logic...
   touch /etc/custom_service.conf
   log_ok "Custom service successfully deployed."
   ```
3. Add the step entry to `installer_wizard/backend/steps.py` to expose it in the supervisor catalog.

---

## 26. Testing and Continuous Integration

Nuxiva maintains a comprehensive testing regime covering unit, integration, neuro-biological, and cross-platform verification:

```bash
# Run supervisor and installer wizard unit tests:
cd /opt/Nuxiva/installer_wizard
pytest -v tests/

# Run Nuxiva Core cognitive kernel and reasoning engine tests:
cd /opt/Nuxiva/server
pytest -v tests/

# Run Rust crate tests (bus-core, spike, fast_scanner, egress):
cd /opt/Nuxiva/native
cargo test --all
```

CI workflows in `.github/workflows/` run on every pull request and push to `main`. Commits are only released to production if 100% of the test suite passes.

---

## 27. Clients: Web, Android, and Edge Satellites

1. **React Web Deck (`client_web`)**:
   - Modern React 18 SPA built with Vite, TypeScript, Tailwind CSS, and Three.js.
   - Interactive 3D visualizers, Control Deck, DynamicWidgetDeck, and full internationalization.
2. **Android APK (`client_apk`)**:
   - Native Kotlin Android client with wake-word detection, local audio streaming, camera feeds, and push alerts.
3. **Hardware Satellites (`client_satellite`)**:
   - Micro-daemon for low-power edge nodes (ESP32-S3 / Raspberry Pi), enabling whole-home voice coverage and ambient proximity radar tracking.

---

## 28. Troubleshooting & Diagnostics

| Symptom | Probable Cause | Corrective Action |
| :--- | :--- | :--- |
| Kiosk screen blank on Port 80 | Display manager or X11/Cage issue | Inspect `journalctl -u nuxiva-kiosk -n 100`. Verify `xhost` permissions and GPU acceleration in `scripts/os/steps/33-display-driver.sh`. |
| Supervisor unresponsive on Port 8080 | Frozen process or lock file | Run `sudo nuxivactl update --force` or `sudo systemctl restart nuxiva-supervisor`. |
| Local LLM answers slowly (> 5s) | Inferring on CPU instead of GPU | Verify CUDA availability: `nvidia-smi`. Check model size in `Brain -> Models`; choose a lighter quant (e.g. 1.5B or 3B). |
| Dynamic widget not appearing in Deck | Syntax error in `widget.py` or invalid manifest | Run `python -m server.tests.test_widget_scanner` to view AST validation errors. Ensure class inherits from `BaseWidget`. |
| Emergency recovery required | Broken package or interrupted upgrade | Run `sudo nuxivactl repair` followed by `sudo nuxivactl update --force`. |

---

## 29. Frequently Asked Questions (FAQ)

**Q: Can Nuxiva run completely offline without an internet connection?**  
A: Yes. Once initial installation steps and local model downloads are complete, Nuxiva operates 100% locally. Speech recognition, neural reasoning, smart home controls, and vision telemetry require zero internet access.

**Q: How does Nuxiva prevent destructive actions (e.g. unlocking doors by voice)?**  
A: High-risk physical actions pass through Byzantine Consensus juries and deterministic safety interlocks. Actions involving locks, security arming, or valve controls require physical confirmation or voiceprint biometric authentication.

**Q: Can I use cloud models alongside local models?**  
A: Absolutely. Nuxiva allows arbitrary mixing in priority lists: for instance, using a local 1.5B model for instant chat and delegating complex reasoning queries to Claude 3.5 Sonnet or OpenAI o-series via encrypted API keys.

---

## 30. Contributing, License, and Credits

Nuxiva is an independent open-source operating system engineered by **Nunzio Aprile (NunzioTech)** and released under the **MIT License**.

- **Contributions**: Contributions, bug reports, and pull requests are welcomed! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and adhere to our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- **Security Inquiries**: Report security vulnerabilities privately following [SECURITY.md](SECURITY.md).
- **Donations**: Support independent open-source AI development at [paypal.me/NunzioAprile](https://www.paypal.com/paypalme/NunzioAprile).

*Designed and developed with passion by NunzioTech for an open, private, and intelligent future.*
