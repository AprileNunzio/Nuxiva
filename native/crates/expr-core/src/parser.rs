use crate::Fault;
use crate::lexer::Tok;

pub const MAX_DEPTH: usize = 100;

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

pub struct Parser {
    toks: Vec<Tok>,
    pos: usize,
    depth: usize,
}

fn syntax(msg: &str) -> Fault {
    Fault::Expr(format!("sintassi non valida: {msg}"))
}

fn denied(what: &str) -> Fault {
    Fault::Expr(format!("costrutto non permesso: {what}"))
}

impl Parser {
    #[must_use]
    pub fn new(toks: Vec<Tok>) -> Self {
        Self {
            toks,
            pos: 0,
            depth: 0,
        }
    }

    fn peek(&self) -> &Tok {
        self.toks.get(self.pos).unwrap_or(&Tok::End)
    }

    fn peek_at(&self, k: usize) -> &Tok {
        self.toks
            .get(self.pos.saturating_add(k))
            .unwrap_or(&Tok::End)
    }

    fn bump(&mut self) -> Tok {
        let t = self.peek().clone();
        self.pos = self.pos.saturating_add(1);
        t
    }

    fn is_op(&self, op: &str) -> bool {
        matches!(self.peek(), Tok::Op(o) if *o == op)
    }

    fn is_word(&self, word: &str) -> bool {
        matches!(self.peek(), Tok::Name(n) if n == word)
    }

    fn eat_op(&mut self, op: &str) -> bool {
        if self.is_op(op) {
            self.pos = self.pos.saturating_add(1);
            true
        } else {
            false
        }
    }

    fn eat_word(&mut self, word: &str) -> bool {
        if self.is_word(word) {
            self.pos = self.pos.saturating_add(1);
            true
        } else {
            false
        }
    }

    fn expect(&mut self, op: &str) -> Result<(), Fault> {
        if self.eat_op(op) {
            Ok(())
        } else {
            Err(syntax(&format!("atteso '{op}'")))
        }
    }

    fn enter(&mut self) -> Result<(), Fault> {
        self.depth = self.depth.saturating_add(1);
        if self.depth > MAX_DEPTH {
            return Err(Fault::Expr("espressione troppo complessa".to_owned()));
        }
        Ok(())
    }

    fn leave(&mut self) {
        self.depth = self.depth.saturating_sub(1);
    }

    pub fn parse(mut self) -> Result<Node, Fault> {
        if matches!(self.peek(), Tok::End) {
            return Err(syntax("espressione vuota"));
        }
        let node = self.test_list()?;
        if !matches!(self.peek(), Tok::End) {
            if self.is_op(":=") || self.is_op("=") {
                return Err(denied("NamedExpr"));
            }
            return Err(syntax("simbolo inatteso"));
        }
        Ok(node)
    }

    fn test_list(&mut self) -> Result<Node, Fault> {
        let first = self.test()?;
        if !self.is_op(",") {
            return Ok(first);
        }
        let mut items = vec![first];
        while self.eat_op(",") {
            if self.ends_list() {
                break;
            }
            items.push(self.test()?);
        }
        Ok(Node::List(items))
    }

    fn ends_list(&self) -> bool {
        matches!(self.peek(), Tok::End) || self.is_op(")") || self.is_op("]") || self.is_op("}")
    }

    fn test(&mut self) -> Result<Node, Fault> {
        self.enter()?;
        if self.is_word("lambda") {
            return Err(denied("Lambda"));
        }
        let body = self.or_test()?;
        let out = if self.eat_word("if") {
            let cond = self.or_test()?;
            if !self.eat_word("else") {
                return Err(syntax("atteso 'else'"));
            }
            let other = self.test()?;
            Node::IfExp(Box::new(cond), Box::new(body), Box::new(other))
        } else {
            body
        };
        if self.is_word("for") {
            return Err(denied("comprehension"));
        }
        self.leave();
        Ok(out)
    }

    fn or_test(&mut self) -> Result<Node, Fault> {
        let first = self.and_test()?;
        if !self.is_word("or") {
            return Ok(first);
        }
        let mut items = vec![first];
        while self.eat_word("or") {
            items.push(self.and_test()?);
        }
        Ok(Node::Or(items))
    }

    fn and_test(&mut self) -> Result<Node, Fault> {
        let first = self.not_test()?;
        if !self.is_word("and") {
            return Ok(first);
        }
        let mut items = vec![first];
        while self.eat_word("and") {
            items.push(self.not_test()?);
        }
        Ok(Node::And(items))
    }

