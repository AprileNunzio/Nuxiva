use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum TlvTag {
    Anonymous,
    Context(u8),
    CommonProfile2(u16),
    CommonProfile4(u32),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum TlvValue {
    SignedInt(i64),
    UnsignedInt(u64),
    Boolean(bool),
    Float(f64),
    Utf8String(String),
    ByteString(Vec<u8>),
    Null,
    Structure(Vec<TlvElement>),
    Array(Vec<TlvElement>),
    List(Vec<TlvElement>),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TlvElement {
    pub tag: TlvTag,
    pub value: TlvValue,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TlvError {
    UnexpectedEof,
    InvalidType(u8),
    InvalidTag(u8),
    InvalidString,
    BufferOverflow,
    UnterminatedContainer,
}

impl std::fmt::Display for TlvError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::UnexpectedEof => write!(f, "Unexpected end of TLV data"),
            Self::InvalidType(t) => write!(f, "Invalid TLV element type: {t}"),
            Self::InvalidTag(t) => write!(f, "Invalid TLV tag control: {t}"),
            Self::InvalidString => write!(f, "Invalid UTF-8 string in TLV"),
            Self::BufferOverflow => write!(f, "TLV buffer overflow"),
            Self::UnterminatedContainer => write!(f, "Unterminated TLV container"),
        }
    }
}

impl std::error::Error for TlvError {}

#[derive(Debug)]
pub struct TlvEncoder {
    buf: Vec<u8>,
}

impl Default for TlvEncoder {
    fn default() -> Self {
        Self::new()
    }
}

impl TlvEncoder {
    pub fn new() -> Self {
        Self { buf: Vec::new() }
    }

    pub fn into_bytes(self) -> Vec<u8> {
        self.buf
    }

    pub fn as_slice(&self) -> &[u8] {
        &self.buf
    }

    fn write_control_and_tag(&mut self, element_type: u8, tag: &TlvTag) {
        let (tag_ctrl, tag_bytes): (u8, Vec<u8>) = match tag {
            TlvTag::Anonymous => (0x00, Vec::new()),
            TlvTag::Context(c) => (0x01, vec![*c]),
            TlvTag::CommonProfile2(cp) => (0x02, cp.to_le_bytes().to_vec()),
            TlvTag::CommonProfile4(cp) => (0x03, cp.to_le_bytes().to_vec()),
        };
        let ctrl = (tag_ctrl << 5) | (element_type & 0x1F);
        self.buf.push(ctrl);
        self.buf.extend_from_slice(&tag_bytes);
    }

    pub fn encode_element(&mut self, element: &TlvElement) {
        match &element.value {
            TlvValue::SignedInt(v) => {
                if *v >= i8::MIN as i64 && *v <= i8::MAX as i64 {
                    self.write_control_and_tag(0x00, &element.tag);
                    self.buf.push(*v as i8 as u8);
                } else if *v >= i16::MIN as i64 && *v <= i16::MAX as i64 {
                    self.write_control_and_tag(0x01, &element.tag);
                    self.buf.extend_from_slice(&(*v as i16).to_le_bytes());
                } else if *v >= i32::MIN as i64 && *v <= i32::MAX as i64 {
                    self.write_control_and_tag(0x02, &element.tag);
                    self.buf.extend_from_slice(&(*v as i32).to_le_bytes());
                } else {
                    self.write_control_and_tag(0x03, &element.tag);
                    self.buf.extend_from_slice(&v.to_le_bytes());
                }
            }
            TlvValue::UnsignedInt(v) => {
                if *v <= u8::MAX as u64 {
                    self.write_control_and_tag(0x04, &element.tag);
                    self.buf.push(*v as u8);
                } else if *v <= u16::MAX as u64 {
                    self.write_control_and_tag(0x05, &element.tag);
                    self.buf.extend_from_slice(&(*v as u16).to_le_bytes());
                } else if *v <= u32::MAX as u64 {
                    self.write_control_and_tag(0x06, &element.tag);
                    self.buf.extend_from_slice(&(*v as u32).to_le_bytes());
                } else {
                    self.write_control_and_tag(0x07, &element.tag);
                    self.buf.extend_from_slice(&v.to_le_bytes());
                }
            }
            TlvValue::Boolean(b) => {
                let element_type = if *b { 0x09 } else { 0x08 };
                self.write_control_and_tag(element_type, &element.tag);
            }
            TlvValue::Float(f) => {
                self.write_control_and_tag(0x0B, &element.tag);
                self.buf.extend_from_slice(&f.to_bits().to_le_bytes());
            }
            TlvValue::Utf8String(s) => {
                let bytes = s.as_bytes();
                let len = bytes.len();
                if len <= u8::MAX as usize {
                    self.write_control_and_tag(0x0C, &element.tag);
                    self.buf.push(len as u8);
                } else {
                    self.write_control_and_tag(0x0D, &element.tag);
                    self.buf.extend_from_slice(&(len as u16).to_le_bytes());
                }
                self.buf.extend_from_slice(bytes);
            }
            TlvValue::ByteString(b) => {
                let len = b.len();
                if len <= u8::MAX as usize {
                    self.write_control_and_tag(0x10, &element.tag);
                    self.buf.push(len as u8);
                } else {
                    self.write_control_and_tag(0x11, &element.tag);
                    self.buf.extend_from_slice(&(len as u16).to_le_bytes());
                }
                self.buf.extend_from_slice(b);
            }
            TlvValue::Null => {
                self.write_control_and_tag(0x14, &element.tag);
            }
            TlvValue::Structure(children) => {
                self.write_control_and_tag(0x15, &element.tag);
                for child in children {
                    self.encode_element(child);
                }
                self.buf.push(0x18);
            }
            TlvValue::Array(children) => {
                self.write_control_and_tag(0x16, &element.tag);
                for child in children {
                    self.encode_element(child);
                }
                self.buf.push(0x18);
            }
            TlvValue::List(children) => {
                self.write_control_and_tag(0x17, &element.tag);
                for child in children {
                    self.encode_element(child);
                }
                self.buf.push(0x18);
            }
        }
    }
}

