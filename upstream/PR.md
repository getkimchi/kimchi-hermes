# Upstream PR draft — from branch `feat/kimchi-providers`

> Body below follows their `.github/pull_request_template.md` (paste as-is
> when creating the PR). Open AFTER the issue lands a maintainer nod.
> One logical change: both providers ship together as one feature (Kimchi
> support); split into two PRs only if reviewers prefer.

---

## What does this PR do?

Adds first-class support for [Kimchi](https://kimchi.dev/) (Cast AI's coding
agent) as two model providers, plus docs, `.env.example` block, and hermetic
tests. No core changes, no new dependencies.

- **`kimchi`** — API-key provider. OpenAI-compatible gateway
  (`https://llm.kimchi.dev/openai/v1`), `KIMCHI_API_KEY` /
  `KIMCHI_BASE_URL` overrides. Model catalog discovered live from Kimchi's
  metadata endpoint (`/v1/models/metadata?include_in_cli=true` — ids under
  `slug`, retired models filtered via `deprecated_at`); no hardcoded
  fallback list, matching the live-catalog pattern.
- **`kimchi-acp`** — external-process ACP provider driving the local Kimchi
  CLI (`kimchi --mode acp --yolo` by default; `KIMCHI_ACP_ARGS` /
  `KIMCHI_ACP_COMMAND` overrides). The subprocess owns its own auth — Hermes
  never handles a key on this path (same contract as `copilot-acp`). Tool
  activity from the harness is rendered into the visible reply as markdown
  bullets (the shim otherwise drops `tool_call` session updates, making
  harness-native execution invisible in Hermes' UI and in later turns'
  flattened context).

## Related Issue

Fixes #<issue-number> *(intro issue linked here once filed — it carries the
verification evidence and the placement question)*

## Type of Change

- [x] ✨ New feature (non-breaking change that adds functionality)

## Changes Made

- `plugins/model-providers/kimchi/` — API-key provider profile
- `plugins/model-providers/kimchi-acp/` — ACP external-process profile
- `tests/plugins/model_providers/test_kimchi_profile.py` (9 tests)
- `tests/plugins/model_providers/test_kimchi_acp_profile.py` (10 tests)
- `website/docs/integrations/providers.md` — Kimchi section
- `.env.example` — Kimchi provider block

## How to Test

1. `uv pip install -e ".[all,dev]"` then
   `scripts/run_tests.sh tests/plugins/model_providers tests/providers`
   → 32 files, 332 tests passed (19 new)
2. `hermes model` → both providers listed with live catalogs
3. `hermes chat --provider kimchi --model kimi-k3` — real turn
4. `hermes chat --provider kimchi-acp` (Kimchi CLI installed + `kimchi login`)
   — harness runs the turn, tool activity rendered inline; Desktop verified.
   ACP probe: harness-native tool execution confirmed via filesystem
   artifact; zero permission requests under the default YOLO mode.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate (no existing Kimchi provider PRs/issues found)
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [x] I've run `pytest tests/ -q` and all tests pass *(see note: full bare-`pytest` run on this machine shows pre-existing environment-dependent failures in `tests/providers/` that occur with this PR's files removed too; the hermetic `scripts/run_tests.sh` — CI parity — is fully green)*
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: macOS 15 (arm64) — TUI and Desktop

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — providers docs page
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A *(N/A: provider env vars are declared in the profile)*
- [ ] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A *(N/A)*
- [x] I've considered cross-platform impact (Windows, macOS) per the compatibility guide — `scripts/check-windows-footguns.py` clean; `ruff check` clean (PLW1514/ASYNC gates)
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A *(N/A)*

## Implementation notes for reviewers

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
