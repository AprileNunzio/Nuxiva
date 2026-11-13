fn strip_blocks(input: &str, open: &str, close: &str) -> String {
    let lower = input.to_ascii_lowercase();
    let mut out = String::with_capacity(input.len());
    let mut at = 0usize;
    while let Some(found) = lower.get(at..).and_then(|rest| rest.find(open)) {
        let start = at.saturating_add(found);
        out.push_str(input.get(at..start).unwrap_or(""));
        out.push(' ');
        let after = start.saturating_add(open.len());
        match lower.get(after..).and_then(|rest| rest.find(close)) {
            Some(end) => at = after.saturating_add(end).saturating_add(close.len()),
            None => return out,
        }
    }
    out.push_str(input.get(at..).unwrap_or(""));
    out
}

fn strip_tags(input: &str) -> String {
    let mut out = String::with_capacity(input.len());
    let mut rest = input;
    while let Some(open) = rest.find('<') {
        out.push_str(rest.get(..open).unwrap_or(""));
        let tail = rest.get(open.saturating_add(1)..).unwrap_or("");
        match tail.find('>') {
            Some(end) if end > 0 => {
                out.push(' ');
                rest = tail.get(end.saturating_add(1)..).unwrap_or("");
            }
            _ => {
                out.push('<');
                rest = tail;
            }
        }
    }
    out.push_str(rest);
    out
}

pub fn plain(html: &str, limit: usize) -> String {
    let no_script = strip_blocks(html, "<script", "</script>");
    let no_style = strip_blocks(&no_script, "<style", "</style>");
    let bare = strip_tags(&no_style);
    let joined = bare.split_whitespace().collect::<Vec<_>>().join(" ");
    joined.chars().take(limit).collect()
}
