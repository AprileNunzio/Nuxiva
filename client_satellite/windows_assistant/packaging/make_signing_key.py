import base64
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> int:
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    print("NUXIVA_ASSISTANT_SIGNING_KEY=" + base64.b64encode(private).decode("ascii"))
    print("PUBLIC_KEY=" + base64.b64encode(public).decode("ascii"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
