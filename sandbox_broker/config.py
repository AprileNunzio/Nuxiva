import os
from dataclasses import dataclass

_SANDBOX_UID = 65534


@dataclass(frozen=True)
class BrokerConfig:
    socket_path: str = "/run/nuxiva/sandbox/broker.sock"
    work_dir: str = "/var/lib/nuxiva/sandbox/work"
    env_file: str = "/etc/nuxiva/nuxiva.env"
    image: str = "nuxiva-sandbox:local"
    docker_bin: str = "docker"
    max_concurrent: int = 2
    queue_wait_seconds: int = 10
    max_body_bytes: int = 12 * 1024 * 1024
    probe_interval_seconds: int = 300
    probe_timeout_seconds: int = 90
    sandbox_uid: int = _SANDBOX_UID
    container_prefix: str = "nuxiva-sbx-"
    egress_network: str = "nuxiva-sbx"
    egress_bridge: str = "nuxiva-sbx0"
    egress_subnet: str = "172.29.240.0/24"
    egress_gateway: str = "172.29.240.1"
    egress_ports: tuple = (38000, 38099)
    egress_bin: str = "/opt/nuxiva-native/bin/nuxiva-egress"
    firecracker_bin: str = "/usr/local/bin/firecracker"
    firecracker_dir: str = "/var/lib/nuxiva/firecracker"
    kvm_device: str = "/dev/kvm"

    @classmethod
    def from_env(cls) -> "BrokerConfig":
        defaults = cls()
        return cls(
            socket_path=os.environ.get("NUXIVA_SANDBOX_SOCKET", defaults.socket_path),
            work_dir=os.environ.get("NUXIVA_SANDBOX_WORK", defaults.work_dir),
            env_file=os.environ.get("NUXIVA_ENV_FILE", defaults.env_file),
            image=os.environ.get("NUXIVA_SANDBOX_IMAGE", defaults.image),
            egress_bin=os.environ.get("NUXIVA_EGRESS_BIN", defaults.egress_bin),
            firecracker_bin=os.environ.get("NUXIVA_FIRECRACKER_BIN", defaults.firecracker_bin),
            firecracker_dir=os.environ.get("NUXIVA_FIRECRACKER_DIR", defaults.firecracker_dir),
            max_concurrent=int(os.environ.get("NUXIVA_SANDBOX_CONCURRENCY", defaults.max_concurrent)),
        )
