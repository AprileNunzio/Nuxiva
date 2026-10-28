import pytest
import feature_registry
from config import read_env, write_env
from feature_registry import Registry
from packages import step_wanted
from state import store
from steps import run_pipeline


@pytest.fixture(autouse=True)
def reset_env(tmp_path, monkeypatch):
    test_env = tmp_path / "nuxiva.env"
    test_env.write_text("NUXIVA_KIOSK=1\n", encoding="utf-8")
    monkeypatch.setattr("config.ENV_FILE", test_env)
    store.steps.clear()
    store.steps["kiosk"] = {"status": "done", "progress": 100}
    yield


def test_kiosk_toggle_persistence_and_wanted(tmp_path, monkeypatch):
    state_file = tmp_path / "features.json"
    monkeypatch.setattr(feature_registry, "STATE_FILE", state_file)
    registry = Registry()
    registry.scan()
    assert registry.features.get("kiosk") is not None

    write_env({"NUXIVA_KIOSK": "0"})
    registry.note_env_change({"NUXIVA_KIOSK": "0"})
    assert registry._rec("kiosk")["mode"] == "0"
    assert registry.enabled("kiosk") is False

    registry2 = Registry()
    registry2.scan()
    assert registry2._rec("kiosk")["mode"] == "0"
    assert registry2.enabled("kiosk") is False

    env = read_env()
    assert env.get("NUXIVA_KIOSK") == "0"
    assert step_wanted("kiosk", env) is False


@pytest.mark.asyncio
async def test_kiosk_pipeline_teardown_status(monkeypatch):
    monkeypatch.setenv("NUXIVA_TEST_AUTH", "1")
    write_env({"NUXIVA_KIOSK": "0"})
    store.steps["kiosk"] = {"status": "done", "progress": 100}

    async def mock_action(step, action, stream=False, quiet=False):
        return 0, ""

    monkeypatch.setattr("steps.run_step_action", mock_action)
    ok = await run_pipeline(only=["kiosk"], force=True)
    assert ok is True
    assert store.steps["kiosk"]["status"] == "disabled"
