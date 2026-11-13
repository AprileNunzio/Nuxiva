use std::path::PathBuf;
use std::time::Duration;

use crate::error::{McpError, McpResult};
use crate::guard::{parse_target, resolve};
use crate::policy::PolicyConfig;
use crate::secrets::{SecretProvider, bearer_header};
use crate::settings::Settings;
use crate::transport::{HttpConfig, Link, StdioSpec, spawn_http, spawn_stdio};
use crate::trust::{ServerEntry, TransportSpec};

pub async fn connect_server(
    entry: &ServerEntry,
    secrets: &dyn SecretProvider,
    policy: &PolicyConfig,
    settings: &Settings,
) -> McpResult<Link> {
    if !entry.enabled {
        return Err(McpError::NotPermitted);
    }
    entry.validate()?;
    match &entry.transport {
        TransportSpec::Stdio {
            program,
            args,
            env,
            secret_env,
            ..
        } => {
            let mut variables: Vec<(String, String)> =
                env.iter().map(|(k, v)| (k.clone(), v.clone())).collect();
            for (name, secret_id) in secret_env {
                variables.push((name.clone(), secrets.get(secret_id)?.expose().to_owned()));
            }
            let spec = StdioSpec {
                program: PathBuf::from(program),
                args: args.clone(),
                env: variables,
            };
            spawn_stdio(&spec, settings.max_message_bytes)
        }
        TransportSpec::Http {
            url,
            secret,
            network,
        } => {
            let target = parse_target(url)?;
            let network = network.as_ref().unwrap_or(&policy.network);
            let addresses = resolve(&target, network).await?;
            let pinned = addresses.first().copied().ok_or(McpError::NetworkDenied)?;
            let headers = match secret {
                Some(id) => vec![bearer_header(&secrets.get(id)?)],
                None => Vec::new(),
            };
            let config = HttpConfig {
                url: target.url.to_string(),
                headers,
                timeout: Duration::from_millis(
                    u64::try_from(settings.request_timeout_ms).unwrap_or(u64::MAX),
                ),
                protocol_version: None,
                pinned: Some((target.host, pinned)),
            };
            spawn_http(&config, settings.max_message_bytes)
        }
    }
}