#[derive(Debug)]
pub struct TlvDecoder<'a> {
    data: &'a [u8],
    cursor: usize,
}

impl<'a> TlvDecoder<'a> {
    pub fn new(data: &'a [u8]) -> Self {
        Self { data, cursor: 0 }
    }

    fn read_byte(&mut self) -> Result<u8, TlvError> {
        let b = *self.data.get(self.cursor).ok_or(TlvError::UnexpectedEof)?;
        self.cursor = self.cursor.checked_add(1).ok_or(TlvError::BufferOverflow)?;
        Ok(b)
    }

    fn read_exact(&mut self, len: usize) -> Result<&'a [u8], TlvError> {
        let end = self
            .cursor
            .checked_add(len)
            .ok_or(TlvError::BufferOverflow)?;
        if end > self.data.len() {
            return Err(TlvError::UnexpectedEof);
        }
        let slice = self
            .data
            .get(self.cursor..end)
            .ok_or(TlvError::UnexpectedEof)?;
        self.cursor = end;
        Ok(slice)
    }

    pub fn decode_next(&mut self) -> Result<Option<TlvElement>, TlvError> {
        if self.cursor >= self.data.len() {
            return Ok(None);
        }
        let ctrl = self.read_byte()?;
        if ctrl == 0x18 {
            return Ok(None);
        }
        let tag_ctrl = (ctrl >> 5) & 0x07;
        let element_type = ctrl & 0x1F;

        let tag = match tag_ctrl {
            0x00 => TlvTag::Anonymous,
            0x01 => TlvTag::Context(self.read_byte()?),
            0x02 => {
                let bytes = self.read_exact(2)?;
                let val =
                    u16::from_le_bytes([*bytes.first().unwrap_or(&0), *bytes.get(1).unwrap_or(&0)]);
                TlvTag::CommonProfile2(val)
            }
            0x03 => {
                let bytes = self.read_exact(4)?;
                let mut arr = [0u8; 4];
                arr.copy_from_slice(bytes);
                TlvTag::CommonProfile4(u32::from_le_bytes(arr))
            }
            _ => return Err(TlvError::InvalidTag(tag_ctrl)),
        };

        let value = match element_type {
            0x00 => TlvValue::SignedInt(self.read_byte()? as i8 as i64),
            0x01 => {
                let b = self.read_exact(2)?;
                TlvValue::SignedInt(i16::from_le_bytes([
                    *b.first().unwrap_or(&0),
                    *b.get(1).unwrap_or(&0),
                ]) as i64)
            }
            0x02 => {
                let b = self.read_exact(4)?;
                let mut arr = [0u8; 4];
                arr.copy_from_slice(b);
                TlvValue::SignedInt(i32::from_le_bytes(arr) as i64)
            }
            0x03 => {
                let b = self.read_exact(8)?;
                let mut arr = [0u8; 8];
                arr.copy_from_slice(b);
                TlvValue::SignedInt(i64::from_le_bytes(arr))
            }
            0x04 => TlvValue::UnsignedInt(self.read_byte()? as u64),
            0x05 => {
                let b = self.read_exact(2)?;
                TlvValue::UnsignedInt(u16::from_le_bytes([
                    *b.first().unwrap_or(&0),
                    *b.get(1).unwrap_or(&0),
                ]) as u64)
            }
            0x06 => {
                let b = self.read_exact(4)?;
                let mut arr = [0u8; 4];
                arr.copy_from_slice(b);
                TlvValue::UnsignedInt(u32::from_le_bytes(arr) as u64)
            }
            0x07 => {
                let b = self.read_exact(8)?;
                let mut arr = [0u8; 8];
                arr.copy_from_slice(b);
                TlvValue::UnsignedInt(u64::from_le_bytes(arr))
            }
            0x08 => TlvValue::Boolean(false),
            0x09 => TlvValue::Boolean(true),
            0x0A => {
                let b = self.read_exact(4)?;
                let mut arr = [0u8; 4];
                arr.copy_from_slice(b);
                TlvValue::Float(f32::from_bits(u32::from_le_bytes(arr)) as f64)
            }
            0x0B => {
                let b = self.read_exact(8)?;
                let mut arr = [0u8; 8];
                arr.copy_from_slice(b);
                TlvValue::Float(f64::from_bits(u64::from_le_bytes(arr)))
            }
            0x0C => {
                let len = self.read_byte()? as usize;
                let b = self.read_exact(len)?;
                let s = std::str::from_utf8(b).map_err(|_| TlvError::InvalidString)?;
                TlvValue::Utf8String(s.to_string())
            }
            0x0D => {
                let b_len = self.read_exact(2)?;
                let len =
                    u16::from_le_bytes([*b_len.first().unwrap_or(&0), *b_len.get(1).unwrap_or(&0)])
                        as usize;
                let b = self.read_exact(len)?;
                let s = std::str::from_utf8(b).map_err(|_| TlvError::InvalidString)?;
                TlvValue::Utf8String(s.to_string())
            }
            0x10 => {
                let len = self.read_byte()? as usize;
                let b = self.read_exact(len)?;
                TlvValue::ByteString(b.to_vec())
            }
            0x11 => {
                let b_len = self.read_exact(2)?;
                let len =
                    u16::from_le_bytes([*b_len.first().unwrap_or(&0), *b_len.get(1).unwrap_or(&0)])
                        as usize;
                let b = self.read_exact(len)?;
                TlvValue::ByteString(b.to_vec())
            }
            0x14 => TlvValue::Null,
            0x15 => {
                let mut children = Vec::new();
                while let Some(child) = self.decode_next()? {
                    children.push(child);
                }
                TlvValue::Structure(children)
            }
            0x16 => {
                let mut children = Vec::new();
                while let Some(child) = self.decode_next()? {
                    children.push(child);
                }
                TlvValue::Array(children)
            }
            0x17 => {
                let mut children = Vec::new();
                while let Some(child) = self.decode_next()? {
                    children.push(child);
                }
                TlvValue::List(children)
            }
            _ => return Err(TlvError::InvalidType(element_type)),
        };

        Ok(Some(TlvElement { tag, value }))
    }
}

