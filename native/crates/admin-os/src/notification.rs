use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum NotificationLevel {
    Info,
    Warning,
    Error,
    Critical,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NotificationItem {
    pub id: u64,
    pub level: NotificationLevel,
    pub title: String,
    pub message: String,
    pub timestamp_secs: u64,
}

#[derive(Debug, Clone)]
pub struct NotificationManager {
    max_items: usize,
    cooldown_secs: u64,
    next_id: u64,
    items: Vec<NotificationItem>,
}

impl Default for NotificationManager {
    fn default() -> Self {
        Self {
            max_items: 128,
            cooldown_secs: 30,
            next_id: 1,
            items: Vec::new(),
        }
    }
}

impl NotificationManager {
    #[must_use]
    pub const fn new(max_items: usize, cooldown_secs: u64) -> Self {
        Self {
            max_items,
            cooldown_secs,
            next_id: 1,
            items: Vec::new(),
        }
    }

    pub fn notify(
        &mut self,
        level: NotificationLevel,
        title: &str,
        message: &str,
        timestamp_secs: u64,
        force: bool,
    ) -> Option<NotificationItem> {
        let clean_title = title.trim();
        let clean_msg = message.trim();

        if clean_title.is_empty() {
            return None;
        }

        if !force {
            let is_duplicate = self.items.iter().rev().take(10).any(|n| {
                n.level == level
                    && n.title == clean_title
                    && n.message == clean_msg
                    && timestamp_secs.saturating_sub(n.timestamp_secs) < self.cooldown_secs
            });

            if is_duplicate {
                return None;
            }
        }

        if self.items.len() >= self.max_items {
            self.items.remove(0);
        }

        let item = NotificationItem {
            id: self.next_id,
            level,
            title: clean_title.to_string(),
            message: clean_msg.to_string(),
            timestamp_secs,
        };

        self.next_id = self.next_id.saturating_add(1);
        self.items.push(item.clone());
        Some(item)
    }

    pub fn clear(&mut self) {
        self.items.clear();
    }

    #[must_use]
    pub fn list(&self) -> &[NotificationItem] {
        &self.items
    }

    #[must_use]
    pub fn count(&self) -> usize {
        self.items.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn notifications_and_cooldown_deduplication() {
        let mut mgr = NotificationManager::default();
        let n1 = mgr.notify(
            NotificationLevel::Warning,
            "Low Disk",
            "Disk space low",
            100,
            false,
        );
        assert!(n1.is_some());

        let n2 = mgr.notify(
            NotificationLevel::Warning,
            "Low Disk",
            "Disk space low",
            110,
            false,
        );
        assert!(n2.is_none());

        let n3 = mgr.notify(
            NotificationLevel::Warning,
            "Low Disk",
            "Disk space low",
            110,
            true,
        );
        assert!(n3.is_some());

        assert_eq!(mgr.count(), 2);
    }

    #[test]
    fn capacity_ring_buffer() {
        let mut mgr = NotificationManager::new(2, 0);
        assert!(
            mgr.notify(NotificationLevel::Info, "A", "1", 1, true)
                .is_some()
        );
        assert!(
            mgr.notify(NotificationLevel::Info, "B", "2", 2, true)
                .is_some()
        );
        assert!(
            mgr.notify(NotificationLevel::Info, "C", "3", 3, true)
                .is_some()
        );

        assert_eq!(mgr.count(), 2);
        let items = mgr.list();
        assert_eq!(items.first().map(|n| n.title.as_str()), Some("B"));
        assert_eq!(items.get(1).map(|n| n.title.as_str()), Some("C"));
    }
}
