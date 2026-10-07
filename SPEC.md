# Kimchi providers for Hermes Agent — v1 Spec

> **Process note.** This spec is a *hypothesis document*, not a frozen contract
> (cf. Kent Beck, Jan 2026: "Implementation doesn't invalidate a spec —
> implementation completes it"). Each Open Question lists how we expect to
> learn the answer. The spec is updated as implementation teaches; commits
> reference the section they change.
>
> **Review status:** APPROVE-WITH-CHANGES by two independent model reviews
> (kimi-k3, glm-5.3, 2026-09-25). Their findings are incorporated below;
> raw reports in `~/.kimchi-harness/.kimchi/docs/review.md` (latest) and the
> reviewers' summaries. Both reviewers verified the evidence table against
> primary sources, including a local byte-identical Hermes clone at
> `~/.hermes/hermes-agent@d5785bb`.

## 1. Goal

Two Hermes model-provider plugins, developed in this repo and installed into
`~/.hermes/plugins/model-providers/` (Hermes' user-plugin directory; see
`plugins/model-providers/README.md` upstream):

| Plugin | Layer | What it gives a Hermes user |
|---|---|---|
| `kimchi` | API-key model provider | Hermes' own agent loop drives Kimchi-served models over OpenAI-compatible HTTP (`llm.kimchi.dev`) |
| `kimchi-acp` | ACP external-process provider | Hermes spawns `kimchi --mode acp` over stdio (YOLO opt-in via `KIMCHI_ACP_ARGS`); the **Kimchi harness itself** serves the turn via Agent Client Protocol |

Layer 2 is the primary use case (the user runs the actual Kimchi harness from
Hermes' TUI/gateway). Layer 1 stays relevant for direct model access with
Hermes' tooling fully in charge.

## 2. Verified facts (evidence table)

Everything below was confirmed by reading source, not assumed — and
spot-checked by two independent model reviews:

| # | Fact | Source |
|---|---|---|
| F1 | Kimchi CLI binary is `kimchi` (`bin: src/entry.ts`), "a coding agent CLI powered by Cast AI" | `kimchi-harness/package.json` |
| F2 | ACP server mode exists: `kimchi --mode acp` | `kimchi-harness/src/cli-args.test.ts:80-99` |
| F3 | Permission modes `default/plan/auto/yolo`; `--yolo` → `"yolo"` = "no restrictions"; also switchable at runtime via ACP config option | `server.ts:149-154, 1829-1840`, `server.test.ts:6350` |
| F4 | ACP `initialize()` returns `protocolVersion` from the official SDK, `agentInfo: {name: "kimchi"}`, and advertises auth methods: browser OAuth `"kimchi-agent"` always; terminal `"kimchi login"` only when the client advertises `auth.terminal` | `server.ts:344-437` |
| F5 | ACP `authenticate()` runs browser OAuth and persists the credential to Kimchi's store (`~/.config/kimchi/config.json` via `writeApiKey`) plus the harness agent dir's `auth.json`/`models.json` | `server.ts:437-486` |
| F6 | API-key validation endpoint: `https://api.cast.ai/v1/llm/openai/supported-providers` (Bearer auth, 200/401/403 semantics) | `src/auth/validator.ts:9-90` |
| F7 | Kimchi inference gateway (OpenAI-compatible chat completions): `https://llm.kimchi.dev/openai/v1/chat/completions` | `src/llm-gateway-error.test.ts:90`, `src/http/stream-idle-timeout.test.ts:28` |
| F8 | Kimchi API-key precedence: `KIMCHI_API_KEY` env > project `.kimchi/config.json` (trust-gated) > `~/.config/kimchi/config.json` (`apiKey` field) | `src/config.ts:9,546-551`, `src/setup-wizard/steps/auth.ts:22-53` |
| F9 | Kimchi's own client discovers its model catalog at `https://llm.kimchi.dev/v1/models/metadata?include_in_cli=true` — **not** `/openai/v1/models` (review finding; cf. OQ-A1) | kimi-k3 review, from kimchi-harness model sources |
| F10 | Hermes plugin contract: a directory with `__init__.py` (calls `register_provider(profile)`) + `plugin.yaml`; user dir `$HERMES_HOME/plugins/model-providers/` lazily discovered, last-writer-wins over bundled | `providers/README.md`, `plugins/model-providers/README.md` (upstream) |
| F11 | Hermes external-process profile fields: `auth_type="external_process"`, `process_command`, `process_args`, `process_command_env_vars`, `process_args_env_var`; consumed by `hermes_cli/auth.resolve_external_process_provider_credentials()`. Empty `KIMCHI_ACP_ARGS` **falls back to `process_args`** (it does not clear args) | `providers/base.py`, `hermes_cli/auth.py:2062-2063` (both reviewers) |
| F12 | Hermes `CopilotACPClient` is parameterized by `command`/`args` (reusable for any ACP agent); sends `initialize` with `protocolVersion: 1`; per request spawns a short-lived session, **blocking until the whole turn finishes, then fake-chunks the result** (no true token streaming); **auto-CANCELS `session/request_permission`**; flattens the conversation to a text prompt (images dropped) and extracts OpenAI-shaped tool calls from the reply text; model selection via v1 `session/set_config_option` or legacy `session/set_model`; default 900 s whole-session timeout; error strings are Copilot-branded | `agent/copilot_acp_client.py` (upstream) |
| F13 | Hermes' bundled `copilot-acp` plugin is the template: `create_client()` returns the ACP shim client; `fetch_models()` probes models via a short-lived `session/new` | `plugins/model-providers/copilot-acp/__init__.py` (upstream) |
| F14 | **OQ-B1 closed:** Kimchi's ACP SDK 0.19.2 uses `PROTOCOL_VERSION = 1` — matches Hermes' handshake exactly. *(Verified by kimi-k3 + glm-5.3 against the SDK source.)* | `@agentclientprotocol/sdk` 0.19.2 |
| F15 | **OQ-B2 closed:** Kimchi's `session/new` always advertises the `model` config option and implements `session/set_config_option` (plus legacy `models.availableModels`) — Hermes' model-selection flow works end-to-end. Live ids are provider-prefixed (`kimchi-dev/...`, `openai-codex/...` — the harness's multi-provider registry). `auto` is the harness's router mode and `auto-beta` a real catalog model: **no content filtering** (user decision 2026-09-25, retracting the reviewers' pseudo-entry caveat — `multi-model` never appeared live) | `server.ts:627` + live probe 2026-09-25 |
| F16 | Hermes user has a managed Hermes install locally (`~/.hermes/hermes-agent@d5785bb`, verified byte-identical to upstream for the files this spec relies on) | user confirmation + reviewer verification |
| F17 | **OQ-A1 resolved live (2026-09-25):** the metadata endpoint returns `{"models": [{slug, provider, tool_call, deprecated_at, limits.context_window, ...}]}` — 20 items, none with `id`/`model`/`name` keys; model ids come from `slug`. The gateway WAF returns **403 when `Accept: application/json` is absent** (both headers the plugin already sends). Full fetch verified inside Hermes' own venv: 20 models | live probes + commit d45f400 |

## 3. Spec A — `kimchi` (API-key model provider)

### Profile

```python
ProviderProfile(
    name="kimchi",
    aliases=("kimchi-dev",),
    display_name="Kimchi",
    description="Kimchi (kimchi.dev) — agentic models via OpenAI-compatible API",
    signup_url="https://app.kimchi.dev",
    env_vars=("KIMCHI_API_KEY", "KIMCHI_BASE_URL"),
    base_url="https://llm.kimchi.dev/openai/v1",   # F7; KIMCHI_BASE_URL overrides
    models_url="https://llm.kimchi.dev/v1/models/metadata?include_in_cli=true",  # F9
    auth_type="api_key",
    fallback_models=(),   # live catalog only — user decision
    default_headers={"User-Agent": "hermes-agent/<hermes-version> (kimchi-plugin)"},
)
```

### Behavior

- **Auth resolution** is Hermes' built-in api-key ladder: `KIMCHI_API_KEY`
  env → `~/.hermes/.env` → setup-wizard prompt (`hermes model`). No custom
  auth code in v1. Bridging from Kimchi's own `~/.config/kimchi/config.json`
  is a documented one-liner in README, not plugin code.
- **Catalog**: `fetch_models()` targets `models_url` (F9). If the metadata
  response shape is not OpenAI's `{"data":[{"id":…}]}` (OQ-A1), override
  `fetch_models()` with a shape adapter. Empty `fallback_models` per user
  decision — a transient catalog failure means an empty picker until
  recovery (accepted consequence; OQ-A1 is load-bearing).
- **Doctor**: free health check from `auth_type="api_key"` + `supports_health_check=True`.

### Acceptance criteria

1. `hermes model` lists "Kimchi"; completing setup stores the key in `~/.hermes/.env`.
2. `/model kimchi:<id>` lists live models when the key is valid (correct catalog URL + shape).
3. `hermes doctor` passes the Kimchi health probe with a valid key.
4. One real agent turn completes against `llm.kimchi.dev`.

### Open questions (hypotheses to verify)

- **OQ-A1 — RESOLVED (F17).** Recorded live shape handled by `_lenient_model_ids` (`slug` ids, retired-model filtering via `deprecated_at`); regression test captures the recorded shape.
- **OQ-A2 — partially answered:** a default `reasoning_effort: medium` turn on `glm-5.3-flash` succeeded with no 400 (2026-09-25). Full per-model vocabulary still unverified; add `build_api_kwargs_extras` only if a live turn needs it.
- **OQ-A3** Aux-model choice for compression/vision (default: none → Hermes uses main model). *Learn by: usage; pin later if needed.*

## 4. Spec B — `kimchi-acp` (ACP external-process provider)

### Profile

```python
class KimchiACPProfile(ProviderProfile):
    def create_client(self, **client_kwargs):
        from agent.copilot_acp_client import CopilotACPClient
        return _KimchiBrandedACPClient(**client_kwargs)   # thin subclass; see below

    def fetch_models(self, *, api_key=None, base_url=None, timeout=15.0):
        # session/new probe → model ids advertised by the Kimchi harness
        # (F13 pattern), filtering pseudo-entries ("multi-model", "auto", F15).
        # None → picker falls back.

    def setup_status(self, **kwargs):
        # {available: shutil.which("kimchi") is not None,
        #  logged_in: ~/.config/kimchi/config.json has non-empty apiKey,
        #  login_command: "kimchi login"}

kimchi_acp = KimchiACPProfile(
    name="kimchi-acp", aliases=("kimchi-agent",),
    display_name="Kimchi (Harness via ACP)",
    api_mode="chat_completions",
    env_vars=(),                       # subprocess owns auth (F11 pattern)
    base_url="acp://kimchi",
    auth_type="external_process",
    process_command="kimchi",
    process_args=("--mode", "acp"),   # prompts stay on — --yolo is opt-in
    process_command_env_vars=("KIMCHI_ACP_COMMAND",),
    process_args_env_var="KIMCHI_ACP_ARGS",
    # NOTE (review finding): KIMCHI_ACP_ARGS="" does NOT clear the args — an
    # empty env var falls back to process_args (F11). The YOLO opt-in is:
    # KIMCHI_ACP_ARGS="--mode acp --yolo" (catalog review 2026-10-06).
)
```

- **`_KimchiBrandedACPClient`** (thin subclass of `CopilotACPClient`):
  rewrites Copilot-branded error strings ("Copilot ACP", "Install GitHub
  Copilot CLI") to Kimchi-specific guidance, since the reused client's
  failure paths otherwise mislead (review finding). If subclassing proves
  invasive (errors raised deep in private methods), fall back to documenting
  the branding gap in README — decision deferred to implementation, either
  outcome acceptable for v1.

### Behavior

- **Turn flow**: per request, Hermes spawns `kimchi --mode acp`,
  sends `initialize` (protocolVersion 1 — compatible, F14) + `session/new`,
  applies the requested model via `session/set_config_option` (F15), then
  sends the conversation + Hermes toolset as **one prompt** (F12 semantics).
  The Kimchi harness runs its internal loop; Hermes receives the result
  **after the turn completes** and fake-chunks it — there is **no true
  token streaming** on this path (review finding; AC-2 reworded
  accordingly).
- **Auth**: owned by the subprocess (Kimchi's own credential store, F8).
  Hermes never handles a key on this path. Whether an exported
  `KIMCHI_API_KEY` actually reaches the child is **unverified** —
  `hermes_subprocess_env` may strip it (review finding; probe in e2e, OQ-B6).
- **Permissions**: the default spawn keeps Kimchi's tool-permission gate
  ON; with no human channel in Hermes' shim, `session/request_permission`
  requests are auto-cancelled (F12) — fail-safe denial, documented gap
  (README #1) — so approval-gated tools don't run. YOLO, the harness's
  no-restrictions mode that turns the gate off entirely (F3), is
  opt-in: `KIMCHI_ACP_ARGS="--mode acp --yolo"`.
- **Project trust (LLM-3628, harness #1266, 2026-09-28)**: headless ACP
  sessions resolve project trust fail-closed — an undecided project with
  trust-requiring resources starts untrusted and silently drops project
  skills/config/`.pi` settings. Hermes' shim cannot answer the harness's
  `_kimchi.dev/set_project_trust` ext method, so the drop persists on the
  `kimchi-acp` path (README #9); recovery is an interactive `kimchi` run
  in the project or `defaultProjectTrust: "always"`. YOLO does not bypass
  trust.
- **Keyless spawn**: if Kimchi has no stored credential, the error surfaces
  Kimchi's "Call session/authenticate" hint, which Hermes' shim cannot act
  on. Setup/doc must point users at `kimchi login` as the recovery path
  (review finding).
- **Images**: silently dropped by the conversation-flattening shim (F12).
  Vision through `kimchi-acp` is not supported in v1 (README #4).
- **Performance**: every request = one harness cold start (process spawn +
  initialize + session/new). Acceptable for v1; documented (README #5).

### Acceptance criteria

1. With kimchi installed + logged in, `hermes model` shows "Kimchi (Harness via ACP)"; setup gates on login status (offers `kimchi login`); model picker lists real model ids (pseudo-entries filtered).
2. `/model kimchi-acp` runs a turn to completion; text result arrives (after the harness finishes — no incremental streaming); no crash.
3. Without kimchi installed or logged in, setup reports actionable guidance (`kimchi login` / install), no crash, no Copilot-branded text.
4. `KIMCHI_ACP_ARGS="--mode acp --yolo"` (YOLO opt-in) spawn path works — permission requests are suppressed by the harness; without YOLO they are auto-cancelled by the shim (documented gap) rather than crashing.
5. Error surfaces (spawn failure, timeout, missing CLI) name Kimchi, not Copilot, to the extent the wrapper achieves.

### Open questions (hypotheses to verify)

- **OQ-B4 - RESOLVED (2026-09-25, decisive probe in `probes/acp_tool_execution_probe.py`, kimchi 1.1.35):** the harness **executes its own tools for real** over ACP in YOLO mode (now an opt-in via `KIMCHI_ACP_ARGS="--mode acp --yolo"`) - live `tool_call` session updates observed (write + shell verify), filesystem artifact created and verified. Three-part verdict: (1) harness-side execution is real and survives the shim's text-emission preamble; (2) that execution is **invisible to Hermes** (the shim only forwards text chunks, so Hermes' transcript/UI carry no tool records - this caused the "did you do it?" self-doubt loop observed in e2e); (3) Hermes' forwarded toolset is effectively unused - the harness prefers its own tools. Double-execution (Hermes re-running extracted text blocks) was **not observed** - residual risk noted, not eliminated.
  **ADDRESSED in the plugin (5b5362b):** `KimchiACPClient._handle_server_message` renders one markdown bullet per completed/failed tool (`- ⚙ **web_search** ✓ — excerpt`) into the visible text stream — pending/in_progress churn suppressed, adjacent duplicates collapsed, bullet block closed before narrative — tool activity shows in Hermes' UI AND reaches later turns' flattened context, so the model can verify its own prior work. Residual: text lines, not Hermes' native rich tool cards (upstream improvement); raw tool I/O still not forwarded.
- **OQ-B3 - RESOLVED empirically:** in a tool-executing YOLO probe, **zero `session/request_permission` traffic** fired - YOLO suppresses tool-permission prompting as designed (YOLO is now opt-in; under the prompt-on default the shim auto-cancels requests, README #1). The non-tool confirm/elicitation fallback path remains unexercised (residual unknown, low stakes).
- **OQ-B5** Long YOLO agentic turns (opt-in via `KIMCHI_ACP_ARGS="--mode acp --yolo"`) vs the client's default 900 s whole-session timeout — do real turns fit? What's the right override? *Learn by: timing real workloads; if insufficient, wrap timeout construction in the subclass.*
- **OQ-B6** Does `KIMCHI_API_KEY` survive `hermes_subprocess_env`'s secret blocklist into the spawned harness? *Learn by: e2e probe with env key set and empty config.json.*

## 5. Delivery & process

- Repo: this one. `install.sh` syncs `model-providers/*` → `~/.hermes/plugins/model-providers/`. Uninstall = delete the two dirs. **`install.sh` is a plain copy — re-run it after every plugin change** (a stale installed copy caused the 0-models incident on 2026-09-25; upstream discovery does not watch files).
- Implementation in thin slices, one clear commit per slice; each slice updates this spec where implementation taught something (spec-maintenance discipline).
- Reviews before implementation: kimi-k3 + glm-5.3 (done, incorporated), then the user (plan gate). Implementation starts only after user approval.
- Tests: hermetic pytest unit tests for profile registration/fields + the catalog shape adapter (mocked HTTP) + pseudo-entry filtering; manual e2e checklist per layer against the local Hermes install (F16) and local `kimchi` build. Live probes marked "needs KIMCHI_API_KEY" are HITL items.

## 6. Decision log

| Decision | Rationale / owner |
|---|---|
| ~~YOLO is the default spawn mode for kimchi-acp~~ → **Reversed 2026-10-06** (catalog review): the default spawn is `--mode acp` with harness permission prompts on (shim cancels them fail-safe); YOLO is opt-in via `KIMCHI_ACP_ARGS="--mode acp --yolo"`. Original rationale (user decision 2026-09-25): unsupervised in-harness tool execution accepted for personal use — reviewer override: too dangerous as a catalog default for gateway/cron contexts |
| `fallback_models=()` — live catalog only | User decision 2026-09-25; accepted consequence: transient catalog failure = empty picker (OQ-A1 load-bearing) |
| Reuse Hermes' `CopilotACPClient` + thin branding/error subclass rather than a custom ACP client | Ours: ~300 LOC saved; both reviewers judged reuse mechanically sound (note-level). Gaps (fake streaming, dropped images, cancelled permission requests, branded errors) documented; revisit if OQ-B4 forces it |
| Close OQ-B1/B2 as verified facts (F14/F15) instead of e2e items | Both reviewers independently verified statically; saves e2e budget |
| Both layers implemented in parallel | User decision 2026-09-25 |
| Ship as user-level plugins first; upstream PR deferred | Upstream policy trend toward standalone plugins (`CONTRIBUTING.md`); confirm with maintainers before any bundled-provider PR |
| Naming: `kimchi` (API) + `kimchi-acp` (agent) | Mirrors upstream convention (`kimi-coding`, `copilot-acp`) |
| No pseudo-entry filtering in the ACP model picker | User decision 2026-09-25, overriding the reviewers' caveat: live evidence shows `auto` (harness router mode) and `auto-beta` (real model); `multi-model` never appeared live. Filtering only risked hiding real selections |
