## What does this PR do?

Adds `kimchi-provider` to the curated plugin catalog — a model provider
(`category: models`, `tier: community`) for [Kimchi](https://kimchi.dev)
models via the OpenAI-compatible API.

Standalone-repo submission per the catalog policy: the plugin lives at
https://github.com/getkimchi/kimchi-hermes (public), subdir
`model-providers/kimchi`, pinned to the exact commit
`f3da18f16dff7220c909227f687b5885ab729f66` — the commit that adds the
plugin README rendered on `/docs/plugins/kimchi-provider`.

## Related Issue

Placement context (not a fix — deliberately left open for maintainers):
#126026 asked whether a third-party model provider belongs in-tree or
standalone. These entries follow the standalone pattern the catalog
already established for vendor providers (telnyx, kiro).

## Type of Change

- [x] 📝 Documentation update

## Changes Made

- `plugin-catalog/kimchi-provider.yaml` — new entry pinned to
  `getkimchi/kimchi-hermes@f3da18f16dff7220c909227f687b5885ab729f66`

## How to Test

1. `hermes plugins validate` / `validate --install-deps` on the plugin
   at the pinned SHA — clean (no Python dependencies declared)
2. After merge: `hermes plugins search kimchi` lists the entry;
   `hermes plugins install kimchi-provider` installs it and the
   provider registers — `hermes model` shows "Kimchi" with the live
   model catalog
3. Verified pre-submission on macOS 15 (arm64) with Hermes 0.21.5:
   `hermes plugins validate` and `hermes plugins doctor` both pass
   (runtime discovery, import, registration; security scan "safe")

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
- [x] Cross-platform impact — N/A (pure-Python provider profile; no
      platform-specific code)
- [x] Tool descriptions/schemas — N/A

## Screenshots / Logs

Disclosure lines per the admission rules (also in the plugin README at
the pinned SHA):

- **Network**: fetches the live model catalog from
  `llm.kimchi.dev/v1/models/metadata` with the user's API key
  (Authorization header, via Hermes' credentialed-URL wrapper);
  model inference goes through Hermes core's own client.
- **Credentials**: none stored by the plugin — resolved by Hermes'
  built-in env / `~/.hermes/.env` ladder. `requires_env:
  KIMCHI_API_KEY`.
- Registers only a provider profile; no tools, hooks, or middleware.
- No self-updating code — the SHA pin is the trust model; updates flow
  through SHA-bump PRs here (with a `version` bump in the same PR).

A companion entry for the ACP layer (`kimchi-acp-provider`, same repo,
drives the full Kimchi harness over ACP stdio) is being submitted
separately.
