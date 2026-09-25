"""Kimchi-acp (Layer 2) hook tests: client subclass, catalog filter, setup status.

All Hermes runtime surfaces (agent.copilot_acp_client, hermes_cli.auth) are
stubbed hermetically via the fake_acp fixture.
"""

import pytest

from conftest import load_plugin


@pytest.fixture
def profile(registry, fake_acp):
    return load_plugin("kimchi-acp").kimchi_acp


def test_create_client_returns_kimchi_branded_subclass(profile):
    client = profile.create_client(
        api_key=None, base_url="acp://kimchi", command="kimchi", args=("--mode", "acp", "--yolo")
    )
    assert type(client).__name__ == "KimchiACPClient"
    assert client.kwargs["base_url"] == "acp://kimchi"
    assert client.kwargs["args"] == ("--mode", "acp", "--yolo")


def test_spawn_error_rebranded(profile):
    client = profile.create_client()
    with pytest.raises(RuntimeError) as excinfo:
        client._spawn()
    message = str(excinfo.value)
    assert "Kimchi ACP" in message
    assert "Kimchi CLI (kimchi.dev)" in message
    assert "KIMCHI_ACP_COMMAND" in message
    assert "Copilot" not in message
    assert "COPILOT" not in message


def test_placeholder_model_skips_selection(profile):
    client = profile.create_client()
    client._run_prompt("hi", timeout_seconds=5, model="kimchi-acp")
    assert client.last_model is None  # no spurious per-turn warning

    client._run_prompt("hi", timeout_seconds=5, model="kimi-k3")
    assert client.last_model == "kimi-k3"  # real models pass through


def test_run_prompt_error_rebranded(profile):
    client = profile.create_client()
    with pytest.raises(RuntimeError) as excinfo:
        client._run_prompt("hi", timeout_seconds=5, model="BOOM")
    assert "Kimchi ACP" in str(excinfo.value)
    assert "Copilot" not in str(excinfo.value)


def test_fetch_models_filters_pseudo_entries(registry, fake_acp):
    # Live shape (2026-09-25): ids arrive provider-prefixed; the pseudo check
    # runs on the leaf, so kimchi-dev/auto is dropped but auto-beta stays.
    module = load_plugin("kimchi-acp")
    assert module._filter_pseudo_models(
        ["kimchi-dev/auto", "kimchi-dev/multi-model", "kimchi-dev/auto-beta", "kimchi-dev/kimi-k3"]
    ) == ["kimchi-dev/auto-beta", "kimchi-dev/kimi-k3"]
    assert module.kimchi_acp.fetch_models() == ["kimi-k3"]  # fake catalog: bare pseudo ids dropped


def test_fetch_models_non_acp_base_url_returns_none(monkeypatch, registry, fake_acp):
    import sys
    import types

    auth_mod = sys.modules["hermes_cli.auth"]
    monkeypatch.setattr(
        auth_mod,
        "resolve_external_process_provider_credentials",
        lambda name: {"base_url": "https://not-acp.example.com", "command": "kimchi", "args": ()},
    )
    assert load_plugin("kimchi-acp").kimchi_acp.fetch_models() is None


def test_fetch_models_swallows_credential_errors(monkeypatch, registry, fake_acp):
    import sys

    auth_mod = sys.modules["hermes_cli.auth"]

    def boom(name):
        raise RuntimeError("AuthError: missing CLI")

    monkeypatch.setattr(auth_mod, "resolve_external_process_provider_credentials", boom)
    assert load_plugin("kimchi-acp").kimchi_acp.fetch_models() is None


def test_setup_status_logged_in_via_config(registry, fake_acp, monkeypatch, tmp_path):
    config = tmp_path / "config.json"
    config.write_text('{"apiKey": "sk-secret"}', encoding="utf-8")
    monkeypatch.setenv("KIMCHI_CONFIG_PATH", str(config))
    monkeypatch.delenv("KIMCHI_API_KEY", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/kimchi" if name == "kimchi" else None)

    status = load_plugin("kimchi-acp").kimchi_acp.setup_status()
    assert status == {
        "available": True,
        "logged_in": True,
        "plan": None,
        "detail": "kimchi found; logged in",
        "login_command": "kimchi login",
    }


def test_setup_status_not_logged_in(registry, fake_acp, monkeypatch, tmp_path):
    monkeypatch.setenv("KIMCHI_CONFIG_PATH", str(tmp_path / "missing.json"))
    monkeypatch.delenv("KIMCHI_API_KEY", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/kimchi" if name == "kimchi" else None)

    status = load_plugin("kimchi-acp").kimchi_acp.setup_status()
    assert status["available"] is True
    assert status["logged_in"] is False
    assert "kimchi login" in status["detail"]


def test_setup_status_cli_missing(registry, fake_acp, monkeypatch, tmp_path):
    monkeypatch.setenv("KIMCHI_CONFIG_PATH", str(tmp_path / "missing.json"))
    monkeypatch.delenv("KIMCHI_API_KEY", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)

    status = load_plugin("kimchi-acp").kimchi_acp.setup_status()
    assert status["available"] is False
    assert status["logged_in"] is False
    assert "KIMCHI_ACP_COMMAND" in status["detail"]


def test_env_key_counts_as_logged_in(registry, fake_acp, monkeypatch, tmp_path):
    monkeypatch.setenv("KIMCHI_CONFIG_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setenv("KIMCHI_API_KEY", "sk-env")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/kimchi" if name == "kimchi" else None)

    status = load_plugin("kimchi-acp").kimchi_acp.setup_status()
    assert status["logged_in"] is True


def test_filter_pseudo_models_unit(registry, fake_acp):
    module = load_plugin("kimchi-acp")
    assert module._filter_pseudo_models(None) is None
    assert module._filter_pseudo_models([]) is None
    assert module._filter_pseudo_models(["auto"]) is None  # all pseudo → None
    assert module._filter_pseudo_models(["Auto", "kimi-k3", "kimi-k3"]) == ["kimi-k3"]
