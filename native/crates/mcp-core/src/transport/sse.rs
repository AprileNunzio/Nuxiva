use crate::error::{McpError, McpResult};

#[derive(Debug)]
pub struct SseParser {
    buffer: Vec<u8>,
    data: Vec<u8>,
    max_event: usize,
}

impl SseParser {
    #[must_use]
    pub fn new(max_event: usize) -> Self {
        Self {
            buffer: Vec::new(),
            data: Vec::new(),
            max_event,
        }
    }

    pub fn feed(&mut self, chunk: &[u8]) -> McpResult<Vec<Vec<u8>>> {
        self.buffer.extend_from_slice(chunk);
        let mut events = Vec::new();
        while let Some(end) = self.buffer.iter().position(|b| *b == b'\n') {
            let mut line: Vec<u8> = self.buffer.drain(..=end).collect();
            line.pop();
            if line.last() == Some(&b'\r') {
                line.pop();
            }
            if line.is_empty() {
                if !self.data.is_empty() {
                    events.push(std::mem::take(&mut self.data));
                }
                continue;
            }
            self.field(&line)?;
        }
        if self.buffer.len() > self.max_event {
            return Err(McpError::TooLarge);
        }
        Ok(events)
    }

    fn field(&mut self, line: &[u8]) -> McpResult<()> {
        let Some(rest) = line.strip_prefix(b"data:") else {
            return Ok(());
        };
        let rest = rest.strip_prefix(b" ").unwrap_or(rest);
        if !self.data.is_empty() {
            self.data.push(b'\n');
        }
        self.data.extend_from_slice(rest);
        if self.data.len() > self.max_event {
            return Err(McpError::TooLarge);
        }
        Ok(())
    }
}
