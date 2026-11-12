use serde::{Deserialize, Serialize};

use crate::error::ActionError;

pub const MAX_VIEW_LINES: usize = 800;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LineRangeView {
    pub start_line: usize,
    pub end_line: usize,
    pub total_lines: usize,
    pub content: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReplacementChunk {
    pub start_line: usize,
    pub end_line: usize,
    pub target_content: String,
    pub replacement_content: String,
    #[serde(default)]
    pub allow_multiple: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PatchOutcome {
    pub updated_content: String,
    pub replacements_applied: usize,
    pub previous_lines: usize,
    pub new_lines: usize,
}

fn split_lines_preserving_empty(content: &str) -> Vec<&str> {
    if content.is_empty() {
        Vec::new()
    } else {
        content.lines().collect()
    }
}

pub fn view_line_range(
    content: &str,
    start_line: usize,
    end_line: usize,
) -> Result<LineRangeView, ActionError> {
    let lines = split_lines_preserving_empty(content);
    let total_lines = lines.len();
    if total_lines == 0 {
        return Ok(LineRangeView {
            start_line: 0,
            end_line: 0,
            total_lines: 0,
            content: String::new(),
        });
    }
    if start_line == 0 || start_line > end_line || start_line > total_lines {
        return Err(ActionError::InvalidLineRange {
            start_line,
            end_line,
            total_lines,
        });
    }
    let clamped_end = end_line
        .min(total_lines)
        .min(start_line.saturating_add(MAX_VIEW_LINES).saturating_sub(1));
    let start_idx = start_line.saturating_sub(1);
    let slice = lines
        .get(start_idx..clamped_end)
        .ok_or(ActionError::InvalidLineRange {
            start_line,
            end_line: clamped_end,
            total_lines,
        })?;

    let mut formatted = Vec::with_capacity(slice.len());
    for (offset, line) in slice.iter().enumerate() {
        let line_no = start_line.saturating_add(offset);
        formatted.push(format!("{line_no}: {line}"));
    }

    Ok(LineRangeView {
        start_line,
        end_line: clamped_end,
        total_lines,
        content: formatted.join("\n"),
    })
}

fn validate_and_sort_chunks(
    chunks: &[ReplacementChunk],
    total_lines: usize,
) -> Result<Vec<ReplacementChunk>, ActionError> {
    if chunks.is_empty() {
        return Err(ActionError::EmptyChunks);
    }
    let mut sorted = chunks.to_vec();
    sorted.sort_by_key(|c| (c.start_line, c.end_line));
    for chunk in &sorted {
        if chunk.start_line == 0
            || chunk.start_line > chunk.end_line
            || chunk.end_line > total_lines
            || chunk.target_content.is_empty()
        {
            return Err(ActionError::InvalidLineRange {
                start_line: chunk.start_line,
                end_line: chunk.end_line,
                total_lines,
            });
        }
    }
    for pair in sorted.windows(2) {
        if let [first, second] = pair {
            if first.end_line >= second.start_line {
                return Err(ActionError::OverlappingChunks {
                    first_end: first.end_line,
                    second_start: second.start_line,
                });
            }
        }
    }
    Ok(sorted)
}

pub fn apply_surgical_patches(
    content: &str,
    chunks: &[ReplacementChunk],
) -> Result<PatchOutcome, ActionError> {
    let normalized = content.replace("\r\n", "\n");
    let trailing_newline = normalized.ends_with('\n');
    let lines: Vec<&str> = split_lines_preserving_empty(&normalized);
    let previous_lines = lines.len();
    let sorted = validate_and_sort_chunks(chunks, previous_lines)?;

    let mut output_segments: Vec<String> = Vec::new();
    let mut cursor_idx: usize = 0;
    let mut total_replacements: usize = 0;

    for chunk in &sorted {
        let start_idx = chunk.start_line.saturating_sub(1);
        let end_idx = chunk.end_line;

        if cursor_idx < start_idx {
            if let Some(before) = lines.get(cursor_idx..start_idx) {
                for &line in before {
                    output_segments.push(line.to_owned());
                }
            }
        }

        let range_slice = lines
            .get(start_idx..end_idx)
            .ok_or(ActionError::InvalidLineRange {
                start_line: chunk.start_line,
                end_line: chunk.end_line,
                total_lines: previous_lines,
            })?;
        let window_text = range_slice.join("\n");
        let target_norm = chunk.target_content.replace("\r\n", "\n");
        let replacement_norm = chunk.replacement_content.replace("\r\n", "\n");

        let match_count = window_text.matches(&target_norm).count();
        if match_count == 0 {
            return Err(ActionError::TargetNotFound {
                start_line: chunk.start_line,
                end_line: chunk.end_line,
            });
        }
        if match_count > 1 && !chunk.allow_multiple {
            return Err(ActionError::AmbiguousTarget {
                start_line: chunk.start_line,
                end_line: chunk.end_line,
                matches: match_count,
            });
        }

        let replaced_window = if chunk.allow_multiple {
            window_text.replace(&target_norm, &replacement_norm)
        } else {
            window_text.replacen(&target_norm, &replacement_norm, 1)
        };
        total_replacements =
            total_replacements.saturating_add(if chunk.allow_multiple { match_count } else { 1 });

        if !replaced_window.is_empty() {
            for line in replaced_window.split('\n') {
                output_segments.push(line.to_owned());
            }
        }
        cursor_idx = end_idx;
    }

    if cursor_idx < previous_lines {
        if let Some(rest) = lines.get(cursor_idx..previous_lines) {
            for &line in rest {
                output_segments.push(line.to_owned());
            }
        }
    }

    let new_lines = output_segments.len();
    let mut updated_content = output_segments.join("\n");
    if trailing_newline && !updated_content.ends_with('\n') && !updated_content.is_empty() {
        updated_content.push('\n');
    }

    Ok(PatchOutcome {
        updated_content,
        replacements_applied: total_replacements,
        previous_lines,
        new_lines,
    })
}
