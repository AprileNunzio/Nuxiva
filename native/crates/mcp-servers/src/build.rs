use std::sync::Arc;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use tokio::runtime::Handle;

use nuxiva_mcp_core::{
    Factory, InternalRegistry, McpError, McpResult, ToolServer, pair, serve, valid_server_id,
};

use crate::fetch::{FetchConfig, FetchServer};
use crate::fs::{FileServer, FsConfig};
use crate::mirror::{Dispatch, MirrorConfig, MirrorServer};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ServerDefinition {
    pub id: String,
    pub kind: String,
    pub config: Value,
}

fn build(
    definition: &ServerDefinition,
    dispatch: Option<&Arc<dyn Dispatch>>,
) -> McpResult<Arc<dyn ToolServer>> {
    if !valid_server_id(&definition.id) {
        return Err(McpError::InvalidName);
    }
    match definition.kind.as_str() {
        "filesystem" => {
            let config: FsConfig = serde_json::from_value(definition.config.clone())
                .map_err(|_| McpError::InvalidSettings)?;
            Ok(Arc::new(FileServer::new(&definition.id, &config)?))
        }
        "fetch" => {
            let config: FetchConfig = serde_json::from_value(definition.config.clone())
                .map_err(|_| McpError::InvalidSettings)?;
            Ok(Arc::new(FetchServer::new(&definition.id, &config)?))
        }
        "mirror" => {
            let config: MirrorConfig = serde_json::from_value(definition.config.clone())
                .map_err(|_| McpError::InvalidSettings)?;
            let dispatch = dispatch.ok_or(McpError::InvalidSettings)?;
            Ok(Arc::new(MirrorServer::new(
                &definition.id,
                &config,
                Arc::clone(dispatch),
            )?))
        }
        _ => Err(McpError::InvalidSettings),
    }
}

pub fn register_all(
    registry: &InternalRegistry,
    definitions: &[ServerDefinition],
    handle: &Handle,
    max_message: usize,
    max_in_flight: usize,
    dispatch: Option<&Arc<dyn Dispatch>>,
) -> McpResult<()> {
    let built: Vec<(String, Arc<dyn ToolServer>)> = definitions
        .iter()
        .map(|d| build(d, dispatch).map(|s| (d.id.clone(), s)))
        .collect::<McpResult<_>>()?;
    registry.clear();
    for (id, server) in built {
        let handle = handle.clone();
        let factory: Factory = Arc::new(move || {
            let (client, remote) = pair();
            let _entered = handle.enter();
            serve(Arc::clone(&server), remote, max_message, max_in_flight);
            Ok(client)
        });
        registry.register(&id, factory)?;
    }
    Ok(())
}