    fn not_test(&mut self) -> Result<Node, Fault> {
        if self.eat_word("not") {
            self.enter()?;
            let inner = self.not_test()?;
            self.leave();
            return Ok(Node::Unary(Unary::Not, Box::new(inner)));
        }
        self.comparison()
    }

    fn comp_op(&mut self) -> Option<Cmp> {
        let op = match self.peek() {
            Tok::Op("==") => Cmp::Eq,
            Tok::Op("!=") => Cmp::NotEq,
            Tok::Op("<") => Cmp::Lt,
            Tok::Op("<=") => Cmp::LtE,
            Tok::Op(">") => Cmp::Gt,
            Tok::Op(">=") => Cmp::GtE,
            Tok::Name(n) if n == "in" => Cmp::In,
            Tok::Name(n) if n == "not" && matches!(self.peek_at(1), Tok::Name(m) if m == "in") => {
                self.pos = self.pos.saturating_add(2);
                return Some(Cmp::NotIn);
            }
            Tok::Name(n) if n == "is" => {
                if matches!(self.peek_at(1), Tok::Name(m) if m == "not") {
                    self.pos = self.pos.saturating_add(2);
                    return Some(Cmp::IsNot);
                }
                Cmp::Is
            }
            _ => return None,
        };
        self.pos = self.pos.saturating_add(1);
        Some(op)
    }

    fn comparison(&mut self) -> Result<Node, Fault> {
        let left = self.bit_or()?;
        let mut rest = Vec::new();
        while let Some(op) = self.comp_op() {
            rest.push((op, self.bit_or()?));
        }
        if rest.is_empty() {
            Ok(left)
        } else {
            Ok(Node::Compare(Box::new(left), rest))
        }
    }

    fn bit_or(&mut self) -> Result<Node, Fault> {
        let mut left = self.arith()?;
        while ["|", "^", "&", "<<", ">>"].iter().any(|op| self.is_op(op)) {
            self.bump();
            let right = self.arith()?;
            left = Node::Binary(Bin::Other, Box::new(left), Box::new(right));
        }
        Ok(left)
    }

    fn arith(&mut self) -> Result<Node, Fault> {
        let mut left = self.term()?;
        loop {
            let op = if self.eat_op("+") {
                Bin::Add
            } else if self.eat_op("-") {
                Bin::Sub
            } else {
                return Ok(left);
            };
            let right = self.term()?;
            left = Node::Binary(op, Box::new(left), Box::new(right));
        }
    }

    fn term(&mut self) -> Result<Node, Fault> {
        let mut left = self.factor()?;
        loop {
            let op = if self.eat_op("*") {
                Bin::Mul
            } else if self.eat_op("//") {
                Bin::FloorDiv
            } else if self.eat_op("/") {
                Bin::Div
            } else if self.eat_op("%") {
                Bin::Mod
            } else if self.eat_op("@") {
                Bin::Other
            } else {
                return Ok(left);
            };
            let right = self.factor()?;
            left = Node::Binary(op, Box::new(left), Box::new(right));
        }
    }

    fn factor(&mut self) -> Result<Node, Fault> {
        let op = if self.eat_op("-") {
            Unary::Neg
        } else if self.eat_op("+") {
            Unary::Pos
        } else if self.eat_op("~") {
            Unary::Invert
        } else {
            return self.power();
        };
        self.enter()?;
        let inner = self.factor()?;
        self.leave();
        Ok(Node::Unary(op, Box::new(inner)))
    }

    fn power(&mut self) -> Result<Node, Fault> {
        let base = self.atom_expr()?;
        if self.eat_op("**") {
            self.enter()?;
            let exp = self.factor()?;
            self.leave();
            return Ok(Node::Binary(Bin::Pow, Box::new(base), Box::new(exp)));
        }
        Ok(base)
    }

    fn atom_expr(&mut self) -> Result<Node, Fault> {
        let mut node = self.atom()?;
        loop {
            if self.eat_op("(") {
                let args = self.call_args()?;
                node = match node {
                    Node::Name(name) => Node::Call(name, args),
                    _ => Node::Denied("Call"),
                };
            } else if self.eat_op("[") {
                let index = self.subscript()?;
                self.expect("]")?;
                node = Node::Index(Box::new(node), Box::new(index));
            } else if self.eat_op(".") {
                match self.bump() {
                    Tok::Name(attr) => node = Node::Attr(Box::new(node), attr),
                    _ => return Err(syntax("atteso un nome")),
                }
            } else {
                return Ok(node);
            }
        }
    }

