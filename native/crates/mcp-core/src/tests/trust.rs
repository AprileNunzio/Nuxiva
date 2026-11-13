use std::collections::BTreeMap;

use ed25519_dalek::SigningKey;

use crate::{
    Catalog, Isolation, McpError, McpResult, NetworkPolicy, Risk, ServerEntry, SignedCatalog,
    TransportSpec, sign_catalog, verify_catalog,
};

fn key(seed: u8) -> SigningKey {
    SigningKey::from_bytes(&[seed; 32])
}

fn entry(id: &str) -> ServerEntry {
    ServerEntry {
        id: id.into(),
        enabled: true,
        max_risk: Risk::Files,
        honor_read_only: false,
        transport: TransportSpec::Http {
            url: "https://tools.example.test/mcp".into(),
            secret: Some("tok".into()),
            network: Some(NetworkPolicy::default()),
        },
    }
}

fn catalog(serial: u64) -> Catalog {
    Catalog {
        version: 1,
        serial,
        issued_at: 1_000,
        not_after: 2_000,
        servers: vec![entry("one"), entry("two")],
    }
}

#[test]
fn valid_catalog_round_trips() -> McpResult<()> {
    let signed = sign_catalog(&catalog(5), &key(1))?;
    let verified = verify_catalog(&signed, &key(1).verifying_key().to_bytes(), 1_500, 5)?;
    assert_eq!(verified, catalog(5));
    Ok(())
}

#[test]
fn forged_or_modified_catalogs_are_refused() -> McpResult<()> {
    let signed = sign_catalog(&catalog(5), &key(1))?;
    let public = key(1).verifying_key().to_bytes();
    let wrong_key = key(2).verifying_key().to_bytes();
    assert_eq!(
        verify_catalog(&signed, &wrong_key, 1_500, 0).err(),
        Some(McpError::SignatureInvalid)
    );
    let tampered = SignedCatalog {
        payload: signed
            .payload
            .replace("tools.example.test", "evil.example.test"),
        signature: signed.signature.clone(),
    };
    assert_eq!(
        verify_catalog(&tampered, &public, 1_500, 0).err(),
        Some(McpError::SignatureInvalid)
    );
    let garbage = SignedCatalog {
        payload: signed.payload.clone(),
        signature: "%%%".into(),
    };
    assert_eq!(
        verify_catalog(&garbage, &public, 1_500, 0).err(),
        Some(McpError::SignatureInvalid)
    );
    let short = SignedCatalog {
        payload: signed.payload,
        signature: "AAAA".into(),
    };
    assert_eq!(
        verify_catalog(&short, &public, 1_500, 0).err(),
        Some(McpError::SignatureInvalid)
    );
    Ok(())
}

#[test]
fn expiry_future_issue_and_rollback_are_refused() -> McpResult<()> {
    let signed = sign_catalog(&catalog(5), &key(1))?;
    let public = key(1).verifying_key().to_bytes();
    assert_eq!(
        verify_catalog(&signed, &public, 2_001, 0).err(),
        Some(McpError::CatalogExpired)
    );
    assert_eq!(
        verify_catalog(&signed, &public, 100, 0).err(),
        Some(McpError::SignatureInvalid)
    );
    assert_eq!(
        verify_catalog(&signed, &public, 1_500, 6).err(),
        Some(McpError::SignatureInvalid)
    );
    Ok(())
}

#[test]
fn invalid_entries_cannot_be_signed() {
    let mut duplicate = catalog(1);
    duplicate.servers.push(entry("one"));
    assert!(sign_catalog(&duplicate, &key(1)).is_err());
    let mut bad_id = catalog(1);
    bad_id.servers = vec![entry("Bad Id")];
    assert!(sign_catalog(&bad_id, &key(1)).is_err());
    let mut relative = catalog(1);
    relative.servers = vec![ServerEntry {
        transport: TransportSpec::Stdio {
            program: "server".into(),
            args: Vec::new(),
            env: BTreeMap::new(),
            secret_env: BTreeMap::new(),
            isolation: Isolation::Sandboxed,
        },
        ..entry("x")
    }];
    assert!(sign_catalog(&relative, &key(1)).is_err());
    let mut lower_env = catalog(1);
    lower_env.servers = vec![ServerEntry {
        transport: TransportSpec::Stdio {
            program: "/usr/bin/server".into(),
            args: Vec::new(),
            env: BTreeMap::from([("bad-name".to_owned(), "v".to_owned())]),
            secret_env: BTreeMap::new(),
            isolation: Isolation::Internal,
        },
        ..entry("x")
    }];
    assert!(sign_catalog(&lower_env, &key(1)).is_err());
    let mut bad_url = catalog(1);
    bad_url.servers = vec![ServerEntry {
        transport: TransportSpec::Http {
            url: "ftp://x.test".into(),
            secret: None,
            network: None,
        },
        ..entry("x")
    }];
    assert!(sign_catalog(&bad_url, &key(1)).is_err());
}

#[test]
fn unknown_fields_are_rejected_on_parse() -> McpResult<()> {
    let signed = sign_catalog(&catalog(1), &key(1))?;
    let extra = signed.payload.replacen('{', "{\"extra\":1,", 1);
    assert!(serde_json::from_str::<Catalog>(&extra).is_err());
    Ok(())
}
