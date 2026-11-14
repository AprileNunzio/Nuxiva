use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use nuxiva_agent_core::ceo::{Card, Index};
use nuxiva_agent_core::{Layout, Manifest, Origin, Registry, Root};
use nuxiva_mcp_core::{Hub, SignedCatalog, verify_catalog};
use nuxiva_swarm_core::{Catalog, Settings};

use crate::error::{BrainError, BrainResult};
use crate::worker::Declared;

const MAX_CATALOG_BYTES: u64 = 1024 * 1024;

fn dispatch<E: std::fmt::Display>(error: E) -> BrainError {
    BrainError::Dispatch(error.to_string())
}

#[must_use]
pub fn card_of(manifest: &Manifest) -> Card {
    let mut keywords: Vec<String> = manifest.routing.verbs.clone();
    keywords.extend(manifest.routing.nouns.iter().cloned());
    Card {
        id: manifest.id.clone(),
        name: manifest.name.clone(),
        description: manifest.description.clone(),
        keywords,
        capabilities: manifest.capabilities.clone(),
        nouns: manifest.routing.nouns.clone(),
        phrases: manifest.routing.phrases.clone(),
        heavy: manifest.profile.heavy,
        project: manifest.profile.project,
        ..Card::default()
    }
}

pub fn load_agents(root: &Path, settings: &Settings) -> BrainResult<(Catalog, Index, Declared)> {
    let mut registry = Registry::new();
    registry.refresh(&[Root {
        path: root.to_path_buf(),
        origin: Origin::System,
        layout: Layout::Categorized,
    }]);
    let manifests: Vec<Manifest> = registry
        .snapshot()
        .agents
        .values()
        .map(|entry| entry.manifest.clone())
        .collect();
    if manifests.is_empty() {
        return Err(BrainError::Input("agents_empty"));
    }
    let catalog = Catalog::build(&manifests, settings).map_err(dispatch)?;
    let cards = manifests.iter().map(card_of).collect();
    let declared = manifests
        .iter()
        .map(|m| (m.id.clone(), m.tools.iter().cloned().collect()))
        .collect();
    Ok((catalog, Index::new(cards), declared))
}

fn read_capped(path: &Path) -> BrainResult<Vec<u8>> {
    let meta = std::fs::metadata(path).map_err(|_| BrainError::Input("catalog_missing"))?;
    if !meta.is_file() || meta.len() > MAX_CATALOG_BYTES {
        return Err(BrainError::Input("catalog_size"));
    }
    std::fs::read(path).map_err(|_| BrainError::Input("catalog_missing"))
}

pub fn apply_signed_catalog(
    hub: &Hub,
    catalog: &Path,
    public_key_hex: &Path,
    last_serial: u64,
) -> BrainResult<u64> {
    let signed: SignedCatalog = serde_json::from_slice(&read_capped(catalog)?)
        .map_err(|_| BrainError::Input("catalog_json"))?;
    let key_text = String::from_utf8(read_capped(public_key_hex)?)
        .map_err(|_| BrainError::Input("catalog_key"))?;
    let key: [u8; 32] = hex::decode(key_text.trim())
        .map_err(|_| BrainError::Input("catalog_key"))?
        .try_into()
        .map_err(|_| BrainError::Input("catalog_key"))?;
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_secs());
    let verified = verify_catalog(&signed, &key, now, last_serial).map_err(dispatch)?;
    hub.apply_catalog(&verified).map_err(dispatch)?;
    Ok(verified.serial)
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Paths {
    pub agents: PathBuf,
    pub catalog: Option<PathBuf>,
    pub public_key: Option<PathBuf>,
}

pub fn build_hub(paths: &Paths) -> BrainResult<(Arc<Hub>, u64)> {
    use nuxiva_mcp_core::{MemorySink, PolicyConfig, Settings as McpSettings, SharedSecrets};
    let hub = Hub::new(
        McpSettings::default(),
        PolicyConfig::default(),
        Arc::new(SharedSecrets::default()),
        Box::new(MemorySink::default()),
        None,
    )
    .map_err(dispatch)?;
    let serial = match (&paths.catalog, &paths.public_key) {
        (Some(catalog), Some(key)) => apply_signed_catalog(&hub, catalog, key, 0)?,
        (None, None) => 0,
        _ => return Err(BrainError::Input("catalog_pair")),
    };
    Ok((Arc::new(hub), serial))
}
