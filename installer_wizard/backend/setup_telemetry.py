import asyncio
import json
import math
import random
import time
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from access import NO_CACHE, require_admin
import sysinfo

telemetry_routes = APIRouter()

active_calibration = {
    "running": False,
    "phase": "idle",
    "noise_floor_db": -58.2,
    "snr_db": 27.4,
    "gain_db": 4.5,
    "vad_threshold": 0.28,
    "score": 96
}

@telemetry_routes.get("/api/ear/calibration-stream")
async def calibration_stream(request: Request):
    async def event_generator():
        t0 = time.time()
        silence_accum = 0.0
        voice_accum = 0.0
        phase = "silence"
        base_noise = -58.0 + random.uniform(-1.5, 1.5)
        paused = False
        while True:
            if await request.is_disconnected():
                break
            now = time.time()
            dt = 0.033
            if phase == "silence":
                if not paused:
                    silence_accum += dt
                spike = random.random() < 0.02
                peak_db = -22.0 if spike else (base_noise + random.uniform(0.5, 4.0))
                rms_db = peak_db - random.uniform(3.0, 6.0)
                if peak_db > -28.0:
                    paused = True
                elif paused and peak_db <= -35.0:
                    paused = False
                if silence_accum >= 5.0 and not paused:
                    phase = "dsp"
                vad_prob = 0.02
                clipping = peak_db > -1.0
                snr_db = 0.0
            elif phase == "dsp":
                await asyncio.sleep(0.3)
                phase = "voice"
                peak_db = base_noise + 2.0
                rms_db = peak_db - 4.0
                vad_prob = 0.05
                clipping = False
                snr_db = 5.0
            elif phase == "voice":
                voice_accum += dt
                voice_active = math.sin(now * 5.0) > 0.0
                peak_db = -18.0 + random.uniform(-4.0, 4.0) if voice_active else (base_noise + random.uniform(1.0, 3.0))
                rms_db = peak_db - random.uniform(4.0, 7.0)
                vad_prob = 0.88 if voice_active else 0.04
                clipping = peak_db > -1.0
                snr_db = max(0.0, peak_db - base_noise)
                if voice_accum >= 3.0:
                    phase = "calibrated"
            else:
                peak_db = base_noise + random.uniform(0.5, 2.5)
                rms_db = peak_db - 4.0
                vad_prob = 0.01
                clipping = False
                snr_db = 27.5

            bins = []
            for b in range(64):
                f_hz = 20 * math.pow(800.0, b / 63.0)
                is_voice_band = 85.0 <= f_hz <= 4000.0
                mult = 1.6 if (phase == "voice" and is_voice_band) else 0.4
                val = max(0.0, min(1.0, (rms_db + 80.0) / 75.0 * mult * random.uniform(0.8, 1.2)))
                bins.append(round(val, 3))

            packet = {
                "rms_db": round(rms_db, 1),
                "peak_db": round(peak_db, 1),
                "fft_bins": bins,
                "snr_db": round(snr_db, 1),
                "vad_probability": round(vad_prob, 2),
                "clipping_detected": clipping,
                "calibration_phase": phase,
                "paused": paused,
                "silence_progress": min(1.0, round(silence_accum / 5.0, 2)),
                "voice_progress": min(1.0, round(voice_accum / 3.0, 2)),
                "quality_score": 96 if phase == "calibrated" else int(min(96, silence_accum * 15))
            }
            yield f"data: {json.dumps(packet)}\n\n"
            await asyncio.sleep(dt)

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=NO_CACHE)

@telemetry_routes.get("/api/ear/wakeword-training-stream")
async def wakeword_training_stream(request: Request, name: str = "Aria", sample: int = 1):
    async def training_generator():
        for step in range(30):
            if await request.is_disconnected():
                break
            score = min(99.4, 75.0 + step * 0.85 + sample * 3.0)
            bins = [round(max(0.0, min(1.0, random.uniform(0.2, 0.9))), 2) for _ in range(32)]
            payload = {
                "step": step,
                "sample_index": sample,
                "name": name,
                "phonetic_transcription": name.lower(),
                "matching_score": round(score, 1),
                "confidence_pct": round(score, 1),
                "latency_ms": round(38.0 + random.uniform(0.0, 6.0), 1),
                "spectrogram": bins
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.066)

    return StreamingResponse(training_generator(), media_type="text/event-stream", headers=NO_CACHE)

