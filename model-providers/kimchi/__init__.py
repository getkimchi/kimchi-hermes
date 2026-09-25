"""Kimchi (kimchi.dev) API-key model provider profile.

Layer 1: Hermes' own agent loop drives Kimchi-served models over the
OpenAI-compatible gateway. Auth is a plain API key resolved by Hermes'
built-in ladder (KIMCHI_API_KEY env -> ~/.hermes/.env -> setup wizard);
this plugin adds no custom auth code.
"""

import logging

from providers import register_provider
from providers.base import ProviderProfile

try:
    from hermes_cli import __version__ as _HERMES_VERSION
except Exception:  # pragma: no cover - standalone import (tests stub or omit hermes_cli)
    _HERMES_VERSION = ""

_USER_AGENT = f"hermes-cli/{_HERMES_VERSION}" if _HERMES_VERSION else "hermes-cli"

logger = logging.getLogger(__name__)

# Kimchi's own client reads its model catalog from the metadata endpoint,
# not /openai/v1/models (SPEC F9). Live response shape is OQ-A1 (unverified);
# KimchiProfile.fetch_models therefore falls back to a lenient parser.
KIMCHI_MODELS_URL = "https://llm.kimchi.dev/v1/models/metadata?include_in_cli=true"


def _lenient_model_ids(payload):
    """Extract model ids from plausible catalog payload shapes (OQ-A1).

    Accepts: a bare list, ``{"data": [...]}``, or ``{"models": [...]}``;
    items may be id strings or dicts with an ``id``/``model``/``name`` key.
    Returns an ordered, de-duplicated list; ``None`` when nothing matches.
    """
    if isinstance(payload, dict):
        items = next(
            (payload[key] for key in ("data", "models") if isinstance(payload.get(key), list)),
            None,
        )
    elif isinstance(payload, list):
        items = payload
    else:
        return None
    if items is None:
        return None

    ids, seen = [], set()
    for item in items:
        if isinstance(item, str):
            model_id = item.strip()
        elif isinstance(item, dict):
            model_id = next(
                (str(item[key]).strip() for key in ("id", "model", "name") if item.get(key)),
                "",
            )
        else:
            continue
        if model_id and model_id not in seen:
            seen.add(model_id)
            ids.append(model_id)
    return ids


class KimchiProfile(ProviderProfile):
    """Kimchi — API-key provider; catalog from the metadata endpoint."""

    def fetch_models(self, *, api_key=None, base_url=None, timeout=8.0):
        """Live catalog, tolerating non-OpenAI metadata shapes (OQ-A1).

        Lenient-first by design: the base parser silently DROPS items lacking
        an ``id`` key and returns a partial (truthy) list, which would mask
        models named via ``model``/``name`` keys. The lenient parser is a
        superset of the OpenAI shape, so one fetch of ``models_url`` covers
        every plausible metadata shape.

        A caller-provided custom ``base_url`` is the user's own OpenAI-shaped
        endpoint — defer to the base implementation, never second-guess it.
        """
        if not self.supports_model_listing:
            return None
        custom_base = bool(base_url) and base_url.rstrip("/") != (self.base_url or "").rstrip("/")
        if custom_base:
            return super().fetch_models(api_key=api_key, base_url=base_url, timeout=timeout)
        return self._fetch_lenient(api_key=api_key, timeout=timeout)

    def _fetch_lenient(self, *, api_key=None, timeout=8.0):
        url = self.models_url or ""
        if not url:
            return None

        import json
        import urllib.request

        from hermes_cli.urllib_security import open_credentialed_url

        request = urllib.request.Request(url)
        if api_key:
            request.add_header("Authorization", f"Bearer {api_key}")
        request.add_header("Accept", "application/json")
        request.add_header("User-Agent", _USER_AGENT)
        for key, value in (self.default_headers or {}).items():
            request.add_header(key, value)

        try:
            with open_credentialed_url(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode())
        except Exception as exc:
            logger.debug("kimchi fetch_models: %s", exc)
            return None
        return _lenient_model_ids(payload)


kimchi = KimchiProfile(
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
