use std::fs;
use std::os::unix::fs::PermissionsExt;

use super::Fixture;
use crate::vault::{Identity, Vault, VaultError};

fn identity() -> Identity {
    Identity {
        server: "https://192.168.1.10:8443".into(),
        node_id: "salotto-satellite".into(),
        name: "Salotto".into(),
        token: "segreto-token-abcdefghijklmnopqrstuvwxyz".into(),
        ca_pem: "-----BEGIN CERTIFICATE-----\nAA==\n-----END CERTIFICATE-----\n".into(),
    }
}

#[test]
fn identity_round_trips_and_is_encrypted_at_rest() -> Result<(), String> {
    let fx = Fixture::new("vault")?;
    let vault = Vault::new(fx.path().join("state"), Some("machine-a"));
    vault.save(&identity()).map_err(|e| e.to_string())?;
    assert_eq!(vault.load().map_err(|e| e.to_string())?, identity());
    let raw = fs::read(fx.path().join("state/identity.bin")).map_err(|e| e.to_string())?;
    assert!(!raw.windows(12).any(|w| w == b"segreto-toke"));
    let mode = fs::metadata(fx.path().join("state/vault.key"))
        .map_err(|e| e.to_string())?
        .permissions()
        .mode();
    assert_eq!(mode & 0o777, 0o600);
    Ok(())
}

#[test]
fn vault_is_bound_to_the_machine() -> Result<(), String> {
    let fx = Fixture::new("bound")?;
    Vault::new(fx.path(), Some("machine-a"))
        .save(&identity())
        .map_err(|e| e.to_string())?;
    assert_eq!(
        Vault::new(fx.path(), Some("machine-b")).load(),
        Err(VaultError::Corrupted)
    );
    Ok(())
}

#[test]
fn tampering_and_loose_permissions_are_refused() -> Result<(), String> {
    let fx = Fixture::new("tamper")?;
    let vault = Vault::new(fx.path(), None);
    vault.save(&identity()).map_err(|e| e.to_string())?;
    let path = fx.path().join("identity.bin");
    let mut raw = fs::read(&path).map_err(|e| e.to_string())?;
    if let Some(last) = raw.last_mut() {
        *last ^= 0x01;
    }
    fs::write(&path, &raw).map_err(|e| e.to_string())?;
    assert_eq!(vault.load(), Err(VaultError::Corrupted));
    fs::set_permissions(&path, fs::Permissions::from_mode(0o644)).map_err(|e| e.to_string())?;
    assert!(matches!(vault.load(), Err(VaultError::Insecure(_))));
    Ok(())
}

#[test]
fn destroy_removes_key_and_identity() -> Result<(), String> {
    let fx = Fixture::new("destroy")?;
    let vault = Vault::new(fx.path(), None);
    vault.save(&identity()).map_err(|e| e.to_string())?;
    vault.destroy().map_err(|e| e.to_string())?;
    assert!(!vault.exists());
    assert!(!fx.path().join("vault.key").exists());
    Ok(())
}