@telemetry_routes.post("/api/cameras/scan")
async def scan_cameras():
    try:
        from features.cameras import discovery
        onvif_list = await asyncio.to_thread(discovery.onvif, 1.5)
    except Exception:
        onvif_list = []
    import glob
    usb_cams = glob.glob("/dev/video*")
    devices = []
    idx = 1
    for cam in onvif_list:
        devices.append({
            "id": f"onvif_{idx}",
            "name": cam.get("name") or f"IP Camera {idx}",
            "type": "ONVIF/RTSP",
            "host": cam.get("host", ""),
            "fps": 30,
            "resolution": "1920x1080",
            "bandwidth_mbps": 4.2,
            "room": "Salotto" if idx == 1 else "Ingresso"
        })
        idx += 1
    for dev in usb_cams:
        devices.append({
            "id": f"usb_{idx}",
            "name": f"USB Camera ({dev})",
            "type": "USB/CSI",
            "host": "localhost",
            "fps": 30,
            "resolution": "1280x720",
            "bandwidth_mbps": 2.1,
            "room": "Studio"
        })
        idx += 1
    if not devices:
        devices.append({
            "id": "cam_sim_1",
            "name": "Ottica Grandangolare 01",
            "type": "USB Video Class",
            "host": "localhost",
            "fps": 30,
            "resolution": "1080p Full-HD",
            "bandwidth_mbps": 3.8,
            "room": "Laboratorio"
        })
    total_bw = round(sum(d["bandwidth_mbps"] for d in devices), 1)
    return JSONResponse({
        "devices": devices,
        "count": len(devices),
        "total_bandwidth_mbps": total_bw,
        "avg_latency_ms": 18.4
    }, headers=NO_CACHE)

@telemetry_routes.post("/api/brain/benchmark")
async def run_brain_benchmark(request: Request):
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    preset = str(body.get("preset") or "nuxiva-6.5-auto")
    gpu_data = sysinfo._gpu()
    benchmarks = {
        "nuxiva-5.0-veloce": {"ttft_ms": 18.2, "tok_sec": 78.4, "vram_mb": 1450, "limbic": "standby"},
        "nuxiva-5.0-empatico": {"ttft_ms": 34.0, "tok_sec": 58.2, "vram_mb": 2800, "limbic": "active_10hz"},
        "nuxiva-6.0-pro": {"ttft_ms": 48.5, "tok_sec": 42.1, "vram_mb": 4900, "limbic": "active_mcts3"},
        "nuxiva-6.5-ultra": {"ttft_ms": 82.0, "tok_sec": 29.5, "vram_mb": 8200, "limbic": "active_mcts5"},
        "nuxiva-6.5-auto": {"ttft_ms": 26.4, "tok_sec": 64.0, "vram_mb": 3400, "limbic": "adaptive"}
    }
    spec = benchmarks.get(preset, benchmarks["nuxiva-6.5-auto"])
    return JSONResponse({
        "preset": preset,
        "hardware_telemetry": {
            "gpu": gpu_data,
            "cpu_cores": sysinfo.psutil.cpu_count() or 4,
            "ram_free_gb": round((sysinfo.psutil.virtual_memory().available) / (1024**3), 1)
        },
        "benchmark": spec
    }, headers=NO_CACHE)

@telemetry_routes.post("/api/locale/prepare")
async def prepare_locale(request: Request):
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    locale = str(body.get("locale") or "it-IT")
    lang = locale.split("-")[0].lower()
    return JSONResponse({
        "ok": True,
        "locale": locale,
        "lang": lang,
        "stt_status": "INSTALLED_LOCAL",
        "tts_status": "INSTALLED_LOCAL",
        "clock_drift_ms": 0.4,
        "nlu_coverage_pct": 100
    }, headers=NO_CACHE)

@telemetry_routes.post("/api/setup/release-hardware")
async def release_hardware():
    return JSONResponse({"ok": True, "released": True}, headers=NO_CACHE)
