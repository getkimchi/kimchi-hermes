"""Kimchi (kimchi.dev) API-key model provider profile.

Layer 1: Hermes' own agent loop drives Kimchi-served models over the
OpenAI-compatible gateway. Auth is a plain API key resolved by Hermes'
built-in ladder (KIMCHI_API_KEY env -> ~/.hermes/.env -> setup wizard);
this plugin adds no custom auth code.
"""

from providers import register_provider
from providers.base import ProviderProfile

# Kimchi's own client reads its model catalog from the metadata endpoint,
# not /openai/v1/models (SPEC F9). Response shape is verified live in
# OQ-A1; fetch_models adapts in C2 if the shape is not OpenAI-standard.
KIMCHI_MODELS_URL = "https://llm.kimchi.dev/v1/models/metadata?include_in_cli=true"

kimchi = ProviderProfile(
    name="kimchi",
    aliases=("kimchi-dev",),
    display_name="Kimchi",
    description="Kimchi (kimchi.dev) — agentic models via OpenAI-compatible API",
    signup_url="https://app.kimchi.dev",
    env_vars=("KIMCHI_API_KEY", "KIMCHI_BASE_URL"),
    base_url="https://llm.kimchi.dev/openai/v1",
    models_url=KIMCHI_MODELS_URL,
    auth_type="api_key",
    # Live catalog only (user decision, SPEC §3): a transient catalog failure
    # means an empty picker until recovery — never a stale hardcoded list.
    fallback_models=(),
    # Deliberately NO custom default_headers User-Agent: the base
    # fetch_models() already sends a WAF-safe `hermes-cli/<version>` UA and a
    # custom one would override it (review finding).
)

register_provider(kimchi)
