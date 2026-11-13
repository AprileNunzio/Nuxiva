use std::collections::HashMap;

use crate::path::{file_name, join, parent, stem};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Target {
    File(u32),
    Package(u32),
}

#[derive(Debug)]
pub struct Index<'a> {
    paths: &'a [String],
    python: HashMap<String, Vec<u32>>,
    packages: HashMap<String, u32>,
}

const SCRIPT_EXT: [&str; 8] = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"];

fn module_parts(path: &str) -> Vec<&str> {
    let without = path.strip_suffix(".py").unwrap_or(path);
    let mut parts: Vec<&str> = without.split('/').collect();
    if parts.last() == Some(&"__init__") {
        parts.pop();
    }
    parts
}

fn is_module_root(path: &str) -> bool {
    matches!(stem(path), "mod" | "lib" | "main")
}

fn children_dir(path: &str) -> Option<String> {
    let dir = parent(path);
    if is_module_root(path) {
        Some(dir.to_owned())
    } else {
        join(dir, stem(path)).or_else(|| Some(stem(path).to_owned()))
    }
}

fn common_prefix(a: &str, b: &str) -> usize {
    a.split('/')
        .zip(b.split('/'))
        .take_while(|(x, y)| x == y)
        .count()
}

impl<'a> Index<'a> {
    #[must_use]
    pub fn new(paths: &'a [String], packages: HashMap<String, u32>) -> Self {
        let mut python: HashMap<String, Vec<u32>> = HashMap::new();
        for (id, path) in paths.iter().enumerate() {
            if !std::path::Path::new(path)
                .extension()
                .is_some_and(|e| e.eq_ignore_ascii_case("py"))
            {
                continue;
            }
            let parts = module_parts(path);
            let Ok(id) = u32::try_from(id) else { continue };
            for start in 0..parts.len() {
                let key = parts.get(start..).unwrap_or(&[]).join(".");
                if !key.is_empty() {
                    python.entry(key).or_default().push(id);
                }
            }
        }
        Self {
            paths,
            python,
            packages,
        }
    }

    #[must_use]
    pub fn file(&self, path: &str) -> Option<u32> {
        self.paths
            .binary_search_by(|p| p.as_str().cmp(path))
            .ok()
            .and_then(|i| u32::try_from(i).ok())
    }

    fn first(&self, candidates: &[String]) -> Option<u32> {
        candidates.iter().find_map(|c| self.file(c))
    }

    fn package(&self, name: &str) -> Option<Target> {
        let flat = name.replace('_', "-");
        self.packages
            .get(name)
            .or_else(|| self.packages.get(&flat))
            .map(|p| Target::Package(*p))
    }

    fn rust_root(&self, path: &str) -> Option<String> {
        let mut dir = parent(path).to_owned();
        loop {
            for root in ["lib.rs", "main.rs"] {
                let candidate = if dir.is_empty() {
                    root.to_owned()
                } else {
                    format!("{dir}/{root}")
                };
                if self.file(&candidate).is_some() {
                    return Some(dir);
                }
            }
            if dir.is_empty() {
                return None;
            }
            let up = parent(&dir).to_owned();
            dir = up;
        }
    }

    fn rust_walk(&self, base: &str, segments: &[&str]) -> Option<u32> {
        for count in (1..=segments.len()).rev() {
            let rel = segments.get(..count).unwrap_or(&[]).join("/");
            let stub = if base.is_empty() {
                rel
            } else {
                format!("{base}/{rel}")
            };
            if let Some(found) = self.first(&[format!("{stub}.rs"), format!("{stub}/mod.rs")]) {
                return Some(found);
            }
        }
        None
    }

