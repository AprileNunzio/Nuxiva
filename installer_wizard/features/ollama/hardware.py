import os
import platform
import subprocess
from typing import Optional

import psutil

from .types import CpuSpecs, GpuSpecs, HardwareProfile, MemorySpecs


def _detect_cpu_flags() -> tuple[bool, bool]:
    has_avx2 = False
    has_avx512 = False
    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                content = f.read().lower()
                has_avx2 = "avx2" in content
                has_avx512 = "avx512" in content
        except OSError:
            pass
    elif platform.system() == "Windows":
        has_avx2 = True
    return has_avx2, has_avx512


def detect_cpu() -> CpuSpecs:
    physical = psutil.cpu_count(logical=False) or 2
    logical = psutil.cpu_count(logical=True) or physical
    model = platform.processor() or "Generic Processor"
    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("model name"):
                        model = line.split(":", 1)[1].strip()
                        break
        except OSError:
            pass
    avx2, avx512 = _detect_cpu_flags()
    return CpuSpecs(
        model=model,
        physical_cores=max(1, physical),
        logical_cores=max(1, logical),
        has_avx2=avx2,
        has_avx512=avx512,
    )


def detect_memory() -> MemorySpecs:
    vm = psutil.virtual_memory()
    total_gb = round(vm.total / (1024**3), 2)
    available_gb = round(vm.available / (1024**3), 2)
    return MemorySpecs(
        total_bytes=vm.total,
        total_gb=total_gb,
        available_gb=available_gb,
    )


def detect_gpu() -> Optional[GpuSpecs]:
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            first_line = proc.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in first_line.split(",")]
            if len(parts) >= 3:
                name = parts[0]
                total_mb = float(parts[1])
                free_mb = float(parts[2])
                return GpuSpecs(
                    name=name,
                    vram_total_gb=round(total_mb / 1024.0, 2),
                    vram_free_gb=round(free_mb / 1024.0, 2),
                    backend="cuda",
                    is_supported=True,
                )
    except (OSError, ValueError, subprocess.SubprocessError):
        pass

    try:
        proc = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
            check=False,
        )
        if proc.returncode == 0 and "Total" in proc.stdout:
            return GpuSpecs(
                name="AMD ROCm Device",
                vram_total_gb=8.0,
                vram_free_gb=6.0,
                backend="rocm",
                is_supported=True,
            )
    except (OSError, subprocess.SubprocessError):
        pass

    return None


def calculate_hardware_profile() -> HardwareProfile:
    cpu = detect_cpu()
    mem = detect_memory()
    gpu = detect_gpu()

    has_gpu = gpu is not None and gpu.is_supported and gpu.vram_total_gb >= 4.0
    vram_gb = gpu.vram_total_gb if gpu else 0.0

    if (has_gpu and vram_gb >= 12.0) or (mem.total_gb >= 32.0 and has_gpu) or mem.total_gb >= 48.0:
        tier = "enterprise"
        parallel = 4
        ctx = 16384
        max_tokens = 4096
        loaded_models = 3
        flash_attn = True
    elif (has_gpu and vram_gb >= 6.0) or mem.total_gb >= 16.0:
        tier = "balanced"
        parallel = 2
        ctx = 8192
        max_tokens = 4096
        loaded_models = 2
        flash_attn = True
    else:
        tier = "lightweight"
        parallel = 2
        ctx = 4096
        max_tokens = 2048
        loaded_models = 1
        flash_attn = cpu.has_avx2

    recommended_threads = max(1, min(cpu.physical_cores, 16))

    return HardwareProfile(
        tier=tier,
        cpu=cpu,
        memory=mem,
        gpu=gpu,
        recommended_parallel=parallel,
        recommended_context=ctx,
        recommended_max_tokens=max_tokens,
        recommended_loaded_models=loaded_models,
        recommended_flash_attention=flash_attn,
        recommended_threads=recommended_threads,
    )
