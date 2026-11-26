#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Action {
    On,
    Off,
    Toggle,
    Open,
    Close,
    Up,
    Down,
    Lock,
    Unlock,
}

impl Action {
    #[must_use]
    pub fn key(self) -> &'static str {
        match self {
            Self::On => "on",
            Self::Off => "off",
            Self::Toggle => "toggle",
            Self::Open => "open",
            Self::Close => "close",
            Self::Up => "up",
            Self::Down => "down",
            Self::Lock => "lock",
            Self::Unlock => "unlock",
        }
    }

    #[must_use]
    pub fn supports(self, domain: &str) -> bool {
        match self {
            Self::On | Self::Off | Self::Toggle => matches!(
                domain,
                "light"
                    | "switch"
                    | "fan"
                    | "media_player"
                    | "climate"
                    | "humidifier"
                    | "input_boolean"
                    | "siren"
            ),
            Self::Open | Self::Close => matches!(domain, "cover" | "valve"),
            Self::Up | Self::Down => matches!(
                domain,
                "light" | "cover" | "media_player" | "climate" | "fan"
            ),
            Self::Lock | Self::Unlock => domain == "lock",
        }
    }

    #[must_use]
    pub fn adapted(self, domain: &str) -> Self {
        let switchable = Self::On.supports(domain);
        match self {
            Self::Open if switchable => Self::On,
            Self::Close if switchable => Self::Off,
            Self::Up if domain == "cover" => Self::Open,
            Self::Down if domain == "cover" => Self::Close,
            other => other,
        }
    }
}

pub const ACTION_ROOTS: &[(Action, &[&str])] = &[
    (
        Action::Unlock,
        &["sblocc", "unlock", "desbloq", "deverrouill", "entriegel"],
    ),
    (Action::Lock, &["blocc", "lock", "verrouill", "verriegel"]),
    (
        Action::Off,
        &[
            "spegn",
            "spent",
            "disattiv",
            "stacc",
            "apag",
            "eteign",
            "ausschalt",
            "desactiv",
            "deactiv",
        ],
    ),
    (
        Action::On,
        &[
            "accend",
            "acces",
            "illumin",
            "attiv",
            "avvi",
            "enciend",
            "encend",
            "allum",
            "einschalt",
            "activ",
        ],
    ),
    (Action::Toggle, &["invert", "commut", "toggl"]),
    (
        Action::Open,
        &[
            "apri", "aprir", "apert", "open", "abri", "abre", "ouvr", "offn", "spalanc",
        ],
    ),
    (
        Action::Close,
        &["chiud", "chius", "clos", "cierr", "schliess"],
    ),
    (
        Action::Up,
        &[
            "alza", "alzi", "aument", "solleva", "raise", "increas", "brighten", "subir", "sube",
            "augment",
        ],
    ),
    (
        Action::Down,
        &[
            "abbass", "diminu", "ridu", "lower", "decreas", "bajar", "baja", "baiss",
        ],
    ),
];

pub const PHRASAL: &[(&str, &str, Action)] = &[
    ("turn", "on", Action::On),
    ("switch", "on", Action::On),
    ("power", "on", Action::On),
    ("turn", "off", Action::Off),
    ("switch", "off", Action::Off),
    ("power", "off", Action::Off),
];

pub const DOMAIN_WORDS: &[(&str, &[&str], &[&str])] = &[
    (
        "light",
        &[
            "luce",
            "lampada",
            "lampadina",
            "light",
            "lamp",
            "bulb",
            "luz",
            "lumiere",
            "licht",
            "illuminazione",
        ],
        &[
            "lampadario",
            "faretto",
            "led",
            "plafoniera",
            "applique",
            "abatjour",
            "abat",
            "piantana",
            "lampara",
            "spot",
        ],
    ),
    (
        "cover",
        &[
            "tapparella",
            "serranda",
            "persiana",
            "tenda",
            "blind",
            "shutter",
            "curtain",
            "volet",
            "cortina",
            "rollladen",
        ],
        &[
            "veneziana",
            "avvolgibile",
            "saracinesca",
            "basculante",
            "lucernario",
        ],
    ),
    (
        "climate",
        &[
            "condizionatore",
            "climatizzatore",
            "clima",
            "termostato",
            "riscaldamento",
            "thermostat",
            "heating",
            "conditioner",
            "aircon",
            "calefaccion",
            "chauffage",
            "heizung",
        ],
        &["termosifone", "caldaia", "split", "pompa"],
    ),
    (
        "fan",
        &["ventilatore", "ventola", "fan", "ventilador", "ventilateur"],
        &[],
    ),
    (
        "switch",
        &[
            "presa",
            "interruttore",
            "spina",
            "switch",
            "plug",
            "socket",
            "outlet",
            "enchufe",
            "prise",
            "steckdose",
        ],
        &["ciabatta", "rele"],
    ),
    (
        "media_player",
        &["tv", "televisione", "televisore", "television", "fernseher"],
        &[
            "stereo",
            "cassa",
            "altoparlante",
            "speaker",
            "radio",
            "soundbar",
            "chromecast",
            "sonos",
        ],
    ),
    (
        "lock",
        &["serratura", "lucchetto", "cerradura", "serrure", "schloss"],
        &[],
    ),
    (
        "vacuum",
        &[
            "aspirapolvere",
            "robot",
            "vacuum",
            "aspiradora",
            "aspirateur",
            "roomba",
        ],
        &[],
    ),
];

