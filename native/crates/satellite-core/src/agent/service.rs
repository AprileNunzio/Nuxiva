use std::path::Path;

pub const UNIT_PATH: &str = "/etc/systemd/system/nuxiva-satellite.service";
pub const ENROLL_CREDENTIAL: &str = "/etc/nuxiva/satellite-enroll.json";

#[must_use]
pub fn valid_label(value: &str) -> bool {
    (1..=48).contains(&value.chars().count())
        && value
            .chars()
            .all(|c| c.is_alphanumeric() || matches!(c, ' ' | '-' | '_' | '.'))
}

pub fn unit(
    binary: &Path,
    name: &str,
    kind: &str,
    room: &str,
    groups: &[String],
) -> Result<String, &'static str> {
    let binary = binary.to_str().ok_or("binary_path_invalid")?;
    if !binary.starts_with('/')
        || binary
            .chars()
            .any(|c| c.is_whitespace() || c == '%' || c == '"')
    {
        return Err("binary_path_invalid");
    }
    if !valid_label(name) || !valid_label(kind) || !(room.is_empty() || valid_label(room)) {
        return Err("label_invalid");
    }
    if !groups.iter().all(|g| valid_label(g) && !g.contains(' ')) {
        return Err("group_invalid");
    }
    let groups = groups.join(" ");
    Ok(format!(
        "[Unit]
Description=Nuxiva universal satellite
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={binary} run
Environment=\"NUXIVA_NODE_NAME={name}\" \"NUXIVA_NODE_TYPE={kind}\" \"NUXIVA_NODE_ROOM={room}\"
LoadCredential=enroll:{ENROLL_CREDENTIAL}
DynamicUser=yes
StateDirectory=nuxiva-satellite
StateDirectoryMode=0700
SupplementaryGroups={groups}
Restart=always
RestartSec=10
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectControlGroups=yes
ProtectClock=yes
ProtectHostname=yes
RestrictNamespaces=yes
RestrictRealtime=yes
RestrictSUIDSGID=yes
LockPersonality=yes
MemoryDenyWriteExecute=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX AF_NETLINK
SystemCallArchitectures=native
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources
CapabilityBoundingSet=
AmbientCapabilities=
UMask=0077

[Install]
WantedBy=multi-user.target
"
    ))
}

#[must_use]
pub fn existing_groups(group_file: &str, wanted: &[&str]) -> Vec<String> {
    wanted
        .iter()
        .filter(|name| {
            group_file
                .lines()
                .any(|line| line.split(':').next() == Some(**name))
        })
        .map(|name| (*name).to_owned())
        .collect()
}
