use serde::{Deserialize, Serialize};

pub const MAX_ITEMS: usize = 6;
pub const MIN_HEIGHT_CM: u16 = 50;
pub const MAX_HEIGHT_CM: u16 = 250;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Color {
    Black,
    White,
    Grey,
    Red,
    Orange,
    Yellow,
    Green,
    Cyan,
    Blue,
    Purple,
    Pink,
    Brown,
    Beige,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Headwear {
    Cap,
    Hat,
    Hood,
    Helmet,
    Beanie,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Item {
    Backpack,
    Bag,
    Parcel,
    Suitcase,
    Umbrella,
    Phone,
    Trolley,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Build {
    Slim,
    Medium,
    Broad,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum VehicleKind {
    Car,
    Van,
    Truck,
    Motorbike,
    Scooter,
    Bicycle,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Vehicle {
    pub kind: VehicleKind,
    #[serde(default)]
    pub color: Option<Color>,
}

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Look {
    #[serde(default)]
    pub upper: Option<Color>,
    #[serde(default)]
    pub lower: Option<Color>,
    #[serde(default)]
    pub headwear: Option<Headwear>,
    #[serde(default)]
    pub face_covered: Option<bool>,
    #[serde(default)]
    pub glasses: Option<bool>,
    #[serde(default)]
    pub beard: Option<bool>,
    #[serde(default)]
    pub hi_vis: Option<bool>,
    #[serde(default)]
    pub build: Option<Build>,
    #[serde(default)]
    pub height_cm: Option<u16>,
    #[serde(default)]
    pub carrying: Vec<Item>,
}

impl Look {
    #[must_use]
    pub fn valid(&self) -> bool {
        let mut seen = self.carrying.clone();
        seen.sort_unstable();
        seen.dedup();
        self.carrying.len() <= MAX_ITEMS
            && seen.len() == self.carrying.len()
            && self
                .height_cm
                .is_none_or(|h| (MIN_HEIGHT_CM..=MAX_HEIGHT_CM).contains(&h))
    }
}