pub const AREA_GROUPS: &[&[&str]] = &[
    &[
        "soggiorno",
        "salotto",
        "sala",
        "salone",
        "living",
        "living room",
        "lounge",
        "salon",
        "wohnzimmer",
    ],
    &[
        "camera da letto",
        "camera matrimoniale",
        "matrimoniale",
        "stanza da letto",
        "bedroom",
        "master bedroom",
        "dormitorio",
        "habitacion",
        "chambre",
        "schlafzimmer",
    ],
    &[
        "cameretta",
        "camera dei bambini",
        "camera bimbi",
        "kids room",
        "nursery",
        "kinderzimmer",
    ],
    &[
        "bagno",
        "toilette",
        "wc",
        "bathroom",
        "bano",
        "salle de bain",
        "badezimmer",
    ],
    &[
        "cucina",
        "angolo cottura",
        "kitchen",
        "cocina",
        "cuisine",
        "kuche",
    ],
    &[
        "studio", "ufficio", "office", "study", "estudio", "oficina", "bureau", "buro",
    ],
    &[
        "ingresso", "entrata", "atrio", "entrance", "hall", "entrada", "entree", "eingang",
    ],
    &[
        "corridoio",
        "disimpegno",
        "hallway",
        "pasillo",
        "couloir",
        "flur",
    ],
    &[
        "balcone", "terrazzo", "terrazza", "veranda", "balcony", "terrace", "terraza", "balcon",
    ],
    &[
        "giardino", "cortile", "esterno", "garden", "backyard", "yard", "jardin", "garten",
    ],
    &["garage", "box", "autorimessa", "garaje"],
    &["lavanderia", "laundry", "buanderie"],
    &["cantina", "taverna", "basement", "sotano", "cave", "keller"],
    &[
        "sala da pranzo",
        "sala pranzo",
        "dining room",
        "comedor",
        "salle a manger",
    ],
    &[
        "camera degli ospiti",
        "camera ospiti",
        "stanza degli ospiti",
        "guest room",
        "chambre d amis",
    ],
];

pub const WHOLE_HOME: &[&str] = &[
    "tutta la casa",
    "tutta casa",
    "tutte le stanze",
    "ogni stanza",
    "ovunque",
    "dappertutto",
    "in casa",
    "whole house",
    "whole home",
    "everywhere",
    "toda la casa",
    "toute la maison",
    "partout",
    "ganzen haus",
];

pub const QUANTIFIERS: &[&str] = &[
    "tutte", "tutti", "tutto", "tutta", "all", "every", "todas", "todos", "toutes", "tous", "alle",
];

pub const DEFER: &[&str] = &[
    "piano",
    "sopra",
    "sotto",
    "pianterreno",
    "seminterrato",
    "floor",
    "upstairs",
    "downstairs",
    "planta",
    "etage",
    "stock",
    "scena",
    "scenario",
    "scene",
    "atmosfera",
    "routine",
    "script",
    "allarme",
    "antifurto",
    "alarm",
];

pub const NEUTRAL: &[&str] = &[
    "cento",
    "percento",
    "percent",
    "gradi",
    "grado",
    "degrees",
    "massimo",
    "minimo",
    "meta",
    "caldo",
    "calda",
    "freddo",
    "fredda",
    "naturale",
    "bianco",
    "rosso",
    "verde",
    "blu",
    "giallo",
    "arancione",
    "viola",
    "rosa",
    "azzurro",
    "red",
    "green",
    "blue",
    "yellow",
    "white",
    "warm",
    "cold",
    "luminosita",
    "brightness",
    "intensita",
    "colore",
    "color",
    "volume",
    "po",
    "poco",
    "piu",
    "meno",
    "favore",
    "grazie",
];

#[must_use]
pub fn plural_word(word: &str) -> bool {
    let n = word.chars().count();
    if n <= 3 {
        return false;
    }
    if word.ends_with('s') && !word.ends_with("ss") {
        return true;
    }
    if word.ends_with('i') {
        return true;
    }
    (word.ends_with('e')
        && !["ore", "one", "ce", "le", "ie", "ue"]
            .iter()
            .any(|s| word.ends_with(s)))
        || word.ends_with("lle")
}
