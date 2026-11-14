use std::os::unix::process::CommandExt;
use std::process::Command;

use crate::proc::run_bounded;
use crate::session::Session;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Notice {
    Saved,
    Queued,
    Blocked,
    Failed,
}

#[must_use]
pub fn text(lang: &str, notice: Notice) -> (&'static str, &'static str) {
    match (lang, notice) {
        ("en", Notice::Saved) => ("Screenshot", "Saved to the shared folder"),
        ("en", Notice::Queued) => ("Screenshot", "Share unreachable: will retry"),
        ("en", Notice::Blocked) => ("Screenshot", "Not captured: blocked by privacy policy"),
        ("en", Notice::Failed) => ("Screenshot", "Capture failed"),
        ("fr", Notice::Saved) => ("Capture d'écran", "Enregistrée dans le dossier partagé"),
        ("fr", Notice::Queued) => (
            "Capture d'écran",
            "Partage injoignable : nouvelle tentative",
        ),
        ("fr", Notice::Blocked) => (
            "Capture d'écran",
            "Non capturée : bloquée par la confidentialité",
        ),
        ("fr", Notice::Failed) => ("Capture d'écran", "Échec de la capture"),
        ("es", Notice::Saved) => ("Captura de pantalla", "Guardada en la carpeta compartida"),
        ("es", Notice::Queued) => ("Captura de pantalla", "Recurso inaccesible: se reintentará"),
        ("es", Notice::Blocked) => (
            "Captura de pantalla",
            "No capturada: bloqueada por privacidad",
        ),
        ("es", Notice::Failed) => ("Captura de pantalla", "Captura fallida"),
        (_, Notice::Saved) => ("Screenshot", "Salvato nella cartella condivisa"),
        (_, Notice::Queued) => ("Screenshot", "Condivisione non raggiungibile: riprovo"),
        (_, Notice::Blocked) => ("Screenshot", "Non catturato: bloccato dalla privacy"),
        (_, Notice::Failed) => ("Screenshot", "Cattura non riuscita"),
    }
}

pub fn show(session: &Session, lang: &str, notice: Notice) {
    let (title, body) = text(lang, notice);
    let runtime = format!("/run/user/{}", session.uid);
    let mut command = Command::new("notify-send");
    command
        .args(["--app-name=Nuxiva", "--expire-time=4000", title, body])
        .env_clear()
        .env("PATH", "/usr/local/bin:/usr/bin:/bin")
        .env("XDG_RUNTIME_DIR", &runtime)
        .env(
            "DBUS_SESSION_BUS_ADDRESS",
            format!("unix:path={runtime}/bus"),
        )
        .uid(session.uid)
        .gid(session.gid);
    let _ = run_bounded(&mut command, std::time::Duration::from_secs(3), 4096);
}
