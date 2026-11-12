use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum ActionError {
    #[error("invalid line range {start_line}..={end_line} (total lines: {total_lines})")]
    InvalidLineRange {
        start_line: usize,
        end_line: usize,
        total_lines: usize,
    },
    #[error("target content not found in range {start_line}..={end_line}")]
    TargetNotFound { start_line: usize, end_line: usize },
    #[error(
        "ambiguous target content ({matches} matches) in range {start_line}..={end_line}; set allow_multiple=true or narrow the range"
    )]
    AmbiguousTarget {
        start_line: usize,
        end_line: usize,
        matches: usize,
    },
    #[error("overlapping replacement chunks between lines {first_end} and {second_start}")]
    OverlappingChunks {
        first_end: usize,
        second_start: usize,
    },
    #[error("empty replacement chunks list")]
    EmptyChunks,
    #[error("merge conflict on '{path}' between workers '{first_worker}' and '{second_worker}'")]
    MergeConflict {
        path: String,
        first_worker: String,
        second_worker: String,
    },
    #[error("invalid path '{0}'")]
    InvalidPath(String),
}
