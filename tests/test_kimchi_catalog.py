"""Kimchi (Layer 1) catalog tests: metadata endpoint + lenient shape parsing.

All network access goes through the fake_urllib fixture (hermetic).
"""

from conftest import load_plugin

METADATA_URL = "https://llm.kimchi.dev/v1/models/metadata?include_in_cli=true"
BASE_URL = "https://llm.kimchi.dev/openai/v1"


def _profile():
    return load_plugin("kimchi").kimchi


def test_standard_openai_shape_via_metadata_endpoint(registry, fake_urllib):
    fake_urllib.payload = {"data": [{"id": "kimi-k3"}, {"id": "kimi-k2.5"}]}
    models = _profile().fetch_models(api_key="sk-test")
    assert models == ["kimi-k3", "kimi-k2.5"]
    assert len(fake_urllib.calls) == 1
    assert fake_urllib.calls[0]["url"] == METADATA_URL
    assert fake_urllib.calls[0]["auth"] == "Bearer sk-test"
    assert fake_urllib.calls[0]["ua"] == "hermes-cli/9.9.9"


def test_metadata_models_shape_parsed_leniently(registry, fake_urllib):
    # Single fetch: the lenient parser handles the {"models": [...]} shape.
    fake_urllib.payload = {"models": [{"name": "kimi-k3"}, {"id": "kimi-k2.5"}, "kimi-k4-lite"]}
    models = _profile().fetch_models(api_key="sk-test")
    assert models == ["kimi-k3", "kimi-k2.5", "kimi-k4-lite"]
    assert len(fake_urllib.calls) == 1
    assert fake_urllib.calls[0]["url"] == METADATA_URL
    assert all(call["auth"] == "Bearer sk-test" for call in fake_urllib.calls)


def test_bare_list_shape(registry, fake_urllib):
    fake_urllib.payload = [{"id": "kimi-k3"}, {"model": "kimi-k2.5"}]
    assert _profile().fetch_models(api_key="sk-test") == ["kimi-k3", "kimi-k2.5"]


def test_lenient_dedupes_and_ignores_junk(registry, fake_urllib):
    fake_urllib.payload = {
        "models": [
            {"id": "kimi-k3"},
            {"id": "kimi-k3"},  # duplicate
            {"irrelevant": True},  # no id-ish key
            42,  # wrong type
            {"name": " kimi-k2.5 "},  # whitespace stripped
        ]
    }
    assert _profile().fetch_models(api_key="sk-test") == ["kimi-k3", "kimi-k2.5"]


def test_unrecognized_shape_returns_none(registry, fake_urllib):
    fake_urllib.payload = {"unexpected": {"nesting": True}}
    assert _profile().fetch_models(api_key="sk-test") is None


def test_network_error_returns_none(registry, fake_urllib):
    fake_urllib.payload = RuntimeError("connection refused")
    assert _profile().fetch_models(api_key="sk-test") is None


def test_custom_base_url_defers_to_base_parser(registry, fake_urllib):
    # A user-configured endpoint is the user's own — base implementation only (SPEC §3).
    fake_urllib.payload = {"models": [{"id": "local-model"}]}
    models = _profile().fetch_models(api_key="sk-test", base_url="http://localhost:9999/v1")
    assert not models  # base parser only reads OpenAI shape → empty
    assert len(fake_urllib.calls) == 1
    assert fake_urllib.calls[0]["url"] == "http://localhost:9999/v1/models"


def test_no_key_omits_auth_header(registry, fake_urllib):
    fake_urllib.payload = {"data": [{"id": "kimi-k3"}]}
    assert _profile().fetch_models(api_key=None) == ["kimi-k3"]
    assert fake_urllib.calls[0]["auth"] is None


def test_lenient_model_ids_unit(registry):
    module = load_plugin("kimchi")
    assert module._lenient_model_ids(None) is None
    assert module._lenient_model_ids("junk") is None
    assert module._lenient_model_ids({"data": []}) == []
    assert module._lenient_model_ids([{"id": "a"}, {"model": "b"}, {"name": "c"}]) == ["a", "b", "c"]
