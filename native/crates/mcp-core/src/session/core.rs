use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicI64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use serde_json::{Map, Value};
use tokio::sync::{mpsc, oneshot};
use tokio::task::JoinHandle;

use crate::error::{McpError, McpResult};
use crate::protocol::{
    ErrorObject, Id, Message, Notification, Outcome, Response, cancelled_notification,
};
use crate::settings::Settings;
use crate::transport::Link;

type Pending = Arc<Mutex<HashMap<Id, oneshot::Sender<Outcome>>>>;

pub struct Session {
    out: mpsc::Sender<Vec<u8>>,
    pending: Pending,
    next: AtomicI64,
    closed: Arc<AtomicBool>,
    pub(super) settings: Settings,
    pub(super) events: tokio::sync::Mutex<mpsc::Receiver<Notification>>,
    reader: JoinHandle<()>,
    _guard: Option<Box<dyn Send + Sync>>,
}

impl std::fmt::Debug for Session {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Session")
            .field("closed", &self.is_closed())
            .finish_non_exhaustive()
    }
}

impl Drop for Session {
    fn drop(&mut self) {
        self.reader.abort();
    }
}

fn locked(
    pending: &Pending,
) -> McpResult<std::sync::MutexGuard<'_, HashMap<Id, oneshot::Sender<Outcome>>>> {
    pending.lock().map_err(|_| McpError::Closed)
}

async fn answer(out: &mpsc::Sender<Vec<u8>>, id: Id, outcome: Outcome) {
    let message = Message::Response(Response { id, outcome });
    if let Ok(bytes) = message.to_vec() {
        let _ = out.send(bytes).await;
    }
}

async fn serve(out: &mpsc::Sender<Vec<u8>>, request: crate::protocol::Request) {
    let outcome = if request.method == "ping" {
        Outcome::Result(Value::Object(Map::new()))
    } else {
        Outcome::Error(ErrorObject {
            code: -32601,
            message: "method not found".into(),
            data: None,
        })
    };
    answer(out, request.id, outcome).await;
}

async fn read_loop(
    mut link_rx: mpsc::Receiver<Vec<u8>>,
    out: mpsc::Sender<Vec<u8>>,
    pending: Pending,
    events: mpsc::Sender<Notification>,
    closed: Arc<AtomicBool>,
    max_bytes: usize,
) {
    while let Some(bytes) = link_rx.recv().await {
        match Message::parse(&bytes, max_bytes) {
            Ok(Message::Response(response)) => {
                let waiter = locked(&pending)
                    .ok()
                    .and_then(|mut map| map.remove(&response.id));
                if let Some(waiter) = waiter {
                    let _ = waiter.send(response.outcome);
                }
            }
            Ok(Message::Notification(notification)) => {
                let _ = events.try_send(notification);
            }
            Ok(Message::Request(request)) => serve(&out, request).await,
            Err(_) => {}
        }
    }
    closed.store(true, Ordering::Release);
    if let Ok(mut map) = locked(&pending) {
        map.clear();
    }
}

impl Session {
    pub(super) fn open(link: Link, settings: Settings) -> Self {
        let Link { tx, rx, guard } = link;
        let pending: Pending = Arc::new(Mutex::new(HashMap::new()));
        let closed = Arc::new(AtomicBool::new(false));
        let (event_tx, event_rx) = mpsc::channel(settings.event_queue);
        let reader = tokio::spawn(read_loop(
            rx,
            tx.clone(),
            Arc::clone(&pending),
            event_tx,
            Arc::clone(&closed),
            settings.max_message_bytes,
        ));
        Self {
            out: tx,
            pending,
            next: AtomicI64::new(1),
            closed,
            settings,
            events: tokio::sync::Mutex::new(event_rx),
            reader,
            _guard: guard,
        }
    }

    #[must_use]
    pub fn is_closed(&self) -> bool {
        self.closed.load(Ordering::Acquire) || self.out.is_closed()
    }

    pub(super) fn timeout(&self) -> Duration {
        Duration::from_millis(u64::try_from(self.settings.request_timeout_ms).unwrap_or(u64::MAX))
    }

    pub async fn notify(&self, message: Message) -> McpResult<()> {
        let bytes = message.to_vec()?;
        self.out.send(bytes).await.map_err(|_| McpError::Closed)
    }

    pub async fn next_event(&self) -> Option<Notification> {
        self.events.lock().await.recv().await
    }

    pub async fn call_outcome(
        &self,
        method: &str,
        params: Option<Map<String, Value>>,
    ) -> McpResult<Outcome> {
        if self.is_closed() {
            return Err(McpError::Closed);
        }
        let id = Id::Number(self.next.fetch_add(1, Ordering::Relaxed));
        let (tx, rx) = oneshot::channel();
        {
            let mut map = locked(&self.pending)?;
            if map.len() >= self.settings.max_in_flight {
                return Err(McpError::Busy);
            }
            map.insert(id.clone(), tx);
        }
        let message = Message::Request(crate::protocol::Request {
            id: id.clone(),
            method: method.to_owned(),
            params,
        });
        if let Err(error) = self.notify(message).await {
            locked(&self.pending)?.remove(&id);
            return Err(error);
        }
        match tokio::time::timeout(self.timeout(), rx).await {
            Ok(Ok(outcome)) => Ok(outcome),
            Ok(Err(_)) => Err(McpError::Closed),
            Err(_) => {
                locked(&self.pending)?.remove(&id);
                let _ = self.notify(cancelled_notification(&id, "timeout")).await;
                Err(McpError::Timeout)
            }
        }
    }

    pub async fn call(&self, method: &str, params: Option<Map<String, Value>>) -> McpResult<Value> {
        match self.call_outcome(method, params).await? {
            Outcome::Result(value) => Ok(value),
            Outcome::Error(_) => Err(McpError::Remote),
        }
    }
}
