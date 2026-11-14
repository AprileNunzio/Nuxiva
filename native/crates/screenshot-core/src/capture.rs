use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::Command;

use crate::error::{Error, Result};
use crate::fb;
use crate::proc::{CAPTURE_TIMEOUT, MAX_OUTPUT, run_bounded};
use crate::session::{Kind, Session, valid_display, wayland_socket, xauthority};

const BIN_DIRS: &[&str] = &["/usr/bin", "/usr/local/bin", "/bin"];
const PATH_VALUE: &str = "/usr/local/bin:/usr/bin:/bin";
const PNG_MAGIC: &[u8] = &[0x89, b'P', b'N', b'G', 0x0d, 0x0a, 0x1a, 0x0a];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tool {
    Grim,
    Maim,
    Import,
}

impl Tool {
    #[must_use]
    pub const fn binary(self) -> &'static str {
        match self {
            Self::Grim => "grim",
            Self::Maim => "maim",
            Self::Import => "import",
        }
    }

    #[must_use]
    pub const fn args(self) -> &'static [&'static str] {
        match self {
            Self::Grim => &["-t", "png", "-"],
            Self::Maim => &["--format", "png", "--hidecursor"],
            Self::Import => &["-window", "root", "png:-"],
        }
    }
}

#[must_use]
pub fn tools_for(kind: Kind) -> &'static [Tool] {
    match kind {
        Kind::Wayland => &[Tool::Grim],
        Kind::X11 => &[Tool::Maim, Tool::Import],
        Kind::Tty | Kind::Unknown => &[],
    }
}

#[must_use]
pub fn locate(tool: Tool, dirs: &[&str]) -> Option<PathBuf> {
    dirs.iter()
        .map(|d| Path::new(d).join(tool.binary()))
        .find(|p| p.is_file())
}

fn session_command(path: &Path, tool: Tool, session: &Session) -> Option<Command> {
    let runtime = PathBuf::from(format!("/run/user/{}", session.uid));
    let mut command = Command::new(path);
    command
        .args(tool.args())
        .env_clear()
        .env("PATH", PATH_VALUE)
        .env("XDG_RUNTIME_DIR", &runtime)
        .env("HOME", &session.home)
        .uid(session.uid)
        .gid(session.gid);
    match session.kind {
        Kind::Wayland => {
            command.env("WAYLAND_DISPLAY", wayland_socket(&runtime)?);
        }
        Kind::X11 => {
            let display = session.display.as_deref().filter(|d| valid_display(d))?;
            command.env("DISPLAY", display);
            if let Some(auth) = xauthority(session) {
                command.env("XAUTHORITY", auth);
            }
        }
        Kind::Tty | Kind::Unknown => return None,
    }
    Some(command)
}

fn valid_png(bytes: &[u8]) -> bool {
    bytes.starts_with(PNG_MAGIC)
}

pub fn from_session(session: &Session) -> Result<Vec<u8>> {
    for tool in tools_for(session.kind) {
        let Some(path) = locate(*tool, BIN_DIRS) else {
            continue;
        };
        let Some(mut command) = session_command(&path, *tool, session) else {
            continue;
        };
        if let Some(bytes) = run_bounded(&mut command, CAPTURE_TIMEOUT, MAX_OUTPUT) {
            if valid_png(&bytes) {
                return Ok(bytes);
            }
        }
    }
    Err(Error::Capture("no_backend"))
}

pub fn from_framebuffer() -> Result<Vec<u8>> {
    fb::capture(Path::new("/sys/class/graphics"), Path::new("/dev"), 0)?.encode()
}

pub fn grab(session: Option<&Session>) -> Result<Vec<u8>> {
    if let Some(session) = session {
        if let Ok(bytes) = from_session(session) {
            return Ok(bytes);
        }
    }
    from_framebuffer()
}
