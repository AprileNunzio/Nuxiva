use crate::{Capability, Matrix, Request, Role, Strength, Verdict, decide};

pub type Digest = [u8; 32];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SyncAction {
    Unchanged,
    Download,
    Upload,
    Conflict,
    Denied,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Snapshot {
    pub common: Option<Digest>,
    pub windows: Option<Digest>,
    pub share: Option<Digest>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Scope<'a> {
    pub tenant: &'a str,
    pub account: &'a str,
    pub share: &'a str,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ShareAccess<'a> {
    pub grant_scope: Scope<'a>,
    pub role: Role,
    pub strength: Strength,
    pub owns_share: bool,
    pub read_grant: bool,
    pub write_grant: bool,
}

impl ShareAccess<'_> {
    fn allows(self, matrix: &Matrix, capability: &str) -> bool {
        Capability::parse(capability).is_ok_and(|capability| {
            decide(
                &Request {
                    capabilities: &[capability],
                    role: self.role,
                    strength: self.strength,
                    local: Some(false),
                    own: self.owns_share,
                },
                matrix,
            ) == Verdict::Allow
        })
    }
}

#[must_use]
pub fn reconcile(
    snapshot: Snapshot,
    scope: Scope<'_>,
    access: ShareAccess<'_>,
    matrix: &Matrix,
) -> SyncAction {
    if scope != access.grant_scope
        || scope.tenant.is_empty()
        || scope.account.is_empty()
        || scope.share.is_empty()
        || !access.read_grant
        || !access.allows(matrix, "files.share.read")
    {
        return SyncAction::Denied;
    }
    if snapshot.windows == snapshot.share {
        return SyncAction::Unchanged;
    }
    if snapshot.windows == snapshot.common && snapshot.share.is_some() {
        return SyncAction::Download;
    }
    if snapshot.share == snapshot.common && snapshot.windows.is_some() {
        return if access.write_grant && access.allows(matrix, "files.share.write") {
            SyncAction::Upload
        } else {
            SyncAction::Denied
        };
    }
    SyncAction::Conflict
}

#[cfg(test)]
mod tests {
    use super::{Matrix, Role, Scope, ShareAccess, Snapshot, Strength, SyncAction, reconcile};
    use crate::AccessError;

    const SCOPE: Scope<'_> = Scope {
        tenant: "home",
        account: "alice",
        share: "documents",
    };

    #[test]
    fn rbac_and_share_grants_are_both_required() -> Result<(), AccessError> {
        let matrix = Matrix::builtin()?;
        let snapshot = Snapshot {
            common: None,
            windows: Some([1; 32]),
            share: None,
        };
        let mut access = ShareAccess {
            grant_scope: SCOPE,
            role: Role::Owner,
            strength: Strength::Strong,
            owns_share: true,
            read_grant: true,
            write_grant: false,
        };
        assert_eq!(
            reconcile(snapshot, SCOPE, access, &matrix),
            SyncAction::Denied
        );
        access.write_grant = true;
        assert_eq!(
            reconcile(snapshot, SCOPE, access, &matrix),
            SyncAction::Upload
        );
        let other = Scope {
            account: "bob",
            ..SCOPE
        };
        assert_eq!(
            reconcile(snapshot, other, access, &matrix),
            SyncAction::Denied
        );
        access.role = Role::Guest;
        assert_eq!(
            reconcile(snapshot, SCOPE, access, &matrix),
            SyncAction::Denied
        );
        Ok(())
    }

    #[test]
    fn deletion_and_parallel_changes_never_overwrite_either_side() -> Result<(), AccessError> {
        let matrix = Matrix::builtin()?;
        let access = ShareAccess {
            grant_scope: SCOPE,
            role: Role::Owner,
            strength: Strength::Strong,
            owns_share: true,
            read_grant: true,
            write_grant: true,
        };
        let mut snapshot = Snapshot {
            common: Some([1; 32]),
            windows: Some([2; 32]),
            share: Some([3; 32]),
        };
        assert_eq!(
            reconcile(snapshot, SCOPE, access, &matrix),
            SyncAction::Conflict
        );
        snapshot.windows = snapshot.common;
        assert_eq!(
            reconcile(snapshot, SCOPE, access, &matrix),
            SyncAction::Download
        );
        snapshot.share = None;
        assert_eq!(
            reconcile(snapshot, SCOPE, access, &matrix),
            SyncAction::Conflict
        );
        Ok(())
    }
}
