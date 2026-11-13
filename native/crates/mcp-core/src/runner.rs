use std::future::Future;
use std::hash::BuildHasher;
use std::sync::Arc;
use std::time::{Duration, Instant};

use tokio::sync::watch;
use tokio::task::JoinHandle;

use crate::backoff::{Backoff, Breaker};
use crate::discovery::discover;
use crate::error::{McpError, McpResult};
use crate::health::{Health, ServerStatus};
use crate::normalize::valid_server_id;
use crate::policy::Risk;
use crate::protocol::{Implementation, ToolSpec};
use crate::registry::Registry;
use crate::session::Session;
use crate::settings::Settings;
use crate::transport::Link;

const LIST_CHANGED: &str = "notifications/tools/list_changed";

pub struct ServerHandle {
    pub status: watch::Receiver<ServerStatus>,
    task: JoinHandle<()>,
}

impl std::fmt::Debug for ServerHandle {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ServerHandle").finish_non_exhaustive()
    }
}

impl ServerHandle {
    pub fn shutdown(self) {
        self.task.abort();
    }
}

impl Drop for ServerHandle {
    fn drop(&mut self) {
        self.task.abort();
    }
}

fn millis(value: usize) -> Duration {
    Duration::from_millis(u64::try_from(value).unwrap_or(u64::MAX))
}

fn entropy(counter: u64) -> u64 {
    std::collections::hash_map::RandomState::new().hash_one(counter)
}

pub type Classifier = Arc<dyn Fn(&ToolSpec) -> Risk + Send + Sync>;

struct Context {
    server: String,
    registry: Arc<Registry>,
    settings: Settings,
    client: Implementation,
    classifier: Classifier,
    status: watch::Sender<ServerStatus>,
}

impl Context {
    fn publish(&self, health: Health, attempts: u32, error: Option<McpError>) {
        let tools = self.registry.snapshot().server_tools(&self.server).count();
        let _ = self.status.send(ServerStatus {
            health,
            tools,
            attempts,
            last_error: error,
        });
    }

    async fn serve_session(&self, link: Link) -> McpResult<()> {
        let (session, _, _) = Session::connect(link, self.settings.clone(), &self.client).await?;
        discover(
            &session,
            &self.server,
            &self.registry,
            &self.settings,
            &*self.classifier,
        )
        .await?;
        self.publish(Health::Ready, 0, None);
        let interval = millis(self.settings.refresh_interval_ms);
        let debounce = millis(self.settings.refresh_debounce_ms);
        loop {
            tokio::select! {
                event = session.next_event() => match event {
                    None => return Ok(()),
                    Some(note) if note.method == LIST_CHANGED => {
                        tokio::time::sleep(debounce).await;
                        discover(&session, &self.server, &self.registry, &self.settings, &*self.classifier).await?;
                        self.publish(Health::Ready, 0, None);
                    }
                    Some(_) => {}
                },
                () = tokio::time::sleep(interval) => {
                    if session.is_closed() {
                        return Ok(());
                    }
                    discover(&session, &self.server, &self.registry, &self.settings, &*self.classifier).await?;
                    self.publish(Health::Ready, 0, None);
                }
            }
        }
    }
}

async fn supervise<C, Fut>(context: Context, connect: C)
where
    C: Fn() -> Fut + Send + Sync,
    Fut: Future<Output = McpResult<Link>> + Send,
{
    let mut backoff = Backoff::new(&context.settings);
    let mut breaker = Breaker::new(&context.settings);
    let retire_after = millis(context.settings.stale_retire_ms);
    let mut down_since: Option<Instant> = None;
    let mut counter = 0u64;
    loop {
        context.publish(Health::Connecting, backoff.attempts(), None);
        let outcome = match connect().await {
            Ok(link) => context.serve_session(link).await,
            Err(error) => Err(error),
        };
        let now = Instant::now();
        let started = down_since.get_or_insert(now);
        let _ = context.registry.mark_stale(&context.server);
        let error = outcome.err();
        if error.is_none() {
            backoff.reset();
        }
        breaker.failure(now);
        let tripped = breaker.open(now);
        if now.saturating_duration_since(*started) >= retire_after {
            let _ = context.registry.retire(&context.server);
        }
        let health = if tripped {
            Health::Quarantined
        } else {
            Health::Degraded
        };
        context.publish(health, backoff.attempts(), error);
        counter = counter.saturating_add(1);
        let wait = if tripped {
            millis(context.settings.backoff_max_ms)
        } else {
            backoff.next(entropy(counter))
        };
        tokio::time::sleep(wait).await;
        if context.status.is_closed() {
            return;
        }
    }
}

pub fn spawn_server<C, Fut>(
    server: &str,
    connect: C,
    registry: Arc<Registry>,
    settings: Settings,
    client: Implementation,
    classifier: Classifier,
) -> McpResult<ServerHandle>
where
    C: Fn() -> Fut + Send + Sync + 'static,
    Fut: Future<Output = McpResult<Link>> + Send + 'static,
{
    if !valid_server_id(server) {
        return Err(McpError::InvalidName);
    }
    settings.validate()?;
    let (status, receiver) = watch::channel(ServerStatus::new());
    let context = Context {
        server: server.to_owned(),
        registry,
        settings,
        client,
        classifier,
        status,
    };
    let task = tokio::spawn(supervise(context, connect));
    Ok(ServerHandle {
        status: receiver,
        task,
    })
}
