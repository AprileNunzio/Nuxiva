use std::time::Duration;

use reqwest::Url;
use reqwest::header::LOCATION;
use reqwest::redirect::Policy;

use nuxiva_mcp_core::{McpError, parse_target, resolve};

use super::config::FetchConfig;

pub struct Page {
    pub status: u16,
    pub body: Vec<u8>,
}

fn refusal(error: McpError) -> String {
    match error {
        McpError::NetworkDenied => "indirizzo non consentito dalla politica di rete".into(),
        _ => "indirizzo non valido".into(),
    }
}

async fn hop(config: &FetchConfig, raw: &str) -> Result<(Url, reqwest::Client), String> {
    let mut target = parse_target(raw).map_err(refusal)?;
    if !config.allows(&target.host) {
        return Err("host non presente nell'elenco consentito".into());
    }
    target.secure |= config.allow_insecure;
    let addresses = resolve(&target, &config.network).await.map_err(refusal)?;
    let pinned = addresses
        .first()
        .copied()
        .ok_or_else(|| "indirizzo non raggiungibile".to_owned())?;
    let client = reqwest::Client::builder()
        .redirect(Policy::none())
        .timeout(Duration::from_millis(config.timeout_ms))
        .user_agent(config.user_agent.as_str())
        .resolve(&target.host, pinned)
        .build()
        .map_err(|_| "client di rete non disponibile".to_owned())?;
    Ok((target.url, client))
}

pub async fn get(config: &FetchConfig, raw: &str) -> Result<Page, String> {
    let mut current = raw.to_owned();
    for _ in 0..=config.max_redirects {
        let (url, client) = hop(config, &current).await?;
        let mut response = client
            .get(url.clone())
            .send()
            .await
            .map_err(|_| "richiesta non riuscita".to_owned())?;
        let status = response.status();
        if status.is_redirection() {
            let location = response
                .headers()
                .get(LOCATION)
                .and_then(|v| v.to_str().ok())
                .ok_or_else(|| "reindirizzamento non valido".to_owned())?;
            current = url
                .join(location)
                .map_err(|_| "reindirizzamento non valido".to_owned())?
                .to_string();
            continue;
        }
        let mut body: Vec<u8> = Vec::new();
        while let Some(chunk) = response
            .chunk()
            .await
            .map_err(|_| "lettura non riuscita".to_owned())?
        {
            let room = config.max_bytes.saturating_sub(body.len());
            body.extend_from_slice(chunk.get(..room.min(chunk.len())).unwrap_or(&[]));
            if body.len() >= config.max_bytes {
                break;
            }
        }
        return Ok(Page {
            status: status.as_u16(),
            body,
        });
    }
    Err("troppi reindirizzamenti".into())
}
