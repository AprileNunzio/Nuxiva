use crate::signal::Kind;

#[must_use]
pub fn detect_visual(class_name: &str, score: f64, width: f64, height: f64) -> (Option<Kind>, f64) {
    let lower = class_name.to_lowercase();
    if lower == "fall" || lower == "caduta" {
        return (Some(Kind::Fall), score.max(0.70));
    }
    if lower == "immobility" || lower == "immobilita" || lower == "immobilità" {
        return (Some(Kind::Immobility), score.max(0.65));
    }
    if (lower == "person" || lower == "persona")
        && height > 0.0
        && (width / height >= 1.6)
        && score >= 0.75
    {
        return (Some(Kind::Fall), score);
    }
    (None, 0.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_visual_heuristics() {
        assert_eq!(
            detect_visual("fall", 0.8, 100.0, 100.0),
            (Some(Kind::Fall), 0.8)
        );
        assert_eq!(
            detect_visual("immobility", 0.7, 100.0, 100.0),
            (Some(Kind::Immobility), 0.7)
        );
        assert_eq!(
            detect_visual("person", 0.85, 320.0, 150.0),
            (Some(Kind::Fall), 0.85)
        );
        assert_eq!(detect_visual("person", 0.85, 100.0, 300.0), (None, 0.0));
    }
}
