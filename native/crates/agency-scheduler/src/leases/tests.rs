use super::{JobLease, LeaseError, Owner};

fn owner(account: &str) -> Owner {
    Owner {
        tenant: "tenant-a".into(),
        account: account.into(),
    }
}

#[test]
fn expired_assignment_can_move_to_another_node() -> Result<(), LeaseError> {
    let owner = owner("alice");
    let mut job = JobLease::new(owner.clone());
    let first = job.assign(&owner, "pc-a".into(), 100, 20)?;
    assert_eq!(
        job.assign(&owner, "pc-b".into(), 119, 20),
        Err(LeaseError::Active)
    );
    let second = job.assign(&owner, "pc-b".into(), 120, 20)?;
    assert!(second.generation > first.generation);
    assert_eq!(
        job.complete(&owner, "pc-a", first.generation, 121),
        Err(LeaseError::Stale)
    );
    job.complete(&owner, "pc-b", second.generation, 121)?;
    assert_eq!(
        job.complete(&owner, "pc-b", second.generation, 122),
        Err(LeaseError::Completed)
    );
    Ok(())
}

#[test]
fn worker_and_account_cannot_be_swapped() -> Result<(), LeaseError> {
    let alice = owner("alice");
    let bob = owner("bob");
    let mut job = JobLease::new(alice.clone());
    assert_eq!(
        job.assign(&bob, "pc-b".into(), 0, 10),
        Err(LeaseError::WrongOwner)
    );
    let lease = job.assign(&alice, "pc-a".into(), 0, 10)?;
    assert_eq!(
        job.complete(&bob, "pc-a", lease.generation, 1),
        Err(LeaseError::WrongOwner)
    );
    assert_eq!(
        job.complete(&alice, "pc-b", lease.generation, 1),
        Err(LeaseError::Stale)
    );
    Ok(())
}
