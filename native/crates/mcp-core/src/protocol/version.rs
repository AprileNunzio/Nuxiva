#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Feature {
    StructuredOutput,
    StreamableHttp,
    ProtocolHeader,
    OutputSchema,
    ToolTitle,
    ResourceLink,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct VersionProfile {
    pub name: &'static str,
    pub features: &'static [Feature],
}

impl VersionProfile {
    #[must_use]
    pub fn has(&self, feature: Feature) -> bool {
        self.features.contains(&feature)
    }
}

const PROFILES: &[VersionProfile] = &[
    VersionProfile {
        name: "2025-06-18",
        features: &[
            Feature::StructuredOutput,
            Feature::StreamableHttp,
            Feature::ProtocolHeader,
            Feature::OutputSchema,
            Feature::ToolTitle,
            Feature::ResourceLink,
        ],
    },
    VersionProfile {
        name: "2025-03-26",
        features: &[Feature::StreamableHttp],
    },
    VersionProfile {
        name: "2024-11-05",
        features: &[],
    },
];

#[must_use]
pub fn supported_versions() -> Vec<&'static str> {
    PROFILES.iter().map(|p| p.name).collect()
}

#[must_use]
pub fn negotiate(server_version: &str) -> Option<&'static VersionProfile> {
    PROFILES.iter().find(|p| p.name == server_version)
}
