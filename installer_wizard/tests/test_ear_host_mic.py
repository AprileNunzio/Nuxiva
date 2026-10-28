import asyncio
import pytest
from features.ear.broadcast import SESSIONS
from features.ear.host_mic import HeadlessSocket, HostMicCapture, pick_capture_binary


@pytest.fixture(autouse=True)
def clean_sessions():
    SESSIONS.clear()
    yield
    SESSIONS.clear()


def test_pick_capture_binary(monkeypatch):
    monkeypatch.setenv("NUXIVA_MIC_CMD", "test-rec -r 16000")
    assert pick_capture_binary() == ["test-rec", "-r", "16000"]


def test_host_mic_should_capture_toggle(monkeypatch):
    capture = HostMicCapture(lambda ws: ws)
    monkeypatch.setenv("NUXIVA_EAR_HOST_MIC", "0")
    assert capture.should_capture() is False

    monkeypatch.setenv("NUXIVA_EAR_HOST_MIC", "1")
    assert capture.should_capture() is True


def test_host_mic_yields_to_visible_session(monkeypatch):
    monkeypatch.setenv("NUXIVA_EAR_HOST_MIC", "1")
    capture = HostMicCapture(lambda ws: ws)

    class MockSession:
        def __init__(self, visible):
            self.page = {"visible": visible}

    session = MockSession("visible")
    SESSIONS.add(session)
    assert capture.should_capture() is False

    session.page["visible"] = "hidden"
    assert capture.should_capture() is True


@pytest.mark.asyncio
async def test_headless_socket_dispatch(monkeypatch):
    dispatched = []

    async def mock_dispatch(event):
        dispatched.append(event)

    monkeypatch.setattr("features.ear.host_mic.dispatch_headless_command", mock_dispatch)

    sock = HeadlessSocket()
    await sock.send('{"type": "transcript", "text": "ciao Nuxiva", "lang": "it"}')
    await asyncio.sleep(0.05)

    assert len(dispatched) == 1
    assert dispatched[0]["text"] == "ciao Nuxiva"
