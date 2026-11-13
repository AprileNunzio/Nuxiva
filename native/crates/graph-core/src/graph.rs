use sha2::{Digest, Sha256};

use crate::error::{GraphError, GraphResult};
use crate::model::{EdgeKind, Language, Node, NodeKind};

pub type RawEdge = (u32, u32, EdgeKind);

#[derive(Debug, Clone, Default)]
pub struct Csr {
    offsets: Vec<u32>,
    peers: Vec<u32>,
    kinds: Vec<EdgeKind>,
}

impl Csr {
    fn build(nodes: usize, edges: &[RawEdge], inbound: bool) -> GraphResult<Self> {
        u32::try_from(edges.len()).map_err(|_| GraphError::Capacity)?;
        let mut offsets = vec![0u32; nodes.saturating_add(1)];
        let mut peers = Vec::with_capacity(edges.len());
        let mut kinds = Vec::with_capacity(edges.len());
        for &(src, dst, kind) in edges {
            let (key, peer) = if inbound { (dst, src) } else { (src, dst) };
            let slot = usize::try_from(key)
                .map_err(|_| GraphError::Capacity)?
                .saturating_add(1);
            let cell = offsets.get_mut(slot).ok_or(GraphError::Capacity)?;
            *cell = cell.saturating_add(1);
            peers.push(peer);
            kinds.push(kind);
        }
        let mut acc = 0u32;
        for cell in &mut offsets {
            acc = acc.saturating_add(*cell);
            *cell = acc;
        }
        Ok(Self {
            offsets,
            peers,
            kinds,
        })
    }

    fn range(&self, id: u32) -> (usize, usize) {
        let i = usize::try_from(id).unwrap_or(usize::MAX);
        let lo = self.offsets.get(i).copied().unwrap_or(0);
        let hi = self.offsets.get(i.saturating_add(1)).copied().unwrap_or(lo);
        (lo as usize, hi as usize)
    }

    fn iter(&self, id: u32) -> impl Iterator<Item = (u32, EdgeKind)> + '_ {
        let (lo, hi) = self.range(id);
        let peers = self.peers.get(lo..hi).unwrap_or(&[]);
        let kinds = self.kinds.get(lo..hi).unwrap_or(&[]);
        peers.iter().copied().zip(kinds.iter().copied())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct GraphStats {
    pub files: usize,
    pub packages: usize,
    pub symbols: usize,
    pub sections: usize,
    pub edges: usize,
    pub skipped: usize,
}

#[derive(Debug, Clone)]
pub struct Graph {
    nodes: Vec<Node>,
    files: usize,
    languages: Vec<Language>,
    digests: Vec<[u8; 32]>,
    out: Csr,
    inc: Csr,
    skipped: usize,
    version: [u8; 32],
}

impl Graph {
    pub(crate) fn assemble(
        nodes: Vec<Node>,
        files: usize,
        languages: Vec<Language>,
        digests: Vec<[u8; 32]>,
        mut edges: Vec<RawEdge>,
        skipped: usize,
    ) -> GraphResult<Self> {
        u32::try_from(nodes.len()).map_err(|_| GraphError::Capacity)?;
        edges.sort_unstable();
        edges.dedup();
        let out = Csr::build(nodes.len(), &edges, false)?;
        edges.sort_unstable_by_key(|&(src, dst, kind)| (dst, src, kind));
        let inc = Csr::build(nodes.len(), &edges, true)?;
        let mut hasher = Sha256::new();
        for (node, digest) in nodes.iter().take(files).zip(&digests) {
            hasher.update((node.name.len() as u64).to_le_bytes());
            hasher.update(node.name.as_bytes());
            hasher.update(digest);
        }
        let version: [u8; 32] = hasher.finalize().into();
        Ok(Self {
            nodes,
            files,
            languages,
            digests,
            out,
            inc,
            skipped,
            version,
        })
    }

    #[must_use]
    pub const fn version(&self) -> &[u8; 32] {
        &self.version
    }

    #[must_use]
    pub fn reference(&self) -> String {
        self.version
            .iter()
            .take(8)
            .fold(String::with_capacity(16), |mut acc, b| {
                acc.extend(
                    [b >> 4, b & 15]
                        .into_iter()
                        .filter_map(|n| char::from_digit(u32::from(n), 16)),
                );
                acc
            })
    }

    #[must_use]
    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }

    #[must_use]
    pub fn edge_count(&self) -> usize {
        self.out.peers.len()
    }

    #[must_use]
    pub fn file_count(&self) -> usize {
        self.files
    }

    #[must_use]
    pub fn node(&self, id: u32) -> Option<&Node> {
        self.nodes.get(usize::try_from(id).ok()?)
    }

    #[must_use]
    pub fn nodes(&self) -> &[Node] {
        &self.nodes
    }

    #[must_use]
    pub fn path(&self, file: u32) -> Option<&str> {
        let i = usize::try_from(file).ok().filter(|i| *i < self.files)?;
        self.nodes.get(i).map(|n| n.name.as_str())
    }

    #[must_use]
    pub fn file_id(&self, path: &str) -> Option<u32> {
        let files = self.nodes.get(..self.files)?;
        files
            .binary_search_by(|n| n.name.as_str().cmp(path))
            .ok()
            .and_then(|i| u32::try_from(i).ok())
    }

    #[must_use]
    pub fn language(&self, file: u32) -> Option<Language> {
        self.languages.get(usize::try_from(file).ok()?).copied()
    }

    #[must_use]
    pub fn digest(&self, file: u32) -> Option<&[u8; 32]> {
        self.digests.get(usize::try_from(file).ok()?)
    }

    pub fn out_edges(&self, id: u32) -> impl Iterator<Item = (u32, EdgeKind)> + '_ {
        self.out.iter(id)
    }

    pub fn in_edges(&self, id: u32) -> impl Iterator<Item = (u32, EdgeKind)> + '_ {
        self.inc.iter(id)
    }

    #[must_use]
    pub fn stats(&self) -> GraphStats {
        let count = |kind: NodeKind| self.nodes.iter().filter(|n| n.kind == kind).count();
        GraphStats {
            files: self.files,
            packages: count(NodeKind::Package),
            symbols: count(NodeKind::Symbol),
            sections: count(NodeKind::Section),
            edges: self.edge_count(),
            skipped: self.skipped,
        }
    }
}
