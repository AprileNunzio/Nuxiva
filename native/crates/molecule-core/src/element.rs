#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Element {
    pub symbol: &'static str,
    pub number: u8,
    pub covalent: f32,
    pub vdw: f32,
    pub color: [u8; 3],
}

pub const UNKNOWN: Element = Element {
    symbol: "X",
    number: 0,
    covalent: 0.77,
    vdw: 1.7,
    color: [255, 20, 147],
};

const TABLE: &[Element] = &[
    Element {
        symbol: "H",
        number: 1,
        covalent: 0.31,
        vdw: 1.1,
        color: [240, 240, 240],
    },
    Element {
        symbol: "C",
        number: 6,
        covalent: 0.76,
        vdw: 1.7,
        color: [144, 144, 144],
    },
    Element {
        symbol: "N",
        number: 7,
        covalent: 0.71,
        vdw: 1.55,
        color: [48, 80, 248],
    },
    Element {
        symbol: "O",
        number: 8,
        covalent: 0.66,
        vdw: 1.52,
        color: [255, 13, 13],
    },
    Element {
        symbol: "F",
        number: 9,
        covalent: 0.57,
        vdw: 1.47,
        color: [144, 224, 80],
    },
    Element {
        symbol: "NA",
        number: 11,
        covalent: 1.66,
        vdw: 2.27,
        color: [171, 92, 242],
    },
    Element {
        symbol: "MG",
        number: 12,
        covalent: 1.41,
        vdw: 1.73,
        color: [138, 255, 0],
    },
    Element {
        symbol: "P",
        number: 15,
        covalent: 1.07,
        vdw: 1.8,
        color: [255, 128, 0],
    },
    Element {
        symbol: "S",
        number: 16,
        covalent: 1.05,
        vdw: 1.8,
        color: [255, 200, 50],
    },
    Element {
        symbol: "CL",
        number: 17,
        covalent: 1.02,
        vdw: 1.75,
        color: [31, 240, 31],
    },
    Element {
        symbol: "K",
        number: 19,
        covalent: 2.03,
        vdw: 2.75,
        color: [143, 64, 212],
    },
    Element {
        symbol: "CA",
        number: 20,
        covalent: 1.76,
        vdw: 2.31,
        color: [61, 255, 0],
    },
    Element {
        symbol: "MN",
        number: 25,
        covalent: 1.39,
        vdw: 2.0,
        color: [156, 122, 199],
    },
    Element {
        symbol: "FE",
        number: 26,
        covalent: 1.32,
        vdw: 2.0,
        color: [224, 102, 51],
    },
    Element {
        symbol: "CO",
        number: 27,
        covalent: 1.26,
        vdw: 2.0,
        color: [240, 144, 160],
    },
    Element {
        symbol: "NI",
        number: 28,
        covalent: 1.24,
        vdw: 1.63,
        color: [80, 208, 80],
    },
    Element {
        symbol: "CU",
        number: 29,
        covalent: 1.32,
        vdw: 1.4,
        color: [200, 128, 51],
    },
    Element {
        symbol: "ZN",
        number: 30,
        covalent: 1.22,
        vdw: 1.39,
        color: [125, 128, 176],
    },
    Element {
        symbol: "SE",
        number: 34,
        covalent: 1.2,
        vdw: 1.9,
        color: [255, 161, 0],
    },
    Element {
        symbol: "BR",
        number: 35,
        covalent: 1.2,
        vdw: 1.85,
        color: [166, 41, 41],
    },
    Element {
        symbol: "I",
        number: 53,
        covalent: 1.39,
        vdw: 1.98,
        color: [148, 0, 148],
    },
];

#[must_use]
pub fn by_symbol(symbol: &str) -> Element {
    let upper = symbol.trim().to_ascii_uppercase();
    TABLE
        .iter()
        .copied()
        .find(|e| e.symbol == upper)
        .unwrap_or(UNKNOWN)
}

#[must_use]
pub fn by_number(number: u8) -> Element {
    TABLE
        .iter()
        .copied()
        .find(|e| e.number == number)
        .unwrap_or(UNKNOWN)
}

#[must_use]
pub fn from_atom_name(name: &str) -> Element {
    let letters: String = name
        .trim()
        .chars()
        .filter(char::is_ascii_alphabetic)
        .take(1)
        .collect();
    by_symbol(&letters)
}
