use std::sync::{Arc, Mutex};

use serde_json::{Value, json};
use tokio::sync::mpsc;

use super::fake;
use crate::{Link, Message};

#[derive(Debug, Clone, Copy)]
pub enum Control {
    Changed,
    Kill,
}

#[derive(Debug, Clone, Default)]
pub struct Tools(pub Arc<Mutex<Vec<Value>>>);

impl Tools {
    pub fn set(&self, tools: Vec<Value>) {
        if let Ok(mut guard) = self.0.lock() {
            *guard = tools;
        }
    }

    pub fn get(&self) -> Vec<Value> {
        self.0.lock().map(|g| g.clone()).unwrap_or_default()
    }
}

pub fn tool_with(name: &str, schema: Value) -> Value {
    let mut tool = json!({"name": name, "description": "d"});
    if let Value::Object(map) = &mut tool {
        map.insert("inputSchema".into(), schema);
    }
    tool
}

pub fn serve(mut link: Link, tools: Tools) -> mpsc::Sender<Control> {
    let (control_tx, mut control_rx) = mpsc::channel::<Control>(8);
    tokio::spawn(async move {
        loop {
            tokio::select! {
                control = control_rx.recv() => match control {
                    Some(Control::Changed) => {
                        let note = json!({"jsonrpc":"2.0","method":"notifications/tools/list_changed"});
                        let _ = link.tx.send(note.to_string().into_bytes()).await;
                    }
                    Some(Control::Kill) | None => return,
                },
                bytes = link.rx.recv() => {
                    let Some(bytes) = bytes else { return };
                    let Ok(Message::Request(request)) = Message::parse(&bytes, fake::MAX) else {
                        continue;
                    };
                    let result = if request.method == "tools/list" {
                        json!({"tools": tools.get()})
                    } else {
                        fake::answer(&request.method, None).unwrap_or_default()
                    };
                    let _ = link.tx.send(fake::reply(request.id, result)).await;
                }
            }
        }
    });
    control_tx
}
