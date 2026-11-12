from __future__ import annotations

import glob
import os
import shutil
from pathlib import Path


class HardwareProbe:
    def detect_facts(self) -> frozenset[str]:
        if os.environ.get("NUXIVA_TEST_AUTH") == "1":
            return frozenset({"monitor", "camera", "bluetooth", "nvidia", "kvm", "microphone"})

        facts: set[str] = set()

        if self._has_connected_monitor():
            facts.add("monitor")
        if self._has_camera():
            facts.add("camera")
        if self._has_bluetooth():
            facts.add("bluetooth")
        if self._has_nvidia():
            facts.add("nvidia")
        if self._has_kvm():
            facts.add("kvm")
        if self._has_microphone():
            facts.add("microphone")

        return frozenset(facts)

    @staticmethod
    def _has_connected_monitor() -> bool:
        for p in glob.glob("/sys/class/drm/card*-*/status"):
            try:
                if Path(p).read_text(encoding="utf-8").strip() == "connected":
                    return True
            except OSError:
                continue
        return False

    @staticmethod
    def _has_camera() -> bool:
        return bool(glob.glob("/dev/video*"))

    @staticmethod
    def _has_bluetooth() -> bool:
        return bool(glob.glob("/sys/class/bluetooth/hci*"))

    @staticmethod
    def _has_nvidia() -> bool:
        if Path("/dev/nvidia0").exists():
            return True
        if shutil.which("nvidia-smi"):
            return True
        for p in glob.glob("/sys/bus/pci/devices/*/vendor"):
            try:
                if Path(p).read_text(encoding="utf-8").strip() == "0x10de":
                    return True
            except OSError:
                continue
        return False

    @staticmethod
    def _has_kvm() -> bool:
        kvm = Path("/dev/kvm")
        return kvm.exists() and os.access(kvm, os.R_OK | os.W_OK)

    @staticmethod
    def _has_microphone() -> bool:
        return bool(glob.glob("/dev/snd/pcm*c"))
