use crate::{Ceilings, McpError, Settings};

#[test]
fn defaults_are_valid() {
    assert_eq!(Settings::default().validate(), Ok(()));
}

#[test]
fn partial_json_uses_defaults() -> Result<(), McpError> {
    let settings = Settings::from_json("{\"max_pages\": 7}")?;
    assert_eq!(settings.max_pages, 7);
    assert_eq!(settings.max_name_len, Settings::default().max_name_len);
    Ok(())
}

#[test]
fn invalid_configuration_is_rejected_whole() {
    let over = format!("{{\"max_pages\": {}}}", Ceilings::PAGES + 1);
    for text in [
        "{\"max_pages\": 0}",
        over.as_str(),
        "{\"unknown\": 1}",
        "{\"max_pages\": \"x\"}",
        "{\"max_tools_per_server\": 600, \"max_tools_total\": 500}",
        "not json",
    ] {
        assert_eq!(
            Settings::from_json(text),
            Err(McpError::InvalidSettings),
            "{text}"
        );
    }
}
