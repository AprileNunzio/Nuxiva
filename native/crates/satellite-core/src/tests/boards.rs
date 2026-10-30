use super::{Fixture, base, camera, microphone_and_speaker};
use crate::backends::Task;
use crate::backends::{Accelerator, Kind, builtin};
use crate::plan::{Placement, Plan, plan};
use crate::probe::{Profile, profile};

fn placement(plan: &Plan, task: Task) -> Option<Placement> {
    plan.steps
        .iter()
        .find(|s| s.task == task)
        .map(|s| s.placement.clone())
}

fn accel<'a>(found: &'a Profile, id: &str) -> Option<&'a Accelerator> {
    found.accelerators.iter().find(|a| a.id == id)
}

fn edge(id: &str) -> Placement {
    Placement::Edge {
        backend: id.to_owned(),
    }
}

#[test]
fn rockchip_rk3588_uses_the_npu_for_listening_vision_and_llm() -> Result<(), String> {
    let fx = Fixture::new("rk3588")?;
    base(&fx, 8, 16 * 1024 * 1024)?;
    microphone_and_speaker(&fx)?;
    camera(&fx, "USB 2.0 Camera")?;
    fx.file(
        "/proc/device-tree/compatible",
        "radxa,rock-5b\0rockchip,rk3588\0",
    )?
    .file("/proc/device-tree/model", "Radxa ROCK 5B\0")?
    .link(
        "/sys/class/drm/renderD129/device/driver",
        "../../../bus/platform/drivers/rknpu",
    )?
    .file("/usr/lib/librknnrt.so", "")?;
    let found = profile(&fx.root(), &builtin(), &[]);
    assert_eq!(found.soc.vendor, "Rockchip");
    assert_eq!(found.soc.family, "rk3588");
    assert_eq!(found.system.model, "Radxa ROCK 5B");
    assert!(found.system.cpu_features.contains(&"neon".to_owned()));
    let npu = accel(&found, "rknn").ok_or("rknn non rilevata")?;
    assert!(npu.ready);
    assert_eq!(npu.kind, Kind::Npu);
    assert!(npu.evidence.contains(&"drm:rknpu".to_owned()));
    assert!(npu.evidence.contains(&"soc:rk3588".to_owned()));
    let steps = plan(&found);
    assert_eq!(placement(&steps, Task::WakeWord), Some(edge("rknn")));
    assert_eq!(placement(&steps, Task::Vision), Some(edge("rknn")));
    assert_eq!(placement(&steps, Task::Llm), Some(edge("rknn")));
    assert_eq!(placement(&steps, Task::Tts), Some(edge("cpu")));
    assert!(steps.missing_runtimes.is_empty());
    Ok(())
}

#[test]
fn mainline_rocket_driver_is_recognised_as_rockchip_npu() -> Result<(), String> {
    let fx = Fixture::new("rocket")?;
    base(&fx, 8, 8 * 1024 * 1024)?;
    fx.file("/proc/device-tree/compatible", "rockchip,rk3588\0")?
        .link(
            "/sys/class/accel/accel0/device/driver",
            "../../bus/platform/drivers/rocket",
        )?;
    let found = profile(&fx.root(), &builtin(), &[]);
    let npu = accel(&found, "rknn").ok_or("rocket non rilevato")?;
    assert!(!npu.ready);
    assert_eq!(
        plan(&found)
            .missing_runtimes
            .first()
            .map(|m| m.backend.as_str()),
        Some("rknn")
    );
    Ok(())
}

#[test]
fn raspberry_pi_with_hailo_without_runtime_falls_back_to_cpu() -> Result<(), String> {
    let fx = Fixture::new("rpi5")?;
    base(&fx, 4, 8 * 1024 * 1024)?;
    microphone_and_speaker(&fx)?;
    camera(&fx, "imx708")?;
    fx.file(
        "/proc/device-tree/compatible",
        "raspberrypi,5-model-b\0brcm,bcm2712\0",
    )?
    .file("/dev/hailo0", "")?
    .file("/sys/bus/pci/devices/0001:01:00.0/vendor", "0x1e60\n")?
    .file("/sys/bus/pci/devices/0001:01:00.0/device", "0x2864\n")?
    .link(
        "/sys/class/drm/card0/device/driver",
        "../../bus/platform/drivers/v3d",
    )?;
    let found = profile(&fx.root(), &builtin(), &[]);
    assert_eq!(found.soc.vendor, "Broadcom");
    let hailo = accel(&found, "hailo").ok_or("hailo non rilevato")?;
    assert!(!hailo.ready);
    assert!(hailo.evidence.contains(&"pci:1e60".to_owned()));
    assert!(accel(&found, "gpu-vulkan").is_some_and(|gpu| !gpu.ready));
    let steps = plan(&found);
    assert_eq!(placement(&steps, Task::Vision), Some(edge("cpu")));
    assert_eq!(placement(&steps, Task::Stt), Some(edge("cpu")));
    assert_eq!(placement(&steps, Task::Llm), Some(Placement::Server));
    assert!(steps.missing_runtimes.iter().any(|m| m.backend == "hailo"));
    Ok(())
}

