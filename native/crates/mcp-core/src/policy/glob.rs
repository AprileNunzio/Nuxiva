#[must_use]
pub fn glob_match(pattern: &str, text: &str) -> bool {
    let p: Vec<char> = pattern.chars().collect();
    let t: Vec<char> = text.chars().collect();
    let (mut pi, mut ti) = (0usize, 0usize);
    let mut star: Option<usize> = None;
    let mut mark = 0usize;
    while ti < t.len() {
        match p.get(pi) {
            Some('*') => {
                star = Some(pi);
                pi = pi.saturating_add(1);
                mark = ti;
            }
            Some(c) if Some(c) == t.get(ti) => {
                pi = pi.saturating_add(1);
                ti = ti.saturating_add(1);
            }
            _ => match star {
                Some(s) => {
                    pi = s.saturating_add(1);
                    mark = mark.saturating_add(1);
                    ti = mark;
                }
                None => return false,
            },
        }
    }
    p.get(pi..)
        .is_some_and(|rest| rest.iter().all(|c| *c == '*'))
}
