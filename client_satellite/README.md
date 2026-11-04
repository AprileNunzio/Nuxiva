# Nuxiva Satellite Clients

This folder contains the lightweight client software meant to run on distributed satellite nodes. A satellite node is a remote microphone/speaker unit that streams audio to the central Nuxiva Server.

## Architectures Supported

### 1. `microcontrollers/` (ESP32, ESP32-S3, Arduino)
Designed for extreme low-cost setups (~10€).
- Requires an I2S Microphone (e.g., INMP441).
- Requires an I2S Amplifier/Speaker (e.g., MAX98357A).
- Uses **PlatformIO** and Arduino/ESP-IDF framework.
- Automatically provisioned and flashed via USB by the Nuxiva Server, then updated Over-The-Air (OTA) via Wi-Fi.

### 2. `linux_edge/` (Raspberry Pi, Orange Pi, Generic Linux)
Designed for slightly more powerful setups where you might already have a Raspberry Pi running in another room.
- Can use standard USB microphones and 3.5mm/HDMI audio output.
- Runs a lightweight Python client (`satellite.py`).
- Nuxiva Server can provision this automatically over SSH.

### 3. `nuxiva-satellite` (Rust, any Linux board)
A single native binary (`native/crates/satellite-core`) for ARM64, ARMv7, x86-64 and RISC-V boards. It is the
recommended agent for new satellites and replaces `linux_edge/satellite.py` wherever it can be installed.

- **Board discovery:** reads the device tree or DMI to identify the SoC (Rockchip, Broadcom/Raspberry Pi, NVIDIA Jetson,
  Amlogic, Allwinner, Qualcomm, MediaTek, NXP, Sophgo, StarFive, Intel, AMD...), the CPU features (NEON, dot product,
  i8mm, SVE, AVX2, AVX-VNNI, RVV) and the peripherals (microphones, speakers, webcams with infrared detection,
  Bluetooth, GPIO, I2C, USB).
- **Accelerator backends:** RKNN (vendor `rknpu` and mainline `rocket`), CUDA/TensorRT (Jetson and desktop GPUs),
  ROCm, Hailo, Coral Edge TPU (USB and PCIe), Intel NPU (OpenVINO), AMD XDNA, Qualcomm Hexagon (QNN), MediaTek APU,
  VeriSilicon NPU (i.MX 8M Plus, A311D), Sophgo TPU, Arm Ethos and any GPU with Vulkan/OpenCL. A backend counts as
  *ready* only when both the device and its runtime library are present.
- **Offload plan:** for each task (wake word, VAD, speech-to-text, text-to-speech, vision, small LLM) it picks the best
  ready accelerator, falls back to the CPU when the board is strong enough, and otherwise leaves the task to the
  central server. The plan and the missing runtimes are reported in every heartbeat and shown in the Nodes panel.
- **Any other chip:** drop a JSON descriptor in `/etc/nuxiva/accelerators.d/`. Descriptors are strictly validated
  (device paths only under `/dev`, plain library names, no unknown fields) and can override a built-in backend:

```json
{
  "id": "kendryte-kpu",
  "vendor": "Canaan",
  "kind": "npu",
  "devices": ["/dev/kpu0"],
  "runtimes": ["libnncase.so"],
  "tasks": ["wake_word", "vad", "vision"],
  "priority": 90
}
```

- **Zero-Trust link:** HTTPS only. The enrollment file (Nodes panel, *satellite enrollment*) carries a single-use
  token and the SHA-256 pin of the Nuxiva CA; the agent refuses a CA with a different pin and a server certificate not
  signed by that CA. The node token is stored encrypted with AES-256-GCM, with a key bound to `/etc/machine-id`, in
  `0600` files.
- **Hardened service:** `sudo nuxiva-satellite install-service --file nuxiva-satellite-enroll.json --name Salotto`
  installs a systemd unit with `DynamicUser`, `ProtectSystem=strict`, no capabilities and a system call filter. The
  enrollment is redeemed on first start through a systemd credential.

```bash
nuxiva-satellite probe                    # print the hardware profile and the offload plan
sudo nuxiva-satellite install-service --file nuxiva-satellite-enroll.json --name "Salotto" --room "Salotto"
```

Extra runtime folders can be listed in `NUXIVA_RUNTIME_PATH` (colon separated, absolute paths).

## Auto-Provisioning
You do not need to manually edit code to set Wi-Fi credentials or the Server IP. The `satellite_manager` in the Nuxiva Core handles dynamic compilation and flashing automatically.

## Edge routing (ESP32)

The ESP32 firmware runs a C++ port of the server's System 1 router (`src/edge_router.cpp`) on the transcript it
receives, so confident direct home actions go straight to the supervisor's lean `/api/nodes/intent` path and skip
the core round trip. Everything else, and anything below `NUXIVA_EDGE_THRESHOLD`, goes to `/api/nodes/chat`.
The supervisor never trusts the satellite's verdict: it re-parses the text, applies the laws guard and still asks
for confirmation on sensitive actions.

- `src/edge_router_model.h` is generated from the server router: `python -m server.core.orchestrator.edge_export`.
  `server/tests/test_edge_router.py` fails when it is stale and checks that the C++ and Python decisions match.
- Transport: put the supervisor CA in `src/nuxiva_ca.h` as `#define NUXIVA_CA_PEM "..."` and use an `https://`
  `NUXIVA_SUPERVISOR_URL`. Without it the firmware refuses to send the node token unless built with
  `-D NUXIVA_ALLOW_PLAINTEXT`.
- Transcripts currently arrive on the serial port (one line per utterance); on-device speech recognition is the
  next step and only needs to call `submit_transcript()`.
