use crate::model::Case;

fn field(hasher: &mut blake3::Hasher, value: &str) {
    hasher.update(&u64::try_from(value.len()).unwrap_or(u64::MAX).to_le_bytes());
    hasher.update(value.as_bytes());
}

#[must_use]
pub fn fingerprint(cases: &[Case]) -> String {
    let mut ordered: Vec<&Case> = cases.iter().collect();
    ordered.sort_by(|a, b| a.id.cmp(&b.id));
    let mut hasher = blake3::Hasher::new();
    hasher.update(b"nuxiva.eval.dataset.v1");
    for case in ordered {
        field(&mut hasher, &case.id);
        field(&mut hasher, &case.lang);
        field(&mut hasher, &format!("{:?}", case.category));
        field(&mut hasher, &case.text);
        field(
            &mut hasher,
            case.external_content.as_deref().unwrap_or_default(),
        );
        field(&mut hasher, &case.expected.intent);
        for effect in &case.expected.effects {
            field(&mut hasher, &format!("{effect:?}"));
        }
        hasher.update(&[0xff]);
    }
    hasher.finalize().to_hex().to_string()
}
