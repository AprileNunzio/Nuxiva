use tokio::sync::mpsc;

pub const QUEUE: usize = 64;

pub struct Link {
    pub tx: mpsc::Sender<Vec<u8>>,
    pub rx: mpsc::Receiver<Vec<u8>>,
    pub guard: Option<Box<dyn Send + Sync>>,
}

impl std::fmt::Debug for Link {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Link")
            .field("guarded", &self.guard.is_some())
            .finish_non_exhaustive()
    }
}

impl Link {
    #[must_use]
    pub fn new(tx: mpsc::Sender<Vec<u8>>, rx: mpsc::Receiver<Vec<u8>>) -> Self {
        Self {
            tx,
            rx,
            guard: None,
        }
    }
}

#[must_use]
pub fn pair() -> (Link, Link) {
    let (a_tx, a_rx) = mpsc::channel(QUEUE);
    let (b_tx, b_rx) = mpsc::channel(QUEUE);
    (Link::new(a_tx, b_rx), Link::new(b_tx, a_rx))
}
