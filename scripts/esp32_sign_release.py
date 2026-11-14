import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

MAX_BYTES = 3 * 1024 * 1024
VERSION_RE = re.compile(r"^[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}$")
SEED_RE = re.compile(r"^[0-9a-f]{64}$")


def message(version: str, size: int, sha256: str) -> bytes:
    return f"nuxiva-fw-v1\n{version}\n{size}\n{sha256}".encode("ascii")


def load_key(seed_hex: str) -> Ed25519PrivateKey:
    if not SEED_RE.fullmatch(seed_hex):
        raise ValueError("seed must be 64 lowercase hex characters")
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))


def public_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def sign(image: bytes, version: str, key: Ed25519PrivateKey) -> dict:
    if not VERSION_RE.fullmatch(version):
        raise ValueError("version must be MAJOR.MINOR.PATCH")
    if not 0 < len(image) <= MAX_BYTES:
        raise ValueError("image size out of range")
    digest = hashlib.sha256(image).hexdigest()
    return {"version": version, "size": len(image), "sha256": digest,
            "sig": key.sign(message(version, len(image), digest)).hex()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--seed-file", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        key = load_key(args.seed_file.read_text(encoding="ascii").strip())
        manifest = sign(args.image.read_bytes(), args.version, key)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "image.bin").write_bytes(args.image.read_bytes())
    (args.out / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")), encoding="ascii")
    print(public_hex(key))
    return 0


if __name__ == "__main__":
    sys.exit(main())
