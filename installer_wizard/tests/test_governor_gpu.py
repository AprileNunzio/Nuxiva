from features.desktop.manifest import clean_cost
from features.governor import gpu
from features.governor.devices import clean_report


def test_estimate_kinds():
    assert gpu.estimate(gpu.clean_gpu({"renderer": "llvmpipe (LLVM 15)"}))["kind"] == "software"
    assert gpu.estimate(gpu.clean_gpu({"renderer": "NVIDIA GeForce RTX 3060", "device_memory": 16}))["vram_mb"] >= 4096
    assert gpu.estimate(gpu.clean_gpu({"renderer": "Mali-G78", "device_memory": 8}))["kind"] == "mobile"
    assert gpu.estimate(gpu.clean_gpu({"renderer": "Intel(R) UHD Graphics 620", "device_memory": 8}))["kind"] == "integrated"


def test_clean_gpu_rejects_injection():
    out = gpu.clean_gpu({"renderer": "<script>alert(1)</script>", "device_memory": 1e9, "webgpu": "yes"})
    assert out["renderer"] == "" and out["device_memory"] == 64 and out["webgpu"] is False
    assert gpu.clean_gpu("x") == {}


def test_budget_scales_with_memory_and_tier():
    assert gpu.budget(256, "full", False) < gpu.budget(4096, "full", False) < gpu.budget(16384, "full", False)
    assert gpu.budget(4096, "minimal", False) < gpu.budget(4096, "full", False)
    assert gpu.budget(4096, "full", True) < gpu.budget(4096, "full", False)
    assert gpu.budget(0, "minimal", True) >= 2


def test_weight_uses_declared_cost_and_measure():
    assert gpu.weight(None, "s", None) < gpu.weight(None, "l", None)
    assert gpu.weight({"gpu": 8, "cpu": 8}, "s", None) == 8
    assert gpu.weight({"gpu": 2, "cpu": 2}, "m", 80) > gpu.weight({"gpu": 2, "cpu": 2}, "m", None)
    assert clean_cost({"gpu": 99, "cpu": "x"}) == {"gpu": 8.0, "cpu": 2.0}
    assert clean_cost("bad") is None


def test_report_carries_clean_gpu():
    clean = clean_report({"device": "abcdef12", "gpu": {"renderer": "Adreno 740", "cores": 8}})
    assert clean["gpu"]["renderer"] == "Adreno 740"
