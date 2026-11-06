#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Bin {
    Add,
    Sub,
    Mul,
    Div,
    FloorDiv,
    Mod,
    Pow,
    Other,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Cmp {
    Eq,
    NotEq,
    Lt,
    LtE,
    Gt,
    GtE,
    In,
    NotIn,
    Is,
    IsNot,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Unary {
    Not,
    Neg,
    Pos,
    Invert,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Node {
    Int(i128),
    Float(f64),
    Str(String),
    Bool(bool),
    Null,
    Name(String),
    And(Vec<Node>),
    Or(Vec<Node>),
    Binary(Bin, Box<Node>, Box<Node>),
    Unary(Unary, Box<Node>),
    Compare(Box<Node>, Vec<(Cmp, Node)>),
    IfExp(Box<Node>, Box<Node>, Box<Node>),
    Attr(Box<Node>, String),
    Index(Box<Node>, Box<Node>),
    List(Vec<Node>),
    Dict(Vec<(Node, Node)>),
    Call(String, Vec<Node>),
    Denied(&'static str),
}
