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


def test_live_metadata_shape_slug_and_deprecated_filter(registry, fake_urllib):
    # Recorded live shape (OQ-A1, 2026-09-25): ids under "slug", retired
    # models carry a past "deprecated_at".
    fake_urllib.payload = {
        "models": [
            {
                "slug": "claude-opus-4-7",
                "provider": "anthropic",
                "tool_call": True,
                "deprecated_at": "2027-04-16T00:00:00Z",  # future — kept
                "limits": {"context_window": 1000000},
            },
            {
                "slug": "kimi-k2.5",
                "deprecated_at": "2020-01-01T00:00:00Z",  # past — skipped
            },
            {"slug": "kimi-k3"},  # no timestamp — kept
        ]
    }
    assert _profile().fetch_models(api_key="sk-test") == ["claude-opus-4-7", "kimi-k3"]


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


def test_unknown_model_400_classified_as_model_not_found(registry):
    """Cross-provider default ids (e.g. a leaked global model.default) 400
    with a routing-specific body — classify as model_not_found, not
    format_error (Desktop error observed 2026-09-29)."""
    profile = load_plugin("kimchi").kimchi
    verdict = profile.classify_api_error(
        status_code=400,
        body='{"error":"no registered providers found for the requested model"}',
    )
    assert verdict == {"reason": "model_not_found", "retryable": False, "should_fallback": True}


def test_classify_leaves_unrelated_errors_to_builtin(registry):
    profile = load_plugin("kimchi").kimchi
    assert profile.classify_api_error(status_code=400, body='{"error":"bad json"}') is None
    assert profile.classify_api_error(status_code=429, body="no registered providers found") is None
    assert profile.classify_api_error(status_code=400) is None
