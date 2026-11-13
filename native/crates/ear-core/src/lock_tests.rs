use nuxiva_seal_core::{Fernet, generate_key};

use crate::VoicePolicy;
use crate::lock::{LockError, VoiceLock};

fn voice(seed: u64, dim: usize) -> Vec<f32> {
    let mut state = seed.wrapping_mul(6_364_136_223_846_793_005).wrapping_add(1);
    (0..dim)
        .map(|_| {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            #[allow(clippy::cast_precision_loss)]
            let v = (state >> 40) as f32 / (1u64 << 24) as f32 - 0.5;
            v
        })
        .collect()
}

fn near(base: &[f32], seed: u64) -> Vec<f32> {
    base.iter()
        .zip(voice(seed, base.len()))
        .map(|(b, n)| b + 0.3 * n)
        .collect()
}

fn owner_rows(base: &[f32]) -> Vec<Vec<f32>> {
    (0..8_u64)
        .map(|i| near(base, i.saturating_add(100)))
        .collect()
}

fn fernet() -> Fernet {
    let key = generate_key().unwrap_or_default();
    Fernet::new(key.as_bytes()).unwrap_or_else(|_| unreachable!())
}

#[test]
fn needs_consent_and_enough_samples() {
    let base = voice(1, 64);
    let mut lock = VoiceLock::new(VoicePolicy::default(), 8.0);
    assert_eq!(
        lock.enroll("nunzio", &owner_rows(&base), false),
        Err(LockError::Consent)
    );
    assert_eq!(
        lock.enroll(
            "nunzio",
            &owner_rows(&base).into_iter().take(2).collect::<Vec<_>>(),
            true
        ),
        Err(LockError::Rows)
    );
    assert_eq!(
        lock.enroll("../x", &owner_rows(&base), true),
        Err(LockError::Slug)
    );
    assert!(!lock.enrolled());
}

#[test]
fn unlocks_only_for_the_owner() {
    let (owner, stranger) = (voice(1, 64), voice(2, 64));
    let mut lock = VoiceLock::new(VoicePolicy::default(), 8.0);
    assert!(lock.enroll("nunzio", &owner_rows(&owner), true).is_ok());
    assert!(!lock.observe(&near(&stranger, 5), 0.0).admit);
    assert!(!lock.unlocked(0.1));
    assert!(!lock.observe(&near(&owner, 6), 1.0).admit);
    let ok = lock.observe(&near(&owner, 7), 2.0);
    assert!(ok.admit && ok.unlocked);
    assert!(!lock.observe(&near(&stranger, 8), 3.0).admit);
    assert!(lock.unlocked(3.0));
    assert!(!lock.unlocked(20.0));
}

#[test]
fn seals_and_restores_without_plaintext() {
    let owner = voice(1, 64);
    let mut lock = VoiceLock::new(VoicePolicy::default(), 8.0);
    assert!(lock.enroll("nunzio", &owner_rows(&owner), true).is_ok());
    let f = fernet();
    let token = lock.seal(&f, 1_000).unwrap_or_default();
    assert!(!token.contains("nunzio"));
    let mut restored = VoiceLock::new(VoicePolicy::default(), 8.0);
    assert_eq!(
        restored.unseal(&f, &token, 1_001, false),
        Err(LockError::Consent)
    );
    assert!(restored.unseal(&f, &token, 1_001, true).is_ok());
    assert!(!restored.observe(&near(&owner, 6), 1.0).admit);
    assert!(restored.observe(&near(&owner, 7), 2.0).admit);
    assert_eq!(
        restored.unseal(&fernet(), &token, 1_001, true),
        Err(LockError::Seal)
    );
}

#[test]
fn revoke_wipes_the_voiceprint() {
    let owner = voice(1, 64);
    let mut lock = VoiceLock::new(VoicePolicy::default(), 8.0);
    assert!(lock.enroll("nunzio", &owner_rows(&owner), true).is_ok());
    lock.revoke();
    assert!(!lock.enrolled());
    assert!(lock.seal(&fernet(), 1).is_err());
    assert!(!lock.observe(&near(&owner, 6), 1.0).admit);
}
