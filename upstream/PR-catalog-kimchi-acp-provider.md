## What does this PR do?

Adds `kimchi-acp-provider` to the curated plugin catalog — a model
provider (`category: models`, `tier: community`) that drives the full
[Kimchi](https://kimchi.dev) coding harness over ACP stdio: Hermes
spawns `kimchi --mode acp` and the harness serves each turn with its
own tools. The default spawn keeps the harness's permission prompts on;
YOLO (no approval prompts) is opt-in via `KIMCHI_ACP_ARGS` — per the
catalog review, mirroring Hermes' bundled `copilot-acp`.

Companion to #133165 (`kimchi-provider`, the API-key layer from the
same repo). Opened as a separate PR per the one-entry-file-per-PR
convention.

Standalone-repo submission per the catalog policy: the plugin lives at
https://github.com/getkimchi/kimchi-hermes (public), subdir
`model-providers/kimchi-acp`, pinned to the exact commit
`f3da18f16dff7220c909227f687b5885ab729f66` (the commit that adds the
plugin README rendered on `/docs/plugins/kimchi-acp-provider`).

## Related Issue

Placement context (not a fix — deliberately left open for maintainers):
#126026 asked whether a third-party model provider belongs in-tree or
standalone. These entries follow the standalone pattern the catalog
already established for vendor providers (telnyx, kiro — including the
ACP-shaped `kiro-acp`).

## Type of Change

- [x] 📝 Documentation update

## Changes Made

- `plugin-catalog/kimchi-acp-provider.yaml` — new entry pinned to
  `getkimchi/kimchi-hermes@f3da18f16dff7220c909227f687b5885ab729f66`
  (re-pinned to the review-fix commit at submission of this update)
- Review fixes applied to the plugin at the pinned SHA (see
  [`model-providers/kimchi-acp`](https://github.com/getkimchi/kimchi-hermes/tree/main/model-providers/kimchi-acp)):
  the `--yolo` no-restrictions spawn flag is no longer the default —
  the harness keeps its permission prompts unless the user opts in via
  `KIMCHI_ACP_ARGS="--mode acp --yolo"`; and the key-presence disclosure
  now states the config is parsed to check that a stored key is
  present, never stored or sent.

## How to Test

1. `hermes plugins validate` / `validate --install-deps` on the plugin
   at the pinned SHA — clean (no Python dependencies declared)
2. After merge: `hermes plugins install kimchi-acp-provider`, then
   `hermes model` shows "Kimchi (Harness via ACP)" with the live
   session-advertised model catalog; a tool-using turn shows harness
   tool activity as inline bullets in the reply
3. Verified pre-submission on macOS 15 (arm64) with Hermes 0.21.5 and
   Kimchi 1.1.35: `hermes plugins validate` and
   `hermes plugins doctor` both pass; harness-native tool execution
   over ACP verified end-to-end by probe (filesystem artifact check)

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow Conventional Commits (`catalog: add ...`)
- [x] I searched for existing PRs to make sure this isn't a duplicate
- [x] My PR contains only changes related to this feature (one YAML file)
- [x] `pytest tests/ -q` — N/A (no code changed; the catalog validation
      action covers the entry)
- [x] `python scripts/check` — N/A (no code changed)
- [x] I've added tests for my changes — N/A (catalog entry)
- [x] I've tested on my platform: macOS 15, arm64

### Documentation & Housekeeping

- [x] I've updated relevant documentation — the entry itself; the
      plugin README at the pinned SHA renders on the plugin page
- [x] `cli-config.yaml.example` — N/A
- [x] `CONTRIBUTING.md` / `AGENTS.md` — N/A
- [x] Cross-platform impact — N/A (pure-Python provider profile; the
      spawned CLI is resolved via PATH / `KIMCHI_ACP_COMMAND`)
- [x] Tool descriptions/schemas — N/A

## Screenshots / Logs

Disclosure lines per the admission rules (also in the plugin README at
the pinned SHA):

- **Subprocess**: every turn spawns `kimchi --mode acp` and
  speaks JSON-RPC over stdio; the process is terminated when the turn
  ends. By default the harness keeps its own tool-permission prompts;
  because Hermes' ACP shim has no human approval channel yet, those
  requests are cancelled fail-safe — so approval-gated tools don't run,
  nothing executes silently. YOLO — Kimchi's no-restrictions permission
  mode, where **harness tools (shell commands, file writes, web
  requests) run without approval prompts** — is **opt-in**:
  `KIMCHI_ACP_ARGS="--mode acp --yolo"` (enable only where unsupervised
  in-harness execution is acceptable, e.g. a personal machine — not
  shared gateway/cron contexts).
- **Reads outside the plugin's own data**: setup status checks whether
  the Kimchi CLI is logged in by reading the Kimchi CLI's own
  `~/.config/kimchi/config.json` — the config is parsed only to check
  that a stored key is present; the key itself is never stored by
  Hermes nor sent anywhere.
- **Auth**: the subprocess owns its own auth (its credential store) —
  no API key is shared with Hermes; `requires_env: []`.
- **Reply rendering**: completed/failed tool calls are rendered as one
  markdown bullet each in the visible reply (churn suppressed).
- Registers only a provider profile; no tools, hooks, or middleware.
- No self-updating code — the SHA pin is the trust model; updates flow
  through SHA-bump PRs here (with a `version` bump in the same PR).
