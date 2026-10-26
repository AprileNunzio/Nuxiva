use std::collections::{BTreeMap, BTreeSet};

use super::types::{SlotDefinition, SlotType, SlotValue};
use crate::platform::error::{CortexError, CortexResult};
use crate::platform::sanitizer::{sanitize_identifier, sanitize_utterance};

pub const MAX_SLOTS: usize = 32;
pub const MAX_SLOT_VALUE_CHARS: usize = 256;
pub const MAX_ALLOWED_VALUES: usize = 64;

pub fn validate_schema(definitions: &[SlotDefinition]) -> CortexResult<()> {
    if definitions.len() > MAX_SLOTS {
        return Err(CortexError::SlotSchemaInvalid);
    }
    let mut names = BTreeSet::new();
    for definition in definitions {
        sanitize_identifier(&definition.name).map_err(|_| CortexError::SlotSchemaInvalid)?;
        sanitize_utterance(&definition.entity_label, MAX_SLOT_VALUE_CHARS)
            .map_err(|_| CortexError::SlotSchemaInvalid)?;
        let enumerated = definition.data_type == SlotType::Enumeration;
        let bounded = definition.allowed_values.len() <= MAX_ALLOWED_VALUES;
        let consistent = enumerated != definition.allowed_values.is_empty();
        if !names.insert(definition.name.as_str()) || !bounded || !consistent {
            return Err(CortexError::SlotSchemaInvalid);
        }
    }
    Ok(())
}

fn coerce(definition: &SlotDefinition, raw: &str) -> CortexResult<SlotValue> {
    let cleaned = sanitize_utterance(raw, MAX_SLOT_VALUE_CHARS)?;
    match definition.data_type {
        SlotType::Text => Ok(SlotValue::Text(cleaned)),
        SlotType::Number => cleaned
            .parse::<f64>()
            .ok()
            .filter(|value| value.is_finite())
            .map(SlotValue::Number)
            .ok_or(CortexError::SlotTypeMismatch),
        SlotType::Boolean => match cleaned.as_str() {
            "true" => Ok(SlotValue::Boolean(true)),
            "false" => Ok(SlotValue::Boolean(false)),
            _ => Err(CortexError::SlotTypeMismatch),
        },
        SlotType::Enumeration => {
            if definition.allowed_values.iter().any(|v| v == &cleaned) {
                Ok(SlotValue::Text(cleaned))
            } else {
                Err(CortexError::SlotValueNotAllowed)
            }
        }
    }
}

pub fn validate_slots(
    definitions: &[SlotDefinition],
    extracted: &BTreeMap<String, String>,
) -> CortexResult<BTreeMap<String, SlotValue>> {
    validate_schema(definitions)?;
    if extracted
        .keys()
        .any(|name| !definitions.iter().any(|d| &d.name == name))
    {
        return Err(CortexError::SlotUnknown);
    }
    let mut validated = BTreeMap::new();
    for definition in definitions {
        match extracted.get(&definition.name) {
            Some(raw) => {
                validated.insert(definition.name.clone(), coerce(definition, raw)?);
            }
            None if definition.required => return Err(CortexError::SlotRequiredMissing),
            None => {}
        }
    }
    Ok(validated)
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use super::{
        CortexError, SlotDefinition, SlotType, SlotValue, validate_schema, validate_slots,
    };

    fn definition(
        name: &str,
        data_type: SlotType,
        required: bool,
        allowed: &[&str],
    ) -> SlotDefinition {
        SlotDefinition {
            name: name.to_owned(),
            entity_label: format!("label {name}"),
            data_type,
            required,
            allowed_values: allowed.iter().map(|v| (*v).to_owned()).collect(),
        }
    }

    fn extracted(pairs: &[(&str, &str)]) -> BTreeMap<String, String> {
        pairs
            .iter()
            .map(|(k, v)| ((*k).to_owned(), (*v).to_owned()))
            .collect()
    }

    fn schema() -> Vec<SlotDefinition> {
        vec![
            definition("target_device", SlotType::Text, true, &[]),
            definition("volume_level", SlotType::Number, false, &[]),
            definition("muted", SlotType::Boolean, false, &[]),
            definition(
                "room",
                SlotType::Enumeration,
                false,
                &["kitchen", "bedroom"],
            ),
        ]
    }

    #[test]
    fn valid_extraction_is_typed() -> Result<(), CortexError> {
        let result = validate_slots(
            &schema(),
            &extracted(&[
                ("target_device", "  soggiorno\u{200B} lamp "),
                ("volume_level", "42.5"),
                ("muted", "false"),
                ("room", "kitchen"),
            ]),
        )?;
        assert_eq!(
            result.get("target_device"),
            Some(&SlotValue::Text("soggiorno lamp".to_owned()))
        );
        assert_eq!(result.get("volume_level"), Some(&SlotValue::Number(42.5)));
        assert_eq!(result.get("muted"), Some(&SlotValue::Boolean(false)));
        assert_eq!(
            result.get("room"),
            Some(&SlotValue::Text("kitchen".to_owned()))
        );
        Ok(())
    }

    #[test]
    fn missing_required_and_unknown_slots_are_rejected() {
        assert_eq!(
            validate_slots(&schema(), &extracted(&[("volume_level", "3")])),
            Err(CortexError::SlotRequiredMissing)
        );
        assert_eq!(
            validate_slots(
                &schema(),
                &extracted(&[("target_device", "x"), ("injected", "y")])
            ),
            Err(CortexError::SlotUnknown)
        );
    }

    #[test]
    fn wrong_types_and_values_are_rejected() {
        let base = [("target_device", "lamp")];
        for (name, value, expected) in [
            ("volume_level", "loud", CortexError::SlotTypeMismatch),
            ("volume_level", "NaN", CortexError::SlotTypeMismatch),
            ("volume_level", "inf", CortexError::SlotTypeMismatch),
            ("muted", "yes", CortexError::SlotTypeMismatch),
            ("room", "garage", CortexError::SlotValueNotAllowed),
        ] {
            let mut pairs = base.to_vec();
            pairs.push((name, value));
            assert_eq!(validate_slots(&schema(), &extracted(&pairs)), Err(expected));
        }
    }

    #[test]
    fn hostile_values_do_not_reach_the_skill() {
        let long = "a".repeat(300);
        for hostile in ["bad\u{0007}", "", long.as_str()] {
            assert!(validate_slots(&schema(), &extracted(&[("target_device", hostile)])).is_err());
        }
    }

    #[test]
    fn broken_schemas_are_rejected() {
        let duplicated = vec![
            definition("a", SlotType::Text, false, &[]),
            definition("a", SlotType::Text, false, &[]),
        ];
        let enum_without_values = vec![definition("a", SlotType::Enumeration, false, &[])];
        let values_without_enum = vec![definition("a", SlotType::Text, false, &["x"])];
        let bad_name = vec![definition("Bad Name", SlotType::Text, false, &[])];
        for broken in [
            duplicated,
            enum_without_values,
            values_without_enum,
            bad_name,
        ] {
            assert_eq!(
                validate_schema(&broken),
                Err(CortexError::SlotSchemaInvalid)
            );
        }
    }
}
