const ACCENTS: &[(char, char)] = &[
    ('à', 'a'),
    ('á', 'a'),
    ('â', 'a'),
    ('ä', 'a'),
    ('è', 'e'),
    ('é', 'e'),
    ('ê', 'e'),
    ('ë', 'e'),
    ('ì', 'i'),
    ('í', 'i'),
    ('î', 'i'),
    ('ï', 'i'),
    ('ò', 'o'),
    ('ó', 'o'),
    ('ô', 'o'),
    ('ö', 'o'),
    ('ù', 'u'),
    ('ú', 'u'),
    ('û', 'u'),
    ('ü', 'u'),
    ('ñ', 'n'),
    ('ç', 'c'),
];

fn fold(c: char) -> char {
    ACCENTS
        .iter()
        .find(|(from, _)| *from == c)
        .map_or(c, |(_, to)| *to)
}

#[must_use]
pub fn words(text: &str) -> Vec<String> {
    let mut out = String::with_capacity(text.len());
    for c in text.chars().flat_map(char::to_lowercase) {
        let c = fold(c);
        out.push(if c.is_ascii_alphanumeric() { c } else { ' ' });
    }
    out.split_whitespace().map(str::to_owned).collect()
}

fn distance(a: &[char], b: &[char]) -> usize {
    let mut prev: Vec<usize> = (0..=b.len()).collect();
    for (i, ca) in a.iter().enumerate() {
        let mut row = vec![i.saturating_add(1)];
        for (j, cb) in b.iter().enumerate() {
            let left = row.get(j).copied().unwrap_or(usize::MAX).saturating_add(1);
            let up = prev
                .get(j.saturating_add(1))
                .copied()
                .unwrap_or(usize::MAX)
                .saturating_add(1);
            let diag = prev
                .get(j)
                .copied()
                .unwrap_or(usize::MAX)
                .saturating_add(usize::from(ca != cb));
            row.push(left.min(up).min(diag));
        }
        prev = row;
    }
    prev.last().copied().unwrap_or(usize::MAX)
}

#[must_use]
pub fn similar(a: &str, b: &str) -> bool {
    if a == b {
        return true;
    }
    let a: Vec<char> = a.chars().collect();
    let b: Vec<char> = b.chars().collect();
    let allowed = match a.len().max(b.len()) {
        0..=3 => 0,
        4..=6 => 1,
        _ => 2,
    };
    allowed > 0 && distance(&a, &b) <= allowed
}