    fn subscript(&mut self) -> Result<Node, Fault> {
        if self.is_op(":") {
            return Err(denied("Slice"));
        }
        let first = self.test()?;
        if self.is_op(":") {
            return Err(denied("Slice"));
        }
        if !self.is_op(",") {
            return Ok(first);
        }
        let mut items = vec![first];
        while self.eat_op(",") {
            if self.is_op("]") {
                break;
            }
            items.push(self.test()?);
        }
        Ok(Node::List(items))
    }

    fn call_args(&mut self) -> Result<Vec<Node>, Fault> {
        let mut args = Vec::new();
        while !self.eat_op(")") {
            if self.is_op("*") || self.is_op("**") {
                return Err(denied("Starred"));
            }
            if matches!(self.peek(), Tok::Name(_)) && matches!(self.peek_at(1), Tok::Op("=")) {
                return Err(denied("keyword"));
            }
            args.push(self.test()?);
            if !self.eat_op(",") {
                self.expect(")")?;
                break;
            }
        }
        Ok(args)
    }

    fn sequence(&mut self, close: &str) -> Result<Vec<Node>, Fault> {
        let mut items = Vec::new();
        while !self.eat_op(close) {
            if self.is_op("*") {
                return Err(denied("Starred"));
            }
            items.push(self.test()?);
            if !self.eat_op(",") {
                self.expect(close)?;
                break;
            }
        }
        Ok(items)
    }

    fn atom(&mut self) -> Result<Node, Fault> {
        self.enter()?;
        let node = match self.bump() {
            Tok::Int(v) => Node::Int(v),
            Tok::Float(v) => Node::Float(v),
            Tok::Str(mut s) => {
                while let Tok::Str(more) = self.peek().clone() {
                    s.push_str(&more);
                    self.pos = self.pos.saturating_add(1);
                }
                Node::Str(s)
            }
            Tok::Name(n) => match n.as_str() {
                "True" => Node::Bool(true),
                "False" => Node::Bool(false),
                "None" => Node::Null,
                "and" | "or" | "not" | "in" | "is" | "if" | "else" | "for" | "lambda"
                | "import" | "def" | "class" | "return" | "yield" | "await" | "async" | "del"
                | "pass" | "while" | "with" | "from" | "global" | "nonlocal" | "raise" | "try"
                | "except" | "finally" | "assert" | "break" | "continue" | "elif" | "as" => {
                    if n == "yield" || n == "await" {
                        return Err(denied(if n == "yield" { "Yield" } else { "Await" }));
                    }
                    return Err(syntax("parola riservata"));
                }
                _ => Node::Name(n),
            },
            Tok::Op("(") => {
                if self.eat_op(")") {
                    Node::List(Vec::new())
                } else {
                    let inner = self.test()?;
                    if self.is_op(",") {
                        let mut items = vec![inner];
                        while self.eat_op(",") {
                            if self.is_op(")") {
                                break;
                            }
                            items.push(self.test()?);
                        }
                        self.expect(")")?;
                        Node::List(items)
                    } else {
                        self.expect(")")?;
                        inner
                    }
                }
            }
            Tok::Op("[") => Node::List(self.sequence("]")?),
            Tok::Op("{") => self.braces()?,
            Tok::Op(".") if self.is_op(".") => {
                return Err(denied("Ellipsis"));
            }
            _ => return Err(syntax("simbolo inatteso")),
        };
        self.leave();
        Ok(node)
    }

    fn braces(&mut self) -> Result<Node, Fault> {
        if self.eat_op("}") {
            return Ok(Node::Dict(Vec::new()));
        }
        if self.is_op("**") {
            return Err(denied("Dict"));
        }
        let first = self.test()?;
        if !self.eat_op(":") {
            return Err(denied("Set"));
        }
        let mut pairs = vec![(first, self.test()?)];
        while self.eat_op(",") {
            if self.eat_op("}") {
                return Ok(Node::Dict(pairs));
            }
            let key = self.test()?;
            self.expect(":")?;
            pairs.push((key, self.test()?));
        }
        self.expect("}")?;
        Ok(Node::Dict(pairs))
    }
}
