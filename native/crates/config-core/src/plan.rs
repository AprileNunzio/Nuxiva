pub type Trigger = (&'static [&'static str], &'static [&'static str]);

pub const STEP_TRIGGERS: &[Trigger] = &[
    (
        &[
            "NUXIVA_EMBED_MODEL",
            "NUXIVA_LLM_FAST_MODEL",
            "NUXIVA_LLM_MODEL",
        ],
        &["preflight", "models", "brain", "warmup"],
    ),
    (&["NUXIVA_EMBED_MODEL", "NUXIVA_LLM_MODEL"], &["services"]),
    (
        &[
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "HOME_ASSISTANT_TOKEN",
            "HOME_ASSISTANT_URL",
        ],
        &["services"],
    ),
    (&["NUXIVA_KIOSK"], &["kiosk"]),
    (&["NUXIVA_VOICE"], &["voice"]),
    (&["NUXIVA_VISION"], &["vision"]),
    (&["NUXIVA_EAR", "NUXIVA_STT_MODEL"], &["ear"]),
    (&["NUXIVA_EAR", "NUXIVA_MUSIC_ID"], &["music"]),
    (&["NUXIVA_STUDY_FINETUNE"], &["soup"]),
    (&["NUXIVA_3D_CONVERT"], &["convert3d"]),
    (
        &["NUXIVA_COMMERCIAL", "NUXIVA_UNOFFICIAL_SERVICES"],
        &["voice", "ear", "music", "models", "brain"],
    ),
    (&["NUXIVA_GPU_DRIVER"], &["display_driver"]),
    (
        &[
            "NUXIVA_SHARES",
            "NUXIVA_SHARES_DISCOVERY",
            "NUXIVA_SHARES_ENCRYPT",
            "NUXIVA_SHARES_NETWORKS",
            "NUXIVA_SHARES_PROTOCOL",
            "NUXIVA_SHARES_READONLY",
            "NUXIVA_SHARES_RECYCLE",
            "NUXIVA_SMB_PASSWORD",
        ],
        &["shares"],
    ),
    (
        &["NUXIVA_OLLAMA_URL"],
        &["ollama", "models", "brain", "warmup", "services"],
    ),
    (
        &["NUXIVA_BRAIN"],
        &["ollama", "models", "brain", "warmup", "services"],
    ),
    (&["NUXIVA_VOICE_PACKAGE"], &["voice"]),
    (&["NUXIVA_DOCUMENTS"], &["office"]),
    (&["NUXIVA_BLUETOOTH"], &["bluetooth"]),
    (&["NUXIVA_SANDBOX"], &["sandbox", "gvisor", "firecracker"]),
    (&["NUXIVA_NATIVE"], &["native"]),
    (&["NUXIVA_ZRAM"], &["memory"]),
    (&["NUXIVA_CORE_RUNTIME"], &["docker", "core", "services"]),
];

const RELOAD_PREFIXES: &[(&str, &[&str])] = &[(
    "nuxiva-ear",
    &[
        "NUXIVA_ASSISTANT_",
        "NUXIVA_WAKE",
        "NUXIVA_EAR_",
        "NUXIVA_VOICEPRINT_",
    ],
)];

fn push_unique(out: &mut Vec<String>, item: &str) {
    if !out.iter().any(|existing| existing == item) {
        out.push(item.to_owned());
    }
}

#[must_use]
pub fn apply_plan(keys: &[String], extra: &[String], known: &[String]) -> Vec<String> {
    let mut wanted: Vec<String> = Vec::new();
    for step in extra {
        push_unique(&mut wanted, step);
    }
    for (trigger, steps) in STEP_TRIGGERS {
        if trigger.iter().any(|t| keys.iter().any(|k| k == t)) {
            for step in *steps {
                push_unique(&mut wanted, step);
            }
        }
    }
    wanted.retain(|step| known.iter().any(|k| k == step));
    wanted
}

#[must_use]
pub fn reload_units(keys: &[String]) -> Vec<String> {
    RELOAD_PREFIXES
        .iter()
        .filter(|(_, prefixes)| {
            keys.iter()
                .any(|k| prefixes.iter().any(|p| k.starts_with(p)))
        })
        .map(|(unit, _)| (*unit).to_owned())
        .collect()
}
