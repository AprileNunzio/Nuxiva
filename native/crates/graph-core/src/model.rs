use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum NodeKind {
    File,
    Symbol,
    Package,
    Section,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SymKind {
    Function,
    Type,
    Trait,
    Module,
    Constant,
    Entity,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum EdgeKind {
    Declares,
    Imports,
    DependsOn,
    Documents,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Language {
    Rust,
    Python,
    Script,
    Cargo,
    Manifest,
    Markdown,
    Other,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Node {
    pub kind: NodeKind,
    pub sym: Option<SymKind>,
    pub name: String,
    pub file: u32,
    pub line: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Fact {
    pub name: String,
    pub kind: SymKind,
    pub line: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize, Deserialize)]
pub struct Facts {
    pub symbols: Vec<Fact>,
    pub imports: Vec<String>,
    pub package: Option<String>,
    pub mentions: Vec<String>,
}

impl Language {
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::Rust => "rust",
            Self::Python => "python",
            Self::Script => "script",
            Self::Cargo => "cargo",
            Self::Manifest => "manifest",
            Self::Markdown => "markdown",
            Self::Other => "other",
        }
    }
}
