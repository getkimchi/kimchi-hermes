"""Kimchi (kimchi.dev) API-key model provider profile.

Layer 1: Hermes' own agent loop drives Kimchi-served models over the
OpenAI-compatible gateway. Auth is a plain API key resolved by Hermes'
built-in ladder (KIMCHI_API_KEY env -> ~/.hermes/.env -> setup wizard);
this plugin adds no custom auth code.
"""

import logging
from datetime import datetime, timezone

from providers import register_provider
from providers.base import ProviderProfile

try:
    from hermes_cli import __version__ as _HERMES_VERSION
except Exception:  # pragma: no cover - standalone import (tests stub or omit hermes_cli)
    _HERMES_VERSION = ""

_USER_AGENT = f"hermes-cli/{_HERMES_VERSION}" if _HERMES_VERSION else "hermes-cli"

# Hermes forwards profile.default_headers to its OpenAI clients, and the
# fetch_models probe applies them over the hermes-cli fallback — so this one
# UA identifies every request to our gateway.
_CHAT_USER_AGENT = (
    f"hermes-agent/{_HERMES_VERSION} (kimchi-plugin)" if _HERMES_VERSION else "hermes-agent (kimchi-plugin)"
)

logger = logging.getLogger(__name__)

# Kimchi's own client reads its model catalog from the metadata endpoint,
# not /openai/v1/models (SPEC F9). Live response shape is OQ-A1 (unverified);
# KimchiProfile.fetch_models therefore falls back to a lenient parser.
KIMCHI_MODELS_URL = "https://llm.kimchi.dev/v1/models/metadata?include_in_cli=true"


def _is_deprecated(item) -> bool:
    """True when the metadata marks the model already retired."""
    raw = item.get("deprecated_at")
    if not raw:
        return False
    try:
        moment = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    return moment <= datetime.now(timezone.utc)


def _lenient_model_ids(payload):
    """Extract model ids from the catalog payload (OQ-A1, resolved live).

    Recorded shape (2026-09-25): ``{"models": [{"slug": ..., "deprecated_at":
    ..., "limits": {"context_window": ...}, ...}]}``. Accepts that plus the
    OpenAI shapes (bare list / ``{"data": [...]}``); item ids come from
    ``slug`` | ``id`` | ``model`` | ``name``; already-retired models are
    skipped. Returns an ordered, de-duplicated list; ``None`` when nothing
    matches.
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
                (str(item[key]).strip() for key in ("slug", "id", "model", "name") if item.get(key)),
                "",
            )
            if model_id and _is_deprecated(item):
                continue
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


def _classify_gateway_error(error=None, *, status_code=None, error_code=None, message=None, body=None, model=None):
    """Kimchi's gateway 400s unknown model ids with a routing-specific body:
    "no registered providers found for the requested model" (it routes
    provider/model ids; an id from another provider's catalog — e.g. a leaked
    global model.default — misses every route). The built-in classifier's
    phrase table doesn't cover that body, so the failure degrades to generic
    format_error ("switch provider or send diagnostics"). Classify as
    model_not_found so Hermes' model-not-found recovery applies instead;
    hints mirror the built-in verdict
    (agent/error_classifier.py::_ABORT_FALLBACK) exactly.

    Passed to the profile as the ``classify_api_error`` constructor kwarg —
    it is a ProviderProfile dataclass FIELD (default None), not a method
    hook; a same-named method is silently overwritten by the dataclass
    __init__ on every instance.
    """
    haystack = f"{message or ''} {body or ''}"
    if status_code == 400 and "no registered providers found" in haystack:
        return {"reason": "model_not_found", "retryable": False, "should_fallback": True}
    return None


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
    # Every chat completion carries this UA; a user's model.default_headers
    # in config.yaml can still override.
    default_headers={"User-Agent": _CHAT_USER_AGENT},
    # Dataclass FIELD (not a method hook) — see _classify_gateway_error.
    classify_api_error=_classify_gateway_error,
)

register_provider(kimchi)
