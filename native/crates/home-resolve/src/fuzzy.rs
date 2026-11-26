fn cell(rows: &[Vec<usize>], i: usize, j: usize) -> usize {
    rows.get(i)
        .and_then(|r| r.get(j))
        .copied()
        .unwrap_or(usize::MAX)
}

#[must_use]
pub fn distance(a: &str, b: &str) -> usize {
    let a: Vec<char> = a.chars().collect();
    let b: Vec<char> = b.chars().collect();
    let mut rows: Vec<Vec<usize>> = (0..=a.len())
        .map(|i| {
            (0..=b.len())
                .map(|j| {
                    if i == 0 {
                        j
                    } else if j == 0 {
                        i
                    } else {
                        0
                    }
                })
                .collect()
        })
        .collect();
    for (i, ca) in a.iter().enumerate() {
        for (j, cb) in b.iter().enumerate() {
            let cost = usize::from(ca != cb);
            let (i1, j1) = (i.saturating_add(1), j.saturating_add(1));
            let mut best = cell(&rows, i, j1)
                .saturating_add(1)
                .min(cell(&rows, i1, j).saturating_add(1))
                .min(cell(&rows, i, j).saturating_add(cost));
            if i > 0 && j > 0 {
                let swapped = a.get(i.saturating_sub(1)) == Some(cb)
                    && b.get(j.saturating_sub(1)) == Some(ca);
                if swapped {
                    best = best.min(
                        cell(&rows, i.saturating_sub(1), j.saturating_sub(1)).saturating_add(1),
                    );
                }
            }
            if let Some(slot) = rows.get_mut(i1).and_then(|r| r.get_mut(j1)) {
                *slot = best;
            }
        }
    }
    cell(&rows, a.len(), b.len())
}

fn allowed(len: usize) -> usize {
    match len {
        0..=3 => 0,
        4..=6 => 1,
        _ => 2,
    }
}

fn ratio(errors: usize, len: usize) -> f64 {
    let e = f64::from(u32::try_from(errors).unwrap_or(u32::MAX));
    let l = f64::from(u32::try_from(len.max(1)).unwrap_or(u32::MAX));
    (1.0 - e / l).max(0.0)
}

#[must_use]
pub fn similarity(a: &str, b: &str) -> f64 {
    if a == b {
        return 1.0;
    }
    if a.is_empty() || b.is_empty() {
        return 0.0;
    }
    if a.chars().any(|c| c.is_ascii_digit()) || b.chars().any(|c| c.is_ascii_digit()) {
        return 0.0;
    }
    let len = a.chars().count().max(b.chars().count());
    let errors = distance(a, b);
    if errors <= allowed(len) {
        return ratio(errors, len).max(0.75);
    }
    0.0
}

#[must_use]
pub fn root_similarity(word: &str, root: &str) -> f64 {
    if word.starts_with(root) {
        return 1.0;
    }
    let root_len = root.chars().count();
    if root_len < 4 {
        return 0.0;
    }
    let chars: Vec<char> = word.chars().collect();
    let mut best = 0.0_f64;
    for take in [
        root_len.saturating_sub(1),
        root_len,
        root_len.saturating_add(1),
    ] {
        if take == 0 || take > chars.len() {
            continue;
        }
        let head: String = chars.iter().take(take).collect();
        let errors = distance(&head, root);
        if errors <= 1 {
            best = best.max(ratio(errors, root_len).max(0.8));
        }
    }
    best
}
