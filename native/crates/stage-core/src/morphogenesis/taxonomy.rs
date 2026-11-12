#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MorphologyKind {
    RadialOrganism,
    RadialMechanical,
    BilateralOrganism,
    BilateralVehicle,
    OrbitalSystem,
    HelicalSpiral,
    BranchingNetwork,
    AxialColumn,
    PolyhedralLattice,
    HarmonicMultibody,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PaletteTheme {
    Bioluminescent,
    Celestial,
    Botanical,
    Fauna,
    Mechanical,
    Microscopic,
    Geological,
    Ethereal,
}

impl PaletteTheme {
    #[must_use]
    pub const fn colors(self) -> [&'static str; 6] {
        match self {
            Self::Bioluminescent => [
                "#4ce6ff", "#7952ec", "#a87bff", "#ff6be5", "#5ef2ff", "#c49bff",
            ],
            Self::Celestial => [
                "#ffd166", "#5ce1e6", "#480ca8", "#72efdd", "#9b7bff", "#ff9f1c",
            ],
            Self::Botanical => [
                "#38b000", "#70e000", "#a7c957", "#ff70a6", "#ffb703", "#007200",
            ],
            Self::Fauna => [
                "#ee9b00", "#ca6702", "#bb3e03", "#0077b6", "#90e0ef", "#f1faee",
            ],
            Self::Mechanical => [
                "#64dfdf", "#48bfe3", "#5390d9", "#ff9f1c", "#80ffdb", "#7400b8",
            ],
            Self::Microscopic => [
                "#ff006e", "#00f5d4", "#8338ec", "#fee440", "#3a86ff", "#ffbe0b",
            ],
            Self::Geological => [
                "#2ec4b6", "#e71d36", "#ff9f1c", "#7209b7", "#e0aaff", "#c77dff",
            ],
            Self::Ethereal => [
                "#5ef2ff", "#9b7bff", "#66ffe3", "#ff7be5", "#7aa2ff", "#ffd166",
            ],
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub struct MorphoDescriptor {
    pub kind: MorphologyKind,
    pub theme: PaletteTheme,
    pub seed: u64,
    pub count: u8,
    pub aspect: f64,
}

const BIO_RADIAL_ROOTS: &[&str] = &[
    "medusa",
    "jellyfish",
    "polp",
    "octopus",
    "squid",
    "calamar",
    "anemon",
    "cnidar",
    "starfish",
    "stella marina",
    "hydra",
    "coral",
];

const MECH_RADIAL_ROOTS: &[&str] = &[
    "turbin",
    "propeller",
    "elica",
    "rotore",
    "girandol",
    "ingranagg",
    "gear",
    "ruota",
    "wheel",
    "ventilator",
    "fan",
    "centrifug",
];

const BIO_BILATERAL_ROOTS: &[&str] = &[
    "aquila",
    "eagle",
    "falco",
    "uccell",
    "bird",
    "farfall",
    "butterfly",
    "leone",
    "lion",
    "cane",
    "dog",
    "gatto",
    "cat",
    "cavallo",
    "horse",
    "pesce",
    "fish",
    "squalo",
    "shark",
    "delfin",
    "dolphin",
    "balen",
    "whale",
    "insetto",
    "insect",
    "ragno",
    "spider",
    "scorpione",
    "lupo",
    "wolf",
    "orso",
    "bear",
    "drago",
    "dragon",
];

const VEHICLE_BILATERAL_ROOTS: &[&str] = &[
    "aereo",
    "airplane",
    "jet",
    "drone",
    "aliant",
    "navetta",
    "shuttle",
    "astronave",
    "spaceship",
    "auto",
    "macchina",
    "car",
    "veicolo",
    "moto",
    "barca",
    "nave",
    "ship",
];

const ORBITAL_ROOTS: &[&str] = &[
    "atom",
    "molecol",
    "nucleo",
    "planet",
    "pianeta",
    "saturno",
    "saturn",
    "giove",
    "jupiter",
    "galassia",
    "galaxy",
    "sistema solare",
    "solar system",
    "buco nero",
    "black hole",
    "pulsar",
    "quasar",
    "orbita",
];

const HELICAL_ROOTS: &[&str] = &[
    "dna",
    "rna",
    "elica",
    "spiral",
    "vortice",
    "vortex",
    "ciclone",
    "tornado",
    "uragano",
    "tromba d'aria",
    "coclea",
];

const BRANCHING_ROOTS: &[&str] = &[
    "albero",
    "tree",
    "pianta",
    "plant",
    "ramo",
    "branch",
    "rete neurale",
    "neural",
    "dendrit",
    "neurone",
    "neuron",
    "fulmine",
    "lightning",
    "radice",
    "root",
    "vascolar",
    "polmone",
    "lung",
    "bronch",
];

const AXIAL_ROOTS: &[&str] = &[
    "razzo",
    "rocket",
    "missile",
    "torre",
    "tower",
    "grattacielo",
    "skyscraper",
    "faro",
    "lighthouse",
    "sommergibile",
    "submarine",
    "obelisco",
    "colonna",
    "pilastro",
    "canna",
    "tubo",
];

const POLYHEDRAL_ROOTS: &[&str] = &[
    "cristall",
    "crystal",
    "diamant",
    "diamond",
    "minerale",
    "quarzo",
    "quartz",
    "fullerene",
    "icosaedro",
    "poliedro",
    "reticolo",
    "lattice",
    "virus",
    "capside",
];

fn compute_hash(text: &str) -> u64 {
    let mut h: u64 = 0xCBF2_9CE4_8422_2325;
    for b in text.bytes() {
        h ^= u64::from(b);
        h = h.wrapping_mul(0x0100_0000_01B3);
    }
    h
}

fn matches_any(text: &str, roots: &[&str]) -> bool {
    roots.iter().any(|r| text.contains(r))
}

fn classify_symmetric(lower: &str, seed: u64) -> Option<MorphoDescriptor> {
    if matches_any(lower, BIO_RADIAL_ROOTS) {
        let count = 6_u8.saturating_add((seed % 3) as u8);
        return Some(MorphoDescriptor {
            kind: MorphologyKind::RadialOrganism,
            theme: PaletteTheme::Bioluminescent,
            seed,
            count,
            aspect: 1.35,
        });
    }
    if matches_any(lower, MECH_RADIAL_ROOTS) {
        let count = 4_u8.saturating_add(((seed >> 2) % 5) as u8);
        return Some(MorphoDescriptor {
            kind: MorphologyKind::RadialMechanical,
            theme: PaletteTheme::Mechanical,
            seed,
            count,
            aspect: 0.95,
        });
    }
    if matches_any(lower, BIO_BILATERAL_ROOTS) {
        return Some(MorphoDescriptor {
            kind: MorphologyKind::BilateralOrganism,
            theme: PaletteTheme::Fauna,
            seed,
            count: 2,
            aspect: 1.2,
        });
    }
    if matches_any(lower, VEHICLE_BILATERAL_ROOTS) {
        return Some(MorphoDescriptor {
            kind: MorphologyKind::BilateralVehicle,
            theme: PaletteTheme::Mechanical,
            seed,
            count: 2,
            aspect: 1.6,
        });
    }
    None
}

fn classify_structural(lower: &str, seed: u64) -> Option<MorphoDescriptor> {
    if matches_any(lower, ORBITAL_ROOTS) {
        let count = 3_u8.saturating_add((seed % 3) as u8);
        let theme = if lower.contains("atom") || lower.contains("molecol") {
            PaletteTheme::Microscopic
        } else {
            PaletteTheme::Celestial
        };
        return Some(MorphoDescriptor {
            kind: MorphologyKind::OrbitalSystem,
            theme,
            seed,
            count,
            aspect: 1.0,
        });
    }
    if matches_any(lower, HELICAL_ROOTS) {
        return Some(MorphoDescriptor {
            kind: MorphologyKind::HelicalSpiral,
            theme: if lower.contains("dna") || lower.contains("rna") {
                PaletteTheme::Microscopic
            } else {
                PaletteTheme::Celestial
            },
            seed,
            count: 2,
            aspect: 1.8,
        });
    }
    if matches_any(lower, BRANCHING_ROOTS) {
        let count = 3_u8.saturating_add((seed % 4) as u8);
        return Some(MorphoDescriptor {
            kind: MorphologyKind::BranchingNetwork,
            theme: PaletteTheme::Botanical,
            seed,
            count,
            aspect: 1.5,
        });
    }
    if matches_any(lower, AXIAL_ROOTS) {
        return Some(MorphoDescriptor {
            kind: MorphologyKind::AxialColumn,
            theme: PaletteTheme::Mechanical,
            seed,
            count: 4,
            aspect: 2.2,
        });
    }
    if matches_any(lower, POLYHEDRAL_ROOTS) {
        let count = 6_u8.saturating_add((seed % 3) as u8);
        return Some(MorphoDescriptor {
            kind: MorphologyKind::PolyhedralLattice,
            theme: PaletteTheme::Geological,
            seed,
            count,
            aspect: 1.0,
        });
    }
    None
}

#[must_use]
pub fn classify_morphology(concept: &str) -> MorphoDescriptor {
    let lower = concept.to_lowercase();
    let seed = compute_hash(&lower);

    if let Some(desc) = classify_symmetric(&lower, seed) {
        return desc;
    }
    if let Some(desc) = classify_structural(&lower, seed) {
        return desc;
    }

    let kind = match seed % 6 {
        0 => MorphologyKind::RadialOrganism,
        1 => MorphologyKind::RadialMechanical,
        2 => MorphologyKind::BilateralVehicle,
        3 => MorphologyKind::OrbitalSystem,
        4 => MorphologyKind::HelicalSpiral,
        _ => MorphologyKind::HarmonicMultibody,
    };
    let theme = match (seed >> 8) % 4 {
        0 => PaletteTheme::Bioluminescent,
        1 => PaletteTheme::Celestial,
        2 => PaletteTheme::Mechanical,
        _ => PaletteTheme::Ethereal,
    };
    let count = 4_u8.saturating_add(((seed >> 16) % 5) as u8);

    MorphoDescriptor {
        kind,
        theme,
        seed,
        count,
        aspect: 1.1,
    }
}