    fn rust_use(&self, from: &str, path: &str) -> Option<Target> {
        let segments: Vec<&str> = path.split("::").filter(|s| !s.is_empty()).collect();
        let (first, rest) = segments.split_first()?;
        match *first {
            "crate" => {
                let root = self.rust_root(from)?;
                self.rust_walk(&root, rest).map(Target::File)
            }
            "self" => self.rust_walk(&children_dir(from)?, rest).map(Target::File),
            "super" => {
                let own = children_dir(from)?;
                let base = if is_module_root(from) {
                    parent(&own).to_owned()
                } else {
                    parent(from).to_owned()
                };
                let rest: Vec<&str> = rest.iter().copied().filter(|s| *s != "super").collect();
                self.rust_walk(&base, &rest).map(Target::File)
            }
            _ => self
                .rust_walk(&children_dir(from)?, &segments)
                .map(Target::File)
                .or_else(|| self.package(first)),
        }
    }

    fn rust_mod(&self, from: &str, name: &str) -> Option<Target> {
        let base = children_dir(from)?;
        self.rust_walk(&base, &[name]).map(Target::File)
    }

    fn python(&self, from: &str, dotted: &str) -> Option<Target> {
        let dots = dotted.chars().take_while(|c| *c == '.').count();
        let name = dotted.trim_start_matches('.');
        if dots > 0 {
            let mut base = parent(from).to_owned();
            for _ in 1..dots {
                base = parent(&base).to_owned();
            }
            let rel = name.replace('.', "/");
            let stub = if rel.is_empty() {
                base.clone()
            } else {
                join(&base, &rel)?
            };
            let init = if stub.is_empty() {
                "__init__.py".to_owned()
            } else {
                format!("{stub}/__init__.py")
            };
            return self.first(&[format!("{stub}.py"), init]).map(Target::File);
        }
        let segments: Vec<&str> = name.split('.').collect();
        for count in (1..=segments.len()).rev() {
            let key = segments.get(..count).unwrap_or(&[]).join(".");
            let Some(found) = self.python.get(&key) else {
                continue;
            };
            let best = found
                .iter()
                .filter_map(|id| {
                    usize::try_from(*id)
                        .ok()
                        .and_then(|i| self.paths.get(i))
                        .map(|p| (*id, p))
                })
                .filter(|(_, p)| p.as_str() != from)
                .max_by(|(_, a), (_, b)| {
                    common_prefix(a, from)
                        .cmp(&common_prefix(b, from))
                        .then_with(|| b.cmp(a))
                });
            if let Some((id, _)) = best {
                return Some(Target::File(id));
            }
        }
        None
    }

    fn script(&self, from: &str, spec: &str) -> Option<Target> {
        if !spec.starts_with('.') {
            return None;
        }
        let joined = join(parent(from), spec)?;
        let mut candidates = vec![joined.clone()];
        let trimmed = joined
            .rsplit_once('.')
            .filter(|(_, ext)| matches!(*ext, "js" | "mjs" | "cjs" | "jsx"))
            .map(|(s, _)| s.to_owned());
        for base in std::iter::once(&joined).chain(trimmed.iter()) {
            for ext in SCRIPT_EXT {
                candidates.push(format!("{base}{ext}"));
            }
            for ext in SCRIPT_EXT {
                candidates.push(format!("{base}/index{ext}"));
            }
        }
        self.first(&candidates).map(Target::File)
    }

    fn markdown(&self, from: &str, target: &str) -> Option<Target> {
        let clean = target.trim_start_matches("./");
        let joined = join(parent(from), clean)?;
        self.file(&joined)
            .or_else(|| self.file(clean))
            .map(Target::File)
    }

    #[must_use]
    pub fn resolve(&self, from: &str, spec: &str) -> Option<Target> {
        let (scheme, value) = spec.split_once(':')?;
        match scheme {
            "mod" => self.rust_mod(from, value),
            "use" => self.rust_use(from, value),
            "py" => self.python(from, value),
            "js" => self.script(from, value),
            "md" => self.markdown(from, value),
            "dep" => self.package(value),
            _ => None,
        }
    }

    #[must_use]
    pub fn mention(&self, from: &str, token: &str) -> Option<u32> {
        let clean = token.trim_start_matches("./").trim_end_matches('/');
        self.file(clean)
            .or_else(|| join(parent(from), clean).and_then(|j| self.file(&j)))
    }

    #[must_use]
    pub fn is_cargo(path: &str) -> bool {
        file_name(path) == "Cargo.toml"
    }
}
