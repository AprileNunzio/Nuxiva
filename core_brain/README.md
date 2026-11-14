# core_brain

Central Rust engine of Nuxiva. It reuses the existing crates instead of duplicating them: `context-core` for the hot per-person memory, `ear-core` for echo cancellation and the voice book, `agent-core` for agent selection, `swarm-core` for supervision and execution, and `mcp-core` for tool discovery, permissions, consent and audit.

## Flow

1. Audio frames go through echo cancellation, speaker verification and a semantic gatekeeper. Unknown or ambiguous voices are dropped.
2. Transcripts and speaker verdicts already produced by the ear service are read over its loopback WebSocket. Only loopback endpoints are accepted, and only a known speaker is trusted as a principal; anyone else is a guest without permissions.
3. The accepted utterance is routed to an agent, planned by the swarm supervisor and executed by workers that call tools discovered at runtime through the MCP hub. Tool output is treated as untrusted external data.
4. Errors and panics become fault events. They never stop listening.

## Configuration

| Variable | Purpose |
| --- | --- |
| `NUXIVA_AGENTS_DIR` | Agents directory (required). |
| `NUXIVA_MCP_CATALOG` and `NUXIVA_MCP_PUBLIC_KEY` | Signed MCP catalogue and hex public key. Both or neither. The signature, expiry and serial are verified. |
| `NUXIVA_EAR_PORT` | Port of the ear service on loopback. |
| `NUXIVA_MODEL_DIR` | Where the speaker model is stored. |
| `NUXIVA_WAKE_NAMES` | Comma-separated wake names. |

## Speaker model

The speaker embedding model is not stored in the repository. On first start it is downloaded over HTTPS, its size and SHA-256 are checked before it is written and again at every load, and the engine refuses to start if it is missing or altered. It runs with `tract-onnx`, so no native library is needed.

The model is WeSpeaker ResNet34 (VoxCeleb), redistributed by the sherpa-onnx project. The licence of the weights, which were trained on VoxCeleb, must be confirmed before any commercial use.

## Development

```
cd native
cargo test -p nuxiva-core-brain
```

Set `NUXIVA_TEST_MODEL_DIR` to a directory that holds the model to also run the test with the real model.