#[test]
fn jetson_uses_cuda_for_everything_including_the_llm() -> Result<(), String> {
    let fx = Fixture::new("jetson")?;
    base(&fx, 6, 8 * 1024 * 1024)?;
    microphone_and_speaker(&fx)?;
    camera(&fx, "vi-output, imx219")?;
    fx.file(
        "/proc/device-tree/compatible",
        "nvidia,p3768-0000+p3767-0005\0nvidia,tegra234\0",
    )?
    .file("/dev/nvhost-ctrl-gpu", "")?
    .file("/usr/local/cuda/lib64/libcudart.so.12", "")?;
    let found = profile(&fx.root(), &builtin(), &[]);
    assert_eq!(found.soc.vendor, "NVIDIA");
    let cuda = accel(&found, "cuda").ok_or("cuda non rilevata")?;
    assert_eq!(cuda.runtime.as_deref(), Some("libcudart.so.12"));
    let steps = plan(&found);
    for task in Task::ALL {
        assert_eq!(placement(&steps, task), Some(edge("cuda")), "{task:?}");
    }
    Ok(())
}

#[test]
fn intel_laptop_with_npu_and_infrared_camera() -> Result<(), String> {
    let fx = Fixture::new("intel")?;
    fx.file(
        "/proc/cpuinfo",
        "processor\t: 0\nvendor_id\t: GenuineIntel\nmodel name\t: Intel(R) Core(TM) Ultra 7 155H\nflags\t\t: fpu sse avx2 avx_vnni\n\nprocessor\t: 1\n\nprocessor\t: 2\n\nprocessor\t: 3\n",
    )?
    .file("/proc/meminfo", "MemTotal: 33554432 kB\nMemAvailable: 16777216 kB\n")?
    .file("/sys/class/dmi/id/sys_vendor", "LENOVO\n")?
    .file("/sys/class/dmi/id/product_name", "ThinkPad X1\n")?
    .link("/sys/class/accel/accel0/device/driver", "../../bus/pci/drivers/intel_vpu")?
    .file("/usr/lib/x86_64-linux-gnu/libopenvino.so.2500", "")?;
    microphone_and_speaker(&fx)?;
    camera(&fx, "Integrated IR Camera")?;
    let found = profile(&fx.root(), &builtin(), &[]);
    assert_eq!(found.soc.vendor, "Intel");
    assert!(found.soc.family.contains("Ultra 7"));
    assert_eq!(found.system.model, "LENOVO ThinkPad X1");
    assert!(found.system.cpu_features.contains(&"avx2".to_owned()));
    assert!(found.system.cpu_features.contains(&"avx-vnni".to_owned()));
    assert!(found.senses.ir_camera);
    assert!(accel(&found, "intel-npu").is_some_and(|npu| npu.ready));
    assert_eq!(placement(&plan(&found), Task::Llm), Some(edge("intel-npu")));
    Ok(())
}

#[test]
fn coral_usb_is_found_by_its_usb_id() -> Result<(), String> {
    let fx = Fixture::new("coral")?;
    base(&fx, 4, 4 * 1024 * 1024)?;
    camera(&fx, "HD Webcam")?;
    fx.file("/sys/bus/usb/devices/2-1/idVendor", "18d1\n")?
        .file("/sys/bus/usb/devices/2-1/idProduct", "9302\n")?
        .file(
            "/sys/bus/usb/devices/2-1/product",
            "Coral USB Accelerator\n",
        )?
        .file("/usr/lib/aarch64-linux-gnu/libedgetpu.so.1", "")?;
    let found = profile(&fx.root(), &builtin(), &[]);
    assert!(
        accel(&found, "edgetpu")
            .is_some_and(|tpu| tpu.ready && tpu.evidence.contains(&"usb:18d1:9302".to_owned()))
    );
    assert!(
        found
            .senses
            .usb
            .contains(&"Coral USB Accelerator".to_owned())
    );
    assert_eq!(
        placement(&plan(&found), Task::Vision),
        Some(edge("edgetpu"))
    );
    Ok(())
}

#[test]
fn tiny_board_without_senses_keeps_everything_on_the_server() -> Result<(), String> {
    let fx = Fixture::new("tiny")?;
    base(&fx, 1, 512 * 1024)?;
    let found = profile(&fx.root(), &builtin(), &[]);
    assert_eq!(found.accelerators.len(), 1);
    let steps = plan(&found);
    assert_eq!(
        placement(&steps, Task::WakeWord),
        Some(Placement::Unavailable {
            reason: "no_microphone"
        })
    );
    assert_eq!(
        placement(&steps, Task::Tts),
        Some(Placement::Unavailable {
            reason: "no_speaker"
        })
    );
    assert_eq!(
        placement(&steps, Task::Vision),
        Some(Placement::Unavailable {
            reason: "no_camera"
        })
    );
    assert_eq!(placement(&steps, Task::Llm), Some(Placement::Server));
    Ok(())
}

#[test]
fn empty_root_never_fails_and_reports_cpu_only() -> Result<(), String> {
    let fx = Fixture::new("empty")?;
    let found = profile(&fx.root(), &builtin(), &[]);
    assert_eq!(
        found.accelerators.first().map(|a| a.id.as_str()),
        Some("cpu")
    );
    assert!(found.system.cores >= 1);
    assert!(found.senses.microphones.is_empty());
    Ok(())
}

#[test]
fn metrics_are_bounded_percentages() -> Result<(), String> {
    let fx = Fixture::new("metrics")?;
    base(&fx, 2, 2 * 1024 * 1024)?;
    let metrics = crate::probe::system::metrics(&fx.root(), 2);
    assert!((metrics.cpu - 25.0).abs() < f64::EPSILON);
    assert!((metrics.ram - 50.0).abs() < f64::EPSILON);
    assert_eq!(metrics.temp, Some(47.3));
    assert!((0.0..=100.0).contains(&metrics.disk));
    Ok(())
}
