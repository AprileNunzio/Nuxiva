use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

pub type EClassId = usize;

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum ENode {
    Const(i64),
    Float(u64),
    Var(String),
    Apply(String, Vec<EClassId>),
}

impl ENode {
    #[must_use]
    pub fn from_f64(v: f64) -> Self {
        Self::Float(v.to_bits())
    }

    #[must_use]
    pub fn as_f64(&self) -> Option<f64> {
        match self {
            Self::Float(bits) => Some(f64::from_bits(*bits)),
            Self::Const(c) => Some(*c as f64),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EClass {
    pub id: EClassId,
    pub nodes: BTreeSet<ENode>,
    pub parents: Vec<(ENode, EClassId)>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RewriteRule {
    pub name: String,
    pub source_op: String,
    pub target_op: String,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EGraph {
    parent: Vec<EClassId>,
    classes: BTreeMap<EClassId, EClass>,
    hashcons: BTreeMap<ENode, EClassId>,
    pending_rebuild: bool,
}

impl EGraph {
    #[must_use]
    pub fn new() -> Self {
        Self {
            parent: Vec::new(),
            classes: BTreeMap::new(),
            hashcons: BTreeMap::new(),
            pending_rebuild: false,
        }
    }

    pub fn find(&mut self, mut id: EClassId) -> EClassId {
        let mut path = Vec::new();
        while let Some(&p) = self.parent.get(id) {
            if p == id {
                break;
            }
            path.push(id);
            id = p;
        }
        for node in path {
            if let Some(p) = self.parent.get_mut(node) {
                *p = id;
            }
        }
        id
    }

    pub fn canonicalize(&mut self, node: &ENode) -> ENode {
        match node {
            ENode::Apply(op, children) => {
                let canonical_children: Vec<EClassId> =
                    children.iter().map(|&c| self.find(c)).collect();
                ENode::Apply(op.clone(), canonical_children)
            }
            other => other.clone(),
        }
    }

    pub fn add(&mut self, node: &ENode) -> EClassId {
        let canonical = self.canonicalize(node);
        if let Some(&existing) = self.hashcons.get(&canonical) {
            return self.find(existing);
        }

        let new_id = self.parent.len();
        self.parent.push(new_id);

        let mut class = EClass {
            id: new_id,
            nodes: BTreeSet::new(),
            parents: Vec::new(),
        };
        class.nodes.insert(canonical.clone());
        self.classes.insert(new_id, class);
        self.hashcons.insert(canonical.clone(), new_id);

        if let ENode::Apply(_, children) = &canonical {
            for &child in children {
                let c_root = self.find(child);
                if let Some(c_class) = self.classes.get_mut(&c_root) {
                    c_class.parents.push((canonical.clone(), new_id));
                }
            }
        }

        new_id
    }

    pub fn union(&mut self, id1: EClassId, id2: EClassId) -> EClassId {
        let root1 = self.find(id1);
        let root2 = self.find(id2);
        if root1 == root2 {
            return root1;
        }

        if let Some(p) = self.parent.get_mut(root2) {
            *p = root1;
        }
        if let Some(class2) = self.classes.remove(&root2) {
            if let Some(class1) = self.classes.get_mut(&root1) {
                class1.nodes.extend(class2.nodes);
                class1.parents.extend(class2.parents);
            }
        }
        self.pending_rebuild = true;
        root1
    }

    pub fn rebuild(&mut self) -> usize {
        if !self.pending_rebuild {
            return 0;
        }
        let mut steps = 0usize;
        let class_ids: Vec<EClassId> = self.classes.keys().copied().collect();
        for id in class_ids {
            let root = self.find(id);
            if root != id {
                continue;
            }
            if let Some(mut class) = self.classes.remove(&root) {
                let old_nodes = std::mem::take(&mut class.nodes);
                for node in old_nodes {
                    let canon = self.canonicalize(&node);
                    self.hashcons.insert(canon.clone(), root);
                    class.nodes.insert(canon);
                    steps = steps.saturating_add(1);
                }
                self.classes.insert(root, class);
            }
        }
        self.pending_rebuild = false;
        steps
    }

    #[must_use]
    pub fn class_count(&self) -> usize {
        self.classes.len()
    }

    #[must_use]
    pub fn extract_best_cost(&mut self, id: EClassId) -> Option<ENode> {
        let root = self.find(id);
        self.classes
            .get(&root)
            .and_then(|cls| cls.nodes.iter().next().cloned())
    }
}
