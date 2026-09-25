"""Kimchi harness ACP provider profile (external process over stdio).

Layer 2: Hermes spawns `kimchi --mode acp --yolo` — YOLO is the user-approved
default permission mode (no approval prompts inside the harness). The escape
hatch to run WITHOUT YOLO is `KIMCHI_ACP_ARGS="--mode acp"`; note that an
EMPTY env var falls back to `process_args` below rather than clearing args.

The subprocess owns its own auth (Kimchi's credential store); Hermes never
handles an API key on this path.
"""

import json
import logging
import os
import shutil
from pathlib import Path

from providers import register_provider
from providers.base import ProviderProfile

logger = logging.getLogger(__name__)

# Hermes' CopilotACPClient treats its own provider name as the "no model
# requested" placeholder; ours is "kimchi-acp". Both are skipped for ACP
# model selection to avoid a spurious per-turn warning (review finding;
# SPEC §4).
_PLACEHOLDER_MODELS = {"kimchi-acp", "copilot-acp"}

# Max chars of ACP tool content echoed per rendered tool line.
_EXCERPT_MAX = 160

# Kimchi's session model ids arrive provider-prefixed (live: "kimchi-dev/...",
# "openai-codex/..."). NO content filtering: `auto` is the harness's router
# mode and `auto-beta` a real model (user decision 2026-09-25, SPEC F15).

# Longest-first so combined env-var mentions rebrand before their parts.
_REBRAND_RULES = (
    ("Copilot ACP", "Kimchi ACP"),
    ("GitHub Copilot CLI", "Kimchi CLI (kimchi.dev)"),
    ("HERMES_COPILOT_ACP_COMMAND/COPILOT_CLI_PATH", "KIMCHI_ACP_COMMAND"),
    ("HERMES_COPILOT_ACP_COMMAND / HERMES_COPILOT_ACP_ARGS", "KIMCHI_ACP_COMMAND / KIMCHI_ACP_ARGS"),
    ("HERMES_COPILOT_ACP_COMMAND", "KIMCHI_ACP_COMMAND"),
    ("HERMES_COPILOT_ACP_ARGS", "KIMCHI_ACP_ARGS"),
    ("Copilot", "Kimchi"),
)


def _rebrand(message: str) -> str:
    """Rewrite Copilot-branded shim errors to Kimchi guidance (review finding)."""
    for old, new in _REBRAND_RULES:
        message = message.replace(old, new)
    return message


def _dedupe_models(models):
    """Order-preserving de-duplication of the advertised model ids.

    Deliberately no content filtering: every id comes from the harness's own
    advertised config options — `auto` is the harness's router mode,
    `auto-beta` a real model (user decision 2026-09-25, SPEC F15).
    """
    if not models:
        return None
    seen, out = set(), []
    for model in models:
        model_id = str(model).strip()
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        out.append(model_id)
    return out or None


def _kimchi_command() -> str:
    return os.environ.get("KIMCHI_ACP_COMMAND", "").strip() or "kimchi"


