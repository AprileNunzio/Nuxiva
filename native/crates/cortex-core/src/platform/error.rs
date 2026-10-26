use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CortexError {
    EmptyInput,
    InputTooLong,
    ForbiddenCharacters,
    InvalidIdentifier,
    InvalidKeyLength,
    EncryptionFailed,
    DecryptionFailed,
    MalformedCiphertext,
    MalformedSignature,
    KeyDerivationFailed,
    RandomUnavailable,
    EmptyVector,
    NonFiniteVector,
    DimensionMismatch,
    InvalidDimension,
    InvalidWeight,
    InvalidThresholds,
    DuplicateVector,
    CapacityExceeded,
    UnknownNeuron,
    SnapshotInvalid,
    SlotSchemaInvalid,
    SlotUnknown,
    SlotRequiredMissing,
    SlotTypeMismatch,
    SlotValueNotAllowed,
}

impl CortexError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::EmptyInput => "cortex.input.empty",
            Self::InputTooLong => "cortex.input.too_long",
            Self::ForbiddenCharacters => "cortex.input.forbidden_characters",
            Self::InvalidIdentifier => "cortex.input.invalid_identifier",
            Self::InvalidKeyLength => "cortex.crypto.invalid_key_length",
            Self::EncryptionFailed => "cortex.crypto.encryption_failed",
            Self::DecryptionFailed => "cortex.crypto.decryption_failed",
            Self::MalformedCiphertext => "cortex.crypto.malformed_ciphertext",
            Self::MalformedSignature => "cortex.crypto.malformed_signature",
            Self::KeyDerivationFailed => "cortex.crypto.key_derivation_failed",
            Self::RandomUnavailable => "cortex.crypto.random_unavailable",
            Self::EmptyVector => "cortex.vector.empty",
            Self::NonFiniteVector => "cortex.vector.non_finite",
            Self::DimensionMismatch => "cortex.vector.dimension_mismatch",
            Self::InvalidDimension => "cortex.vector.invalid_dimension",
            Self::InvalidWeight => "cortex.neuron.invalid_weight",
            Self::InvalidThresholds => "cortex.router.invalid_thresholds",
            Self::DuplicateVector => "cortex.neuron.duplicate_vector",
            Self::CapacityExceeded => "cortex.neuron.capacity_exceeded",
            Self::UnknownNeuron => "cortex.neuron.unknown",
            Self::SnapshotInvalid => "cortex.snapshot.invalid",
            Self::SlotSchemaInvalid => "cortex.slots.schema_invalid",
            Self::SlotUnknown => "cortex.slots.unknown",
            Self::SlotRequiredMissing => "cortex.slots.required_missing",
            Self::SlotTypeMismatch => "cortex.slots.type_mismatch",
            Self::SlotValueNotAllowed => "cortex.slots.value_not_allowed",
        }
    }
}

impl fmt::Display for CortexError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.code())
    }
}

impl std::error::Error for CortexError {}

pub type CortexResult<T> = Result<T, CortexError>;
