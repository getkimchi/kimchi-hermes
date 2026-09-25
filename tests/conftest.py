"""Shared hermetic test fixtures.

The plugin modules import `providers` / `providers.base`, which only exist
inside Hermes' runtime. These fixtures stub them so plugins can be imported
standalone without Hermes or network access.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "model-providers"


class StubProviderProfile:
    """Field-capturing stand-in for providers.base.ProviderProfile.

    fetch_models mirrors the verified base contract (providers/base.py,
    read 2026-09-25): custom base_url → {base}/models, else models_url or
    {base_url}/models; Bearer auth + hermes-cli UA; OpenAI shape only
    ({"data": [...]} or bare list of {"id": ...}); None on failure.
    """

    def __init__(self, **kwargs):
        # Mirror the real dataclass defaults so plugins can rely on the same
        # attributes they'd see on providers.base.ProviderProfile.
        self.default_headers = {}
        self.supports_model_listing = True
        for key, value in kwargs.items():
            setattr(self, key, value)

    def fetch_models(self, *, api_key=None, base_url=None, timeout=8.0):
        if not getattr(self, "supports_model_listing", True):
            return None
        profile_base = getattr(self, "base_url", "") or ""
        caller_base = (base_url or "").strip()
        custom_base = bool(caller_base) and caller_base.rstrip("/") != profile_base.rstrip("/")
        if custom_base:
            url = caller_base.rstrip("/") + "/models"
        else:
            url = getattr(self, "models_url", "") or (profile_base.rstrip("/") + "/models" if profile_base else "")
        if not url:
            return None

        import json
        import urllib.request

        from hermes_cli.urllib_security import open_credentialed_url

        request = urllib.request.Request(url)
        if api_key:
            request.add_header("Authorization", f"Bearer {api_key}")
        request.add_header("Accept", "application/json")
        request.add_header("User-Agent", "hermes-cli/9.9.9")  # base's WAF-safe UA (stubbed __version__)
        for key, value in (getattr(self, "default_headers", None) or {}).items():
            request.add_header(key, value)
        try:
            with open_credentialed_url(request, timeout=timeout) as response:
                data = json.loads(response.read().decode())
        except Exception:
            return None
        items = data if isinstance(data, list) else data.get("data", [])
        return [m["id"] for m in items if isinstance(m, dict) and "id" in m]


@pytest.fixture
def registry(monkeypatch):
    """Stub the Hermes provider registry; returns {name: profile}."""
    registered: dict = {}

    providers_mod = types.ModuleType("providers")
    providers_mod.register_provider = lambda profile: registered.__setitem__(profile.name, profile)

    base_mod = types.ModuleType("providers.base")
    base_mod.ProviderProfile = StubProviderProfile
    base_mod.OMIT_TEMPERATURE = object()

    monkeypatch.setitem(sys.modules, "providers", providers_mod)
    monkeypatch.setitem(sys.modules, "providers.base", base_mod)
    return registered


def load_plugin(name: str):
    """Import model-providers/<name>/__init__.py as a standalone module."""
    path = PLUGIN_DIR / name / "__init__.py"
    spec = importlib.util.spec_from_file_location(f"kimchi_plugin_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_acp(monkeypatch):
    """Stub agent.copilot_acp_client with a record/raise double.

    The double mimics the surface KimchiACPClient overrides: _spawn raising a
    Copilot-branded RuntimeError, _run_prompt recording the requested model
    (model "BOOM" raises a branded RuntimeError), list_models returning a
    pseudo-entry-laden catalog.
    """

    class FakeCopilotACPClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.last_model = None

        def _spawn(self):
            raise RuntimeError(
                "Could not start Copilot ACP command 'copilot'. Install GitHub Copilot CLI "
                "or set HERMES_COPILOT_ACP_COMMAND/COPILOT_CLI_PATH."
            )

        def _run_prompt(self, prompt_text, *, timeout_seconds, model=None):
            self.last_model = model
            if str(model or "").strip() == "BOOM":
                raise RuntimeError("Copilot ACP session/prompt failed: boom")
            return "ok", ""

        def list_models(self, *, timeout_seconds=15.0):
            return ["multi-model", "auto", "kimi-k3", "kimi-k3"]

        def _handle_server_message(self, msg, *, process, cwd, text_parts, reasoning_parts, allow_file_requests=True):
            # Mimic the real shim: capture text chunks only; tool events drop.
            if msg.get("method") == "session/update":
                update = (msg.get("params") or {}).get("update") or {}
                if update.get("sessionUpdate") == "agent_message_chunk":
                    content = update.get("content") or {}
                    text_parts.append(str(content.get("text") or "") if isinstance(content, dict) else "")
                return True
            return False

    client_mod = types.ModuleType("agent.copilot_acp_client")
    client_mod.CopilotACPClient = FakeCopilotACPClient
    agent_mod = types.ModuleType("agent")
    agent_mod.copilot_acp_client = client_mod

    auth_mod = types.ModuleType("hermes_cli.auth")
    auth_mod.resolve_external_process_provider_credentials = lambda name: {
        "base_url": "acp://kimchi",
        "api_key": None,
        "command": "kimchi",
        "args": ("--mode", "acp", "--yolo"),
    }

    hermes_cli_mod = types.ModuleType("hermes_cli")
    hermes_cli_mod.auth = auth_mod

    monkeypatch.setitem(sys.modules, "agent", agent_mod)
    monkeypatch.setitem(sys.modules, "agent.copilot_acp_client", client_mod)
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli_mod)
    monkeypatch.setitem(sys.modules, "hermes_cli.auth", auth_mod)
    return {"client_mod": client_mod}


@pytest.fixture
def fake_urllib(monkeypatch):
    """Stub hermes_cli.urllib_security.open_credentialed_url.

    Configure ``opener.payload`` with a JSON-serializable body (or an
    Exception instance to simulate network failure); ``opener.calls`` records
    every request's url/Authorization/User-Agent for assertions.
    """
    import json as _json

    class FakeResponse:
        def __init__(self, payload):
            self._body = _json.dumps(payload).encode("utf-8")

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class FakeUrlOpener:
        def __init__(self):
            self.payload = None
            self.calls = []

        def __call__(self, request, timeout=None):
            self.calls.append(
                {
                    "url": request.full_url,
                    "auth": request.get_header("Authorization"),
                    "ua": request.get_header("User-agent"),
                }
            )
            if isinstance(self.payload, Exception):
                raise self.payload
            if self.payload is None:
                raise AssertionError("fake_urllib: no payload configured")
            return FakeResponse(self.payload)

    opener = FakeUrlOpener()

    urllib_security_mod = types.ModuleType("hermes_cli.urllib_security")
    urllib_security_mod.open_credentialed_url = opener

    hermes_cli_mod = types.ModuleType("hermes_cli")
    hermes_cli_mod.__version__ = "9.9.9"
    hermes_cli_mod.urllib_security = urllib_security_mod

    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli_mod)
    monkeypatch.setitem(sys.modules, "hermes_cli.urllib_security", urllib_security_mod)
    return opener
