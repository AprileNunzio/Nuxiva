fn valid_model_id(value: &str) -> bool {
    value.len() <= 64
        && value
            .as_bytes()
            .first()
            .is_some_and(u8::is_ascii_alphanumeric)
        && !value.contains("..")
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-' | b'.'))
}

#[must_use]
pub fn model_candidates(name: &str, override_id: &str) -> Vec<String> {
    let override_id = override_id.trim();
    if valid_model_id(override_id) {
        return vec![override_id.to_owned()];
    }
    let name = name.trim().to_lowercase();
    if name.is_empty() || name == "nuxiva" {
        return vec!["ehi_nuxiva".to_owned()];
    }
    [format!("ehi_{name}"), name]
        .into_iter()
        .filter(|id| valid_model_id(id))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn candidates_follow_the_configured_name() {
        assert_eq!(model_candidates(" Maya ", ""), ["ehi_maya", "maya"]);
        assert_eq!(model_candidates("Ada", "ada_v2"), ["ada_v2"]);
        assert_eq!(model_candidates("", ""), ["ehi_nuxiva"]);
    }

    #[test]
    fn rejects_path_components_and_keeps_the_configured_identity() {
        assert_eq!(model_candidates("../../maya", ""), [] as [std::string::String; 0]);
        assert_eq!(model_candidates("maya/voice", ""), [] as [std::string::String; 0]);
        assert_eq!(model_candidates("Ada", "../other"), ["ehi_ada", "ada"]);
    }
}
