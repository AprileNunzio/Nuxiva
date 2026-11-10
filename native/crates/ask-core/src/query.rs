use nuxiva_memory_core::{Class, Color, Headwear, Item, VehicleKind};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum QueryLang {
    It,
    En,
    Fr,
    Es,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum QuestionKind {
    When,
    WhatLook,
    Who,
    DidPass,
    General,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RoleTarget {
    Courier,
    Visitor,
    Household,
    Vehicle,
    Animal,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AskQuery {
    pub lang: QueryLang,
    pub kind: QuestionKind,
    pub from_ms: u64,
    pub to_ms: u64,
    #[serde(default)]
    pub target_role: Option<RoleTarget>,
    #[serde(default)]
    pub class: Option<Class>,
    #[serde(default)]
    pub upper_color: Option<Color>,
    #[serde(default)]
    pub lower_color: Option<Color>,
    #[serde(default)]
    pub headwear: Option<Headwear>,
    #[serde(default)]
    pub item: Option<Item>,
    #[serde(default)]
    pub vehicle_kind: Option<VehicleKind>,
    #[serde(default)]
    pub vehicle_color: Option<Color>,
    #[serde(default)]
    pub camera_or_zone: Option<String>,
}
