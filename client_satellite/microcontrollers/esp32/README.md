# Nuxiva ESP32 firmware

Firmware for ESP32-S3 nodes: I2S microphone (INMP441, 16 kHz), relays, signed requests, signed OTA.

## Status

Verified in CI: host tests of the portable core (ASan/UBSan) and a PlatformIO build. Not yet proven on a real board.

## Flow

1. Upload: `pio run -t upload` from this directory. Set the release public key with `NUXIVA_FW_PUBKEY_HEX` in `PLATFORMIO_BUILD_FLAGS`.
2. Provision: connect the board by USB to the server and use Nodes, Install a node, ESP32. The server sends Wi-Fi, host and the pinned CA over serial. The board generates its own Ed25519 key in NVS and enrolls with its public key. The administrator confirms the pairing.
3. Runtime: every request is signed with the device key (same canonical form as node-core). TLS is pinned to the provisioned CA. Audio streams over WSS to `/ws/ear`; the server runs wake word and speaker verification.
4. Relays: the node declares the `relay` capability. The administrator calls `POST /api/nodes/{id}/relay`; the node polls its inbox. Relays have a maximum on time (default 1 h) and switch off after 5 minutes without server contact.
5. Update: `python scripts/esp32_sign_release.py` signs the image and writes `manifest.json` and `image.bin` into the server firmware directory. The device checks signature, monotonic version and SHA-256 before finishing the update.

## Tests

`bash test/host/run.sh`

## Wake word

Own template detector (crate `wakeword-core`). Enroll with `POST /api/ear/wake-template` (3-10 base64 takes). On Android place the `.nxwk` model in the app files directory as `wakeword.nxwk` and build the library with `scripts/android/build_wakeword.sh`.
