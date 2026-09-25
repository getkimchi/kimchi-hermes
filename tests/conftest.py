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
    """Field-capturing stand-in for providers.base.ProviderProfile."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


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
