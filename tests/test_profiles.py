"""Hermetic tests: profile registration, declarative fields, plugin manifests."""

import subprocess
from pathlib import Path

from conftest import PLUGIN_DIR, load_plugin


def test_kimchi_registered_and_fields(registry):
    load_plugin("kimchi")

    assert set(registry) == {"kimchi"}
    profile = registry["kimchi"]
    assert profile.name == "kimchi"
    assert profile.aliases == ("kimchi-dev",)
    assert profile.display_name == "Kimchi"
    assert profile.signup_url == "https://app.kimchi.dev"
    assert profile.env_vars == ("KIMCHI_API_KEY", "KIMCHI_BASE_URL")
    assert profile.base_url == "https://llm.kimchi.dev/openai/v1"
    # Catalog comes from Kimchi's metadata endpoint, not /openai/v1/models (SPEC F9).
    assert profile.models_url == "https://llm.kimchi.dev/v1/models/metadata?include_in_cli=true"
    assert profile.auth_type == "api_key"
    assert profile.fallback_models == ()  # live catalog only — user decision
    # No custom UA declared — the base class's WAF-safe hermes-cli UA must win
    # (the stub only records fields the plugin explicitly passes).
    assert not getattr(profile, "default_headers", {}).get("User-Agent")


def test_kimchi_acp_registered_and_fields(registry):
    load_plugin("kimchi-acp")

    assert set(registry) == {"kimchi-acp"}
    profile = registry["kimchi-acp"]
    assert profile.name == "kimchi-acp"
    assert profile.aliases == ("kimchi-agent",)
    assert profile.api_mode == "chat_completions"
    assert profile.base_url == "acp://kimchi"
    assert profile.auth_type == "external_process"
    assert profile.env_vars == ()  # subprocess owns auth
    assert profile.process_command == "kimchi"
    # YOLO is the user-approved default (SPEC §6).
    assert profile.process_args == ("--mode", "acp", "--yolo")
    assert profile.process_command_env_vars == ("KIMCHI_ACP_COMMAND",)
    assert profile.process_args_env_var == "KIMCHI_ACP_ARGS"


def test_plugin_yaml_manifests():
    expected = {
        "kimchi": "kimchi-provider",
        "kimchi-acp": "kimchi-acp-provider",
    }
    for plugin_name, manifest_name in expected.items():
        text = (PLUGIN_DIR / plugin_name / "plugin.yaml").read_text(encoding="utf-8")
        assert f"name: {manifest_name}" in text
        assert "kind: model-provider" in text
        assert "version: 1.0.0" in text


def test_install_script_copies_both_plugins(tmp_path):
    repo_root = Path(__file__).resolve().parent.parent
    subprocess.run(
        ["bash", str(repo_root / "install.sh")],
        env={"HERMES_HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
        check=True,
        capture_output=True,
        text=True,
    )
    dest = tmp_path / "plugins" / "model-providers"
    assert (dest / "kimchi" / "__init__.py").is_file()
    assert (dest / "kimchi" / "plugin.yaml").is_file()
    assert (dest / "kimchi-acp" / "__init__.py").is_file()
    assert (dest / "kimchi-acp" / "plugin.yaml").is_file()
