# Upstream — Hermes plugin catalog (maintenance)

Kimchi's model providers ship through the curated Hermes plugin catalog
([NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent),
`plugin-catalog/`). Both entries are **merged**; any Hermes user can
`hermes plugins install kimchi-provider` / `kimchi-acp-provider`.
Placement question
([#126026](https://github.com/NousResearch/hermes-agent/issues/126026))
was answered by the merge itself — standalone repo + catalog entry, the
route `CONTRIBUTING.md` documents for third-party product integrations
(the issue itself remains open; decision log in
[`SPEC.md`](SPEC.md)).

| Plugin | PR | Pinned SHA |
|---|---|---|
| `kimchi-provider` | [#133165](https://github.com/NousResearch/hermes-agent/pull/133165) (merged 2026-10-06); bump PR [#135599](https://github.com/NousResearch/hermes-agent/pull/135599) (`v1.1.0`: attribution UA, `KIMCHI_BASE_URL` doc) | `0fcca81491ce97449d615754c60f89eff7696a93` |
| `kimchi-acp-provider` | [#133166](https://github.com/NousResearch/hermes-agent/pull/133166) (merged 2026-10-07 as `0c7f6468`) | `d6ffe62876a44605585eaf5c2e3d5214b9e10cb8` — the review fix that made `--yolo` opt-in |

The merged `kimchi-acp-provider` description was expanded by the
maintainer into a fuller disclosure block (subprocess spawn in Hermes's
working directory, prompts-on default, YOLO opt-in "not for shared
gateway or cron use", key-presence-only config parse).

## Updating the plugins (SHA bumps)

The catalog pins an exact commit; a plugin change ships as a new PR
that bumps `sha` (and `version` in the same PR). Procedure:

1. Land the change on kimchi-hermes `main`; note the commit.
2. `hermes plugins validate model-providers/<plugin>` — gate before
   anything upstream-facing.
3. On a fresh fork branch off upstream `main`, update the entry
   (`sha`, `description` if disclosures changed); one entry file per
   PR. Source of truth for the entry:
   [`upstream/plugin-catalog/`](upstream/plugin-catalog/) in this repo.
4. Open the PR against `NousResearch/hermes-agent`; after merge, sync
   the `sha` back into the local `upstream/plugin-catalog/` copy and
   the table above.

Schema rules that bit us once (verified against
`plugin-catalog/README.md` @ `c2346276`): `name` must equal the plugin
manifest `name:`; `sha` is an exact 40-hex commit (branches, tags, and
short SHAs are rejected by the loader); `subdir` is where the docs
page fetches the README from — keep the per-plugin READMEs current
(they carry the rule-13 disclosures); `requires_hermes` is never
newer than the current release (the loader skips the plugin
otherwise).

## Shelved: the in-tree path (old "Path A")

`feat/kimchi-providers` (commits `037b20f410`, `35b385646c`) survives
**only on the fork** `zilvinasu/hermes-agent` — the local branch in
`~/.hermes/hermes-agent` was deleted in the 2026-10-07 cleanup. If a
maintainer ever answers #126026 with "in-tree": rebase onto
`origin/main` (conflict surface is small — `.env.example` and
`website/docs/integrations/providers.md`), then
`scripts/run_tests.sh tests/plugins/model_providers tests/providers`
(expect 32 files / 332 tests green), `scripts/check-windows-footguns.py`,
`ruff check .`, and paste [`upstream/PR.md`](upstream/PR.md). Both
providers ship together — one logical change. Deleting the fork branch
ends this option permanently.

Upstream dev-environment notes: Python `>=3.14,<3.15` via the PM
developer workflow (`source ./activate`), canonical runner
`scripts/run_tests.sh`; do not run raw pip/uv inside PM-built
environments.

Archived submission paperwork: [`upstream/PR.md`](upstream/PR.md),
[`upstream/PR-catalog-kimchi-provider.md`](upstream/PR-catalog-kimchi-provider.md),
[`upstream/PR-catalog-kimchi-acp-provider.md`](upstream/PR-catalog-kimchi-acp-provider.md).
