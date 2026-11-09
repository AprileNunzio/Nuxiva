use thiserror::Error;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Owner {
    pub tenant: String,
    pub account: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Lease {
    pub worker: String,
    pub generation: u64,
    pub expires_at: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
pub enum LeaseError {
    #[error("job belongs to a different account")]
    WrongOwner,
    #[error("job already has an active lease")]
    Active,
    #[error("job has already completed")]
    Completed,
    #[error("invalid lease duration or worker")]
    Invalid,
    #[error("lease expired or was replaced")]
    Stale,
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum State {
    Pending,
    Assigned(Lease),
    Completed,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JobLease {
    owner: Owner,
    generation: u64,
    state: State,
}

impl JobLease {
    #[must_use]
    pub const fn new(owner: Owner) -> Self {
        Self {
            owner,
            generation: 0,
            state: State::Pending,
        }
    }

    pub fn assign(
        &mut self,
        owner: &Owner,
        worker: String,
        now: u64,
        duration: u64,
    ) -> Result<Lease, LeaseError> {
        self.check_owner(owner)?;
        match &self.state {
            State::Assigned(lease) if now < lease.expires_at => return Err(LeaseError::Active),
            State::Completed => return Err(LeaseError::Completed),
            _ => {}
        }
        if worker.is_empty() || duration == 0 {
            return Err(LeaseError::Invalid);
        }
        let expires_at = now.checked_add(duration).ok_or(LeaseError::Invalid)?;
        let generation = self.generation.checked_add(1).ok_or(LeaseError::Invalid)?;
        let lease = Lease {
            worker,
            generation,
            expires_at,
        };
        self.generation = generation;
        self.state = State::Assigned(lease.clone());
        Ok(lease)
    }

    pub fn complete(
        &mut self,
        owner: &Owner,
        worker: &str,
        generation: u64,
        now: u64,
    ) -> Result<(), LeaseError> {
        self.check_owner(owner)?;
        match &self.state {
            State::Assigned(lease)
                if lease.worker == worker
                    && lease.generation == generation
                    && now < lease.expires_at =>
            {
                self.state = State::Completed;
                Ok(())
            }
            State::Completed => Err(LeaseError::Completed),
            _ => Err(LeaseError::Stale),
        }
    }

    fn check_owner(&self, owner: &Owner) -> Result<(), LeaseError> {
        if owner == &self.owner {
            Ok(())
        } else {
            Err(LeaseError::WrongOwner)
        }
    }
}

#[cfg(test)]
mod tests;
