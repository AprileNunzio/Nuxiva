use std::path::PathBuf;

use crate::{Implementation, McpError, McpResult, Session, Settings, StdioSpec, spawn_stdio};

const SERVER: &str = r"
import sys, json
for line in sys.stdin:
    m = json.loads(line)
    if 'id' not in m:
        continue
    if m['method'] == 'initialize':
        r = {'protocolVersion': '2025-06-18', 'capabilities': {}, 'serverInfo': {'name': 's', 'version': '1'}}
    elif m['method'] == 'tools/list':
        r = {'tools': [{'name': 'echo', 'inputSchema': {'type': 'object'}}]}
    else:
        r = {}
    sys.stdout.write(json.dumps({'jsonrpc': '2.0', 'id': m['id'], 'result': r}) + '\n')
    sys.stdout.flush()
";

fn spec(script: &str) -> StdioSpec {
    StdioSpec {
        program: PathBuf::from("python3"),
        args: vec!["-I".into(), "-c".into(), script.into()],
        env: vec![("PATH".into(), std::env::var("PATH").unwrap_or_default())],
    }
}

fn client() -> Implementation {
    Implementation {
        name: "nuxiva".into(),
        version: "1".into(),
        title: None,
    }
}

#[tokio::test]
async fn stdio_server_is_listed() -> McpResult<()> {
    let link = spawn_stdio(&spec(SERVER), 1024 * 1024)?;
    let (session, _, _) = Session::connect(link, Settings::default(), &client()).await?;
    let listing = session.list_tools().await?;
    assert_eq!(listing.tools.len(), 1);
    Ok(())
}

#[tokio::test]
async fn dying_process_closes_the_session() -> McpResult<()> {
    let link = spawn_stdio(&spec("import sys; sys.exit(0)"), 1024)?;
    let outcome = Session::connect(link, Settings::default(), &client()).await;
    assert!(matches!(
        outcome.err(),
        Some(McpError::Closed | McpError::Timeout)
    ));
    Ok(())
}

#[tokio::test]
async fn oversized_line_ends_the_stream() -> McpResult<()> {
    let flood =
        "import sys\nsys.stdout.write('x' * 5000 + '\\n')\nsys.stdout.flush()\nsys.stdin.read()";
    let link = spawn_stdio(&spec(flood), 100)?;
    let settings = Settings {
        request_timeout_ms: 500,
        ..Settings::default()
    };
    let outcome = Session::connect(link, settings, &client()).await;
    assert!(outcome.is_err());
    Ok(())
}

#[tokio::test]
async fn missing_program_is_an_io_error() {
    let missing = StdioSpec {
        program: PathBuf::from("/nonexistent/server"),
        args: Vec::new(),
        env: Vec::new(),
    };
    assert_eq!(spawn_stdio(&missing, 1024).err(), Some(McpError::Io));
}