pub fn encode_tlv(element: &TlvElement) -> Vec<u8> {
    let mut enc = TlvEncoder::new();
    enc.encode_element(element);
    enc.into_bytes()
}

pub fn decode_tlv(bytes: &[u8]) -> Result<Option<TlvElement>, TlvError> {
    let mut dec = TlvDecoder::new(bytes);
    dec.decode_next()
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::expect_used, clippy::panic)]
mod tests {
    use super::*;

    #[test]
    fn test_tlv_encode_decode_primitives() {
        let el = TlvElement {
            tag: TlvTag::Context(1),
            value: TlvValue::UnsignedInt(42),
        };
        let bytes = encode_tlv(&el);
        let decoded = decode_tlv(&bytes).unwrap().unwrap();
        assert_eq!(decoded.tag, TlvTag::Context(1));
        assert_eq!(decoded.value, TlvValue::UnsignedInt(42));
    }

    #[test]
    fn test_tlv_encode_decode_structure() {
        let el = TlvElement {
            tag: TlvTag::Anonymous,
            value: TlvValue::Structure(vec![
                TlvElement {
                    tag: TlvTag::Context(0),
                    value: TlvValue::Utf8String("Matter 1.6.1".to_string()),
                },
                TlvElement {
                    tag: TlvTag::Context(1),
                    value: TlvValue::Boolean(true),
                },
            ]),
        };
        let bytes = encode_tlv(&el);
        let decoded = decode_tlv(&bytes).unwrap().unwrap();
        match decoded.value {
            TlvValue::Structure(items) => {
                assert_eq!(items.len(), 2);
                assert_eq!(
                    items.first().unwrap().value,
                    TlvValue::Utf8String("Matter 1.6.1".to_string())
                );
                assert_eq!(items.get(1).unwrap().value, TlvValue::Boolean(true));
            }
            _ => panic!("Expected structure"),
        }
    }
}
