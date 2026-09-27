# Upstream PR draft — from branch `feat/kimchi-providers`

> Open against `NousResearch/hermes-agent:main` AFTER the issue lands a
> maintainer nod. One logical change: both providers ship together as one
> feature (Kimchi support); split into two PRs only if reviewers prefer.

---

**Title:** `feat(providers): add Kimchi (kimchi.dev) API-key and ACP harness providers`

## What

Two new model providers for [Kimchi](https://kimchi.dev/) (Cast AI's coding
agent), plus docs and hermetic tests. No core changes, no new dependencies.

- **`kimchi`** — API-key provider. OpenAI-compatible gateway
  (`https://llm.kimchi.dev/openai/v1`), `KIMCHI_API_KEY` /
  `KIMCHI_BASE_URL` overrides. Model catalog discovered live from Kimchi's
  metadata endpoint (`/v1/models/metadata?include_in_cli=true` — ids under
  `slug`, retired models filtered via `deprecated_at`); no hardcoded
  fallback list, matching the live-catalog pattern.
- **`kimchi-acp`** — external-process ACP provider driving the local Kimchi
  CLI (`kimchi --mode acp --yolo` by default; `KIMCHI_ACP_ARGS` /
  `KIMCHI_ACP_COMMAND` overrides). The subprocess owns its own auth — Hermes
  never handles a key on this path (same contract as `copilot-acp`).
  Tool activity from the harness is rendered into the visible reply as
  markdown bullets (the shim otherwise drops `tool_call` session updates,
  making harness-native execution invisible in Hermes' UI and in later
  turns' flattened context).

## Why

Kimchi is Cast AI's coding-agent product with a subscription API; its users
overlap heavily with Hermes' audience. Both integration shapes follow
existing in-tree precedents: API-key providers (≈38 bundled) and ACP
external-process providers (`copilot-acp`). An intro issue with verification
evidence will be linked here before review.

## How to test

```bash
uv pip install -e ".[all,dev]"
scripts/run_tests.sh tests/plugins/model_providers tests/providers
# → 32 files, 332 tests passed (includes 19 new tests)
```

Manual matrix (macOS arm64, managed install):
- `hermes model` → both providers listed with live catalogs
- `hermes chat --provider kimchi --model kimi-k3` — real turn,
  `reasoning_effort` accepted
- `hermes chat --provider kimchi-acp` (Kimchi CLI installed + `kimchi login`)
  — harness runs the turn, tool activity rendered inline; Desktop app
  verified. ACP probe: harness-native tool execution confirmed via
  filesystem artifact; zero permission requests under the default YOLO mode.

## Implementation notes

- Profile-level only: `register_provider()` auto-wires auth, setup wizard,
  doctor, model picker (no core edits).
- The ACP client self-heals its spawn target: some construction paths
  (Desktop/auxiliary rebuilds) don't pass `command`/`args`, and the shim's
  fallback resolves to the copilot CLI — a Kimchi client must always target
  the Kimchi CLI (explicit command/args still respected). Happy to discuss a
  generic fix (thread external-process specs through every construction
  path) as a follow-up.
- The gateway's WAF 403s catalog probes without `Accept: application/json`;
  the profile deliberately does not override the base UA/header set.

## Platforms tested

macOS 15 (arm64). No OS-specific code paths touched: urllib catalog fetch +
the existing ACP subprocess shim.