def _kimchi_config_path() -> Path:
    override = os.environ.get("KIMCHI_CONFIG_PATH", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".config" / "kimchi" / "config.json"


def _kimchi_logged_in() -> bool:
    # An exported KIMCHI_API_KEY satisfies the harness too (SPEC F8); whether
    # it propagates through Hermes' subprocess env is OQ-B6 (unverified).
    if os.environ.get("KIMCHI_API_KEY", "").strip():
        return True
    try:
        data = json.loads(_kimchi_config_path().read_text(encoding="utf-8-sig"))
    except Exception:
        return False
    key = data.get("apiKey") or data.get("api_key") or ""
    return bool(str(key).strip())


try:
    # Only importable inside the Hermes runtime; the guard keeps this module
    # importable standalone (tooling/tests). Without Hermes, create_client
    # fails loudly only when actually invoked.
    from agent.copilot_acp_client import CopilotACPClient as _ACPClientBase
except ImportError:  # pragma: no cover - exercised via stubs in tests
    _ACPClientBase = object


def _content_excerpt(update) -> str:
    """Compact text excerpt from an ACP tool-call content array.

    Mirrors the ecosystem convention (Zed/ACP reference clients render tool
    content inline): agents embed progress text and output excerpts in the
    update's ``content`` blocks. Accepts both block shapes ({type: "content",
    content: {text}} and {type: "text", text}); collapses whitespace and
    truncates. Empty when the shape is unrecognized.
    """
    blocks = update.get("content")
    if not isinstance(blocks, list):
        return ""
    parts = []
    for block in blocks:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            inner = block.get("content")
            if isinstance(inner, dict) and isinstance(inner.get("text"), str):
                parts.append(inner["text"])
            elif isinstance(block.get("text"), str):
                parts.append(block["text"])
    text = " ".join(" ".join(parts).split())
    if len(text) > _EXCERPT_MAX:
        text = text[: _EXCERPT_MAX - 1] + "…"
    return text


class KimchiACPClient(_ACPClientBase):
    """CopilotACPClient with Kimchi-facing error strings and placeholder handling."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # toolCallId -> title, from the initial tool_call event; ACP allows
        # tool_call_update events to omit the title, and rendering the raw id
        # would be noise. Completed/failed entries are pruned.
        self._tool_call_titles = {}

    def _spawn(self):
        try:
            return super()._spawn()
        except RuntimeError as exc:
            raise RuntimeError(_rebrand(str(exc))) from exc

    def _run_prompt(self, prompt_text, *, timeout_seconds, model=None):
        # Provider-name placeholders mean "no explicit model" — skip ACP model
        # selection instead of warning every turn (review finding).
        if str(model or "").strip().lower() in _PLACEHOLDER_MODELS:
            model = None
        try:
            return super()._run_prompt(prompt_text, timeout_seconds=timeout_seconds, model=model)
        except (RuntimeError, TimeoutError) as exc:
            raise type(exc)(_rebrand(str(exc))) from exc

    def _handle_server_message(self, msg, *, process, cwd, text_parts, reasoning_parts, allow_file_requests=True):
        """Surface harness-native tool activity in the visible reply text.

        Hermes' shim captures only text chunks and silently drops
        tool_call/tool_call_update updates, so YOLO harness execution is
        invisible in Hermes' UI and absent from later turns' flattened
        context — the "did you do it?" self-doubt loop observed in e2e
        (SPEC OQ-B4). Render one compact line per tool event into
        text_parts (arrival order → interleaved with narrative chunks);
        delegate everything else to the shim untouched.
        """
        if msg.get("method") == "session/update" and text_parts is not None:
            update = (msg.get("params") or {}).get("update") or {}
            kind = str(update.get("sessionUpdate") or "")
            status = str(update.get("status") or "").strip()
            tool_call_id = str(update.get("toolCallId") or "")
            title = str(update.get("title") or "").strip()
            if kind == "tool_call":
                if title and tool_call_id:
                    self._tool_call_titles[tool_call_id] = title
            elif kind == "tool_call_update" and not title and tool_call_id in self._tool_call_titles:
                title = self._tool_call_titles[tool_call_id]
                if status in ("completed", "failed"):
                    self._tool_call_titles.pop(tool_call_id, None)
            render = kind == "tool_call" or (
                kind == "tool_call_update" and status in ("completed", "failed")
            )
            if render:
                tool_kind = str(update.get("kind") or "").strip()
                label = f"{tool_kind}: {title}" if tool_kind and tool_kind != "other" else title
                line = f"[kimchi {label}]" + (f" {status}" if status else "")
                excerpt = _content_excerpt(update)
                if excerpt:
                    line += f" — {excerpt}"
                text_parts.append(line + "\n")
                return True
        return super()._handle_server_message(
            msg,
            process=process,
            cwd=cwd,
            text_parts=text_parts,
            reasoning_parts=reasoning_parts,
            allow_file_requests=allow_file_requests,
        )


class KimchiACPProfile(ProviderProfile):
    """Kimchi harness over ACP stdio — `kimchi --mode acp --yolo`."""

    def create_client(self, **client_kwargs):
        return KimchiACPClient(**client_kwargs)

    def fetch_models(self, *, api_key=None, base_url=None, timeout=15.0):
        """Model ids advertised by a short-lived signed-in ACP session.

        The subprocess owns auth (env_vars=()), so api_key/base_url are
        ignored. None when the CLI is missing, refuses --mode acp, or the
        probe fails/times out — callers fall back to their next source.
        """
        from hermes_cli.auth import resolve_external_process_provider_credentials

        try:
            creds = resolve_external_process_provider_credentials(self.name)
            if not str(creds.get("base_url") or "").startswith("acp://"):
                return None
            client = self.create_client(
                api_key=creds.get("api_key"),
                base_url=creds.get("base_url"),
                command=creds.get("command"),
                args=creds.get("args"),
            )
            models = client.list_models(timeout_seconds=timeout) or None
        except Exception as exc:
            logger.debug("kimchi-acp fetch_models: %s", exc)
            return None
        return _dedupe_models(models)

    def setup_status(self, **kwargs):
        """Gate setup on CLI presence + Kimchi login (SPEC §4)."""
        command = _kimchi_command()
        available = shutil.which(command) is not None
        logged_in = _kimchi_logged_in()
        if not available:
            detail = (
                f"'{command}' not found on PATH — install the Kimchi CLI "
                "(https://kimchi.dev) or set KIMCHI_ACP_COMMAND"
            )
        elif logged_in:
            detail = f"{command} found; logged in"
        else:
            detail = f"{command} found but not logged in — run 'kimchi login'"
        return {
            "available": available,
            "logged_in": logged_in,
            "plan": None,
            "detail": detail,
            "login_command": "kimchi login",
        }


kimchi_acp = KimchiACPProfile(
    name="kimchi-acp",
    aliases=("kimchi-agent",),
    display_name="Kimchi (Harness via ACP)",
    description="Kimchi coding harness (kimchi.dev) driven over ACP stdio",
    api_mode="chat_completions",  # ACP subprocess uses chat_completions routing
    env_vars=(),  # managed by the ACP subprocess
    base_url="acp://kimchi",  # ACP internal scheme
    auth_type="external_process",
    # Placeholder model id meaning "harness session default" — parity with
    # upstream copilot-acp's documented `--model copilot-acp` usage. Merged
    # into the /model picker alongside the live session catalog (models.py
    # merge_profile_catalog), and accepted by KimchiACPClient as a no-model-
    # -selection request. Only surfaces when the live probe fails otherwise.
    fallback_models=("kimchi-acp",),
    # How to launch the harness; KIMCHI_ACP_ARGS lets users override the argv
    # tail (e.g. drop --yolo). See module docstring for the empty-string trap.
    process_command="kimchi",
    process_args=("--mode", "acp", "--yolo"),
    process_command_env_vars=("KIMCHI_ACP_COMMAND",),
    process_args_env_var="KIMCHI_ACP_ARGS",
)

register_provider(kimchi_acp)
