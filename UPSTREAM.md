# Upstream submission — catalog path

How to land Kimchi provider support in
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).
**Decision (2026-10-05): standalone repo + curated plugin catalog** —
the former "Path B". The placement question
([#126026](https://github.com/NousResearch/hermes-agent/issues/126026))
was answered by upstream's own repo state — evidence below. Full
decision log lives in [`SPEC.md`](SPEC.md).

**Status (2026-10-05): SUBMITTED** — catalog PRs
[#133165](https://github.com/NousResearch/hermes-agent/pull/133165)
(`kimchi-provider`) and
[#133166](https://github.com/NousResearch/hermes-agent/pull/133166)
(`kimchi-acp-provider`) are open; `main` and tag `v1.0.0` are pushed;
the loop on #126026 is closed
([comment](https://github.com/NousResearch/hermes-agent/issues/126026#issuecomment-5989285234)).
Remaining: watch the catalog validation actions, respond to review,
promote in Discord.

## Why standalone — the evidence (upstream `main` @ `c2346276`, 2026-10-05)

1. **The in-tree precedent inverted.** `telnyx` and `kiro` — the two
   providers this file once cited as in-tree precedent — are not in
   `plugins/model-providers/` at all. They ship as catalog entries:
   `plugin-catalog/telnyx-provider.yaml`, `plugin-catalog/kiro-provider.yaml`,
   and `plugin-catalog/kiro-acp.yaml` (an ACP entry — our exact shape).
2. **The in-tree provider set is frozen.** `plugins/model-providers/`
   is byte-identical between the staged branch's base (`d5785bb5`) and
   current `main` — zero providers added or removed across ~6,650
   commits while `plugin-catalog/` grew to hundreds of entries.
3. **CONTRIBUTING.md closes the category.** "any plugin that integrates
   someone else's product or project … These do not land in this repo."
   A vendor model-provider plugin is squarely that; the rewrite since
   `d5785bb5` also added explicit catalog-submission guidance.
4. `kiro-acp` proves ACP-provider plugins are a first-class catalog
   category (`category: models`).

The prepared in-tree branch (`feat/kimchi-providers`, commits
`037b20f410`, `35b385646c` — the first was rebased from the originally
recorded `5224c91365`) is **shelved, not deleted**. Revival procedure is
at the bottom of this file.

## Staged materials

| What | Where |
|---|---|
| Catalog entry — `kimchi-provider` | [`upstream/plugin-catalog/kimchi-provider.yaml`](upstream/plugin-catalog/kimchi-provider.yaml) |
| Catalog entry — `kimchi-acp-provider` | [`upstream/plugin-catalog/kimchi-acp-provider.yaml`](upstream/plugin-catalog/kimchi-acp-provider.yaml) |
| Pinned SHA (both entries) | `f3da18f16dff7220c909227f687b5885ab729f66` — the commit adding the per-plugin READMEs the catalog page renders |
| Per-plugin READMEs (rule 13 disclosures) | `model-providers/kimchi/README.md`, `model-providers/kimchi-acp/README.md` |
| Placement issue + closing comment | [#126026 (comment)](https://github.com/NousResearch/hermes-agent/issues/126026#issuecomment-5989285234) |
| PR body — `kimchi-provider` | [`upstream/PR-catalog-kimchi-provider.md`](upstream/PR-catalog-kimchi-provider.md) |
| PR body — `kimchi-acp-provider` | [`upstream/PR-catalog-kimchi-acp-provider.md`](upstream/PR-catalog-kimchi-acp-provider.md) |
| Upstream repo (local clone) | `~/.hermes/hermes-agent` |

## Submission checklist

- [x] Repo public — this repo is already `PUBLIC` (the old "flip"
      item was stale; verified via `gh repo view` 2026-10-05)
- [x] Secrets audit clean (2026-09-29; re-verified 2026-10-05 — no
      keys, tokens, private keys, embedded creds, internal IPs in the
      tree or full history; the committer Gmail in commit metadata is
      the only personal data — accepted)
- [x] `hermes plugins validate` both plugins — green incl. security
      scan ("Validation passed", 2026-10-05)
- [x] `hermes plugins doctor` both plugins — green (runtime
      discovery, import, registration)
- [x] Per-plugin READMEs with rule-13 disclosures (catalog page
      renders the README from the subdir at the pinned SHA)
- [x] Entries drafted against the verified schema, capabilities
      matching reality (rule 6)
- [x] Push `main` (contains the pinned commit) — done 2026-10-05
      (`98ff317..3e419d2`)
- [x] Tag `v1.0.0` on the pinned commit — hygiene only; the catalog
      does **not** require tags ("`version` … is cosmetic … the sha
      stays the release")
- [x] Open PR #1: `plugin-catalog/kimchi-provider.yaml` — one entry
      file per PR, from a fork branch off upstream `main` →
      [#133165](https://github.com/NousResearch/hermes-agent/pull/133165)
- [x] Open PR #2: `plugin-catalog/kimchi-acp-provider.yaml` →
      [#133166](https://github.com/NousResearch/hermes-agent/pull/133166)
- [x] PR bodies carry the rule-13 disclosure lines (below)
- [ ] Catalog validation action green on both PRs; respond to review
      (SHA bumps later = new PR + `version` bump in the same PR)
- [x] Close the loop on #126026 with a comment linking the entries
      ([posted](https://github.com/NousResearch/hermes-agent/issues/126026#issuecomment-5989285234))
- [ ] Promote in the Nous Research Discord
      [`#plugins-skills-and-skins`](https://discord.gg/NousResearch)

## Disclosure lines for the PR bodies (rule 13)

- `kimchi-provider`: fetches the live model catalog from
  `llm.kimchi.dev` with the user's API key (Hermes' credentialed-URL
  wrapper); inference goes through Hermes core's own client. No
  credentials stored by the plugin.
- `kimchi-acp-provider`: spawns `kimchi --mode acp` per turn — the
  harness keeps its own permission prompts (shim cancels them fail-safe;
  YOLO opt-in via `KIMCHI_ACP_ARGS="--mode acp --yolo"`); reads the
  Kimchi CLI's own
  `~/.config/kimchi/config.json` (key **presence** only) for setup
  status; the subprocess owns auth — no key is shared with Hermes;
  renders completed tool calls as bullets in the reply.

## Entry schema notes (verified against `plugin-catalog/README.md` @ `c2346276`)

- `name` **must equal the plugin manifest `name:`** — `kimchi-provider`
  and `kimchi-acp-provider` (not `kimchi-acp`); `[a-z0-9_-]{1,64}`.
- `sha` — exact 40-hex commit; branches, tags, and short SHAs are
  rejected by the loader. Installs clone and check out exactly it.
- `subdir` — plain relative path (`model-providers/kimchi` …); the
  docs page fetches the README **from the subdir** at the pinned SHA.
- `tier: community`, `category: models` — matches telnyx/kiro
  precedent; `maintainer: getkimchi` (the org; gives the entry a
  `/docs/plugins/by/getkimchi` page).
- `requires_hermes: ">=0.21.5"` — the version both plugins were
  verified against; truthful floor, never newer than the current
  release (the loader skips the plugin otherwise).
- `capabilities` — must match the pinned commit (rule 6): no tools,
  hooks, or middleware; `requires_env: [KIMCHI_API_KEY]` for the
  API-key layer, `[]` for ACP (subprocess owns auth).
- `version: "1.0.0"` — cosmetic label; keep synced with `plugin.yaml`
  and the pinned code (bump in the same PR as any SHA bump).

## Verification & monitoring commands

```bash
# Admission gates (both green 2026-10-05)
hermes plugins validate model-providers/kimchi
hermes plugins validate model-providers/kimchi-acp
hermes plugins doctor model-providers/kimchi
hermes plugins doctor model-providers/kimchi-acp

# Watch the placement issue
gh issue view 126026 --repo NousResearch/hermes-agent --json state,comments

# Confirm the pinned commit is what upstream will clone
git rev-parse f3da18f16dff7220c909227f687b5885ab729f66
git ls-tree f3da18f16dff7220c909227f687b5885ab729f66 model-providers/
```

## Retired: the in-tree path (old "Path A")

Preserved for the record. The prepared branch `feat/kimchi-providers`
lives in `~/.hermes/hermes-agent` (pushed to fork
`zilvinasu/hermes-agent`). If a maintainer ever answers #126026 with
"in-tree": rebase onto `origin/main` (~6,650 commits drifted; the
conflict surface is small — only `.env.example` and
`website/docs/integrations/providers.md` overlap), then
`scripts/run_tests.sh tests/plugins/model_providers tests/providers`
(expect 32 files / 332 tests green), `scripts/check-windows-footguns.py`,
`ruff check .`, and paste [`upstream/PR.md`](upstream/PR.md). Both
providers ship together — one logical change.

Upstream dev-environment notes (for future upstream work): Python
`>=3.14,<3.15` via the PM developer workflow (`source ./activate`), Node
per root `package.json` engines, canonical runner
`scripts/run_tests.sh`, JS workspaces via `npm ci` (website separately).
Do not run raw pip/uv inside PM-built environments.
