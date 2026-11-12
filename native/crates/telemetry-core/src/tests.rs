use crate::{
    MachineClass, MachineInputs, Sampler, core_runtime, detect_class, docker_needed,
    parse_cpu_times, parse_loadavg, parse_meminfo, parse_net_dev, parse_nvidia_smi,
    parse_process_stat,
};

const STAT: &str = "cpu  100 0 100 700 100 0 0 0 5 0\ncpu0 50 0 50 350 50 0 0 0 0 0\ncpu1 50 0 50 350 50 0 0 0 0 0\nintr 1\nbtime 1700000000\n";
const STAT2: &str = "cpu  200 0 200 800 100 0 0 0 5 0\ncpu0 150 0 50 350 50 0 0 0 0 0\ncpu1 50 0 150 450 50 0 0 0 0 0\nbtime 1700000000\n";

#[test]
fn cpu_times_and_percent() {
    let (a, cores, boot) = parse_cpu_times(STAT);
    let (b, cores2, _) = parse_cpu_times(STAT2);
    assert_eq!(boot, 1_700_000_000);
    assert_eq!(cores.len(), 2);
    assert!((b.percent_since(a) - 66.7).abs() < 1e-9);
    let first = cores2.first().copied().unwrap_or_default();
    let before = cores.first().copied().unwrap_or_default();
    assert!((first.percent_since(before) - 100.0).abs() < 1e-9);
    assert!((a.percent_since(a)).abs() < 1e-9);
}

#[test]
fn meminfo_and_fallback() {
    let info = parse_meminfo(
        "MemTotal: 1000 kB\nMemFree: 100 kB\nMemAvailable: 400 kB\nSwapTotal: 50 kB\nSwapFree: 25 kB\n",
    );
    assert_eq!(info.total, 1_024_000);
    assert_eq!(info.available, 409_600);
    assert_eq!(info.swap_free, 25_600);
    let old = parse_meminfo("MemTotal: 1000 kB\nMemFree: 100 kB\nBuffers: 50 kB\nCached: 50 kB\n");
    assert_eq!(old.available, 204_800);
}

#[test]
fn loadavg_and_net() {
    let load = parse_loadavg("0.123 1.5 2 1/200 999");
    for (got, want) in load.iter().zip([0.12, 1.5, 2.0]) {
        assert!((got - want).abs() < 1e-9);
    }
    let net = parse_net_dev(
        "h1\nh2\n  lo: 100 1 0 0 0 0 0 0 200 2 0 0 0 0 0 0\neth0: 5 1 0 0 0 0 0 0 7 1 0 0 0 0 0 0\n",
    );
    assert_eq!((net.rx, net.tx), (105, 207));
}

#[test]
fn process_stat_with_spaces_and_parens() {
    let raw = "42 (my (odd) proc) S 1 1 1 0 -1 0 0 0 0 0 30 12 0 0 20 0 1 0 100 1000 250 0";
    let sample = parse_process_stat(raw);
    assert!(sample.is_some());
    if let Some(sample) = sample {
        assert_eq!(sample.pid, 42);
        assert_eq!(sample.name, "my (odd) proc");
        assert_eq!(sample.state, 'S');
        assert_eq!(sample.ticks, 42);
        assert_eq!(sample.rss_pages, 250);
    }
    assert!(parse_process_stat("garbage").is_none());
}

#[test]
fn nvidia_output() {
    let gpu = parse_nvidia_smi("NVIDIA RTX, 37, 2048, 8192, 61, 1800\n");
    assert!(
        gpu.as_ref()
            .is_some_and(|g| g.available && (g.vram_percent - 25.0).abs() < 1e-9)
    );
    assert!(parse_nvidia_smi("a, b").is_none());
    assert!(parse_nvidia_smi("x, nan, 1, 2, 3, 4").is_none());
}

#[test]
fn machine_classes() {
    let gib = 1_073_741_824u64;
    let class = |board: &str, ram: u64, gpu: bool| {
        detect_class(MachineInputs {
            board,
            ram_bytes: ram * gib,
            gpu,
        })
    };
    assert_eq!(class("Raspberry Pi 5", 8, false), MachineClass::Pi);
    assert_eq!(class("", 4, true), MachineClass::Small);
    assert_eq!(class("", 16, false), MachineClass::Standard);
    assert_eq!(class("", 16, true), MachineClass::Powerful);
    assert_eq!(class("", 32, false), MachineClass::Powerful);
    assert_eq!(core_runtime("", MachineClass::Small), "native");
    assert_eq!(core_runtime("docker", MachineClass::Pi), "docker");
    assert_eq!(core_runtime("bogus", MachineClass::Standard), "docker");
    assert!(docker_needed("native", " Auto "));
    assert!(!docker_needed("native", "0"));
    assert_eq!(
        MachineClass::parse("pi").map(MachineClass::code),
        Some("pi")
    );
}

#[test]
fn live_sampler_reads_this_machine() {
    let mut sampler = Sampler::system();
    let first = sampler.sample(1_000.0, 8);
    let second = sampler.sample(1_001.0, 8);
    assert!(first.mem_total > 0);
    assert!(second.cpu_count >= 1);
    assert!(second.top_processes.len() <= 8);
    assert!(second.disk_total > 0);
}
