# Upstream submission — action items

How to land Kimchi provider support in
[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent),
as a checklist. Status snapshot and the full decision log live in
[`SPEC.md`](SPEC.md); the prepared materials are
[`upstream/ISSUE.md`](upstream/ISSUE.md) and
[`upstream/PR.md`](upstream/PR.md).

**Status (2026-09-29):** issue
[#126026](https://github.com/NousResearch/hermes-agent/issues/126026) is
OPEN with no maintainer response yet. Everything else is staged.

## Staged materials & pointers

| What | Where |
|---|---|
| Upstream issue (placement question) | https://github.com/NousResearch/hermes-agent/issues/126026 |
| Upstream repo (local clone) | `~/.hermes/hermes-agent` |
| Prepared PR branch | `feat/kimchi-providers` — commits `5224c91365`, `35b385646c`, pushed to fork `zilvinasu/hermes-agent` |
| PR body (template-following, `Fixes #126026`) | [`upstream/PR.md`](upstream/PR.md) |
| Issue text as filed | [`upstream/ISSUE.md`](upstream/ISSUE.md) |
| Their contribution guide | `~/.hermes/hermes-agent/CONTRIBUTING.md` (1020 lines; the two load-bearing sections: *Memory Providers: Ship as a Standalone Plugin* and *Third-Party Product Integrations: Ship as a Standalone Plugin*) |
| Their PR template | `~/.hermes/hermes-agent/.github/pull_request_template.md` (CI auto-labels from its checklist) |
| Catalog admission docs | `website/docs/user-guide/features/plugin-catalog.md` § *Submitting a plugin to the catalog* + the [`plugin-catalog/` README](https://github.com/NousResearch/hermes-agent/tree/main/plugin-catalog) (authoritative entry schema) |
| Plugin manifest used by the installer | this repo's `model-providers/*/plugin.yaml` — includes `requires_env` (masked install-time key prompt → `~/.hermes/.env`) |

## Verification & monitoring commands

```bash
# Watch the placement answer
gh issue view 126026 --repo NousResearch/hermes-agent --json state,comments

# Re-verify the staged branch against upstream main
cd ~/.hermes/hermes-agent && git checkout feat/kimchi-providers && git rebase origin/main
scripts/run_tests.sh tests/plugins/model_providers tests/providers   # hermetic, CI parity
scripts/check-windows-footguns.py   # grep-based, cheap, CI runs it too
ruff check .

# Validate plugin manifests the way the catalog gate will
hermes plugins validate model-providers/kimchi
hermes plugins validate model-providers/kimchi-acp
hermes plugins doctor model-providers/kimchi   # real-runtime contract check
```

---

## The one decision everything hangs on

Hermes' contribution policy closes in-tree **third-party product
integrations** ("PRs that add such a directory under `plugins/` will be
closed with a pointer to publish it as its own repo" — CONTRIBUTING.md,
*Third-Party Product Integrations*). Whether **model providers** are in
that closed category is exactly what issue #126026 asks: in-tree providers
telnyx/kiro exist as precedent, and the memory-provider closure shows the
pattern for closing categories. **Do not open the PR until a maintainer
answers the placement question** — a premature in-tree PR is likely to be
closed on policy, not quality.

Monitor: watch #126026 (subscribe on GitHub), or check
`gh issue view 126026 --repo NousResearch/hermes-agent`.

## Path A — maintainer says in-tree (telnyx/kiro precedent holds)

- [ ] Open the PR from the prepared branch: `feat/kimchi-providers`
      already exists in `~/.hermes/hermes-agent` (commits `5224c91365`,
      `35b385646c`) and is pushed to the fork `zilvinasu/hermes-agent`.
- [ ] Paste `upstream/PR.md` body as-is (it follows their PR template,
      `Fixes #126026`). One logical change — both providers ship together.
- [ ] Re-verify before opening (code may have moved upstream):
      `scripts/run_tests.sh tests/plugins/model_providers tests/providers`
      → expect 32 files, 332 tests green.
- [ ] Re-run `scripts/check-windows-footguns.py` and `ruff check` on the
      diff (`providers/**` is ruff-relaxed for PLW1514 only; ASYNC gates
      still apply).
- [ ] Respond to review; expect the "salvage" landing pattern (maintainers
      may rework/absorb the change — do not force-push over their edits).
- [ ] If the fork branch goes stale while waiting: rebase onto upstream
      `main`, re-run the hermetic suite, force-push **the fork branch
      only** (never upstream).

## Path B — maintainer says standalone (the documented default)

- [ ] **Flip this repo to public** (required: catalog admits public repos
      only). Secrets audit is already done and clean (see commit history,
      2026-09-29) — re-run a scan before flipping anyway.
- [ ] **Create real releases/tags** (e.g. `v1.0.0` from `main`). The
      catalog requires released tags, not just a default branch.
- [ ] Restructure if the maintainers' standalone pattern (kiro/telnyx
      migration layout) suggests a different dir shape — otherwise the
      current `model-providers/<name>/` layout already matches Hermes'
      plugin discovery (`~/.hermes/plugins/model-providers/`).
- [ ] **Curated catalog submission**: one PR per entry against
      NousResearch/hermes-agent adding `plugin-catalog/<name>.yaml`
      (one for `kimchi-provider`, one for `kimchi-acp`). Requirements
      (plugin-catalog README + docs):
  - [ ] owner-submitted (you own the plugin repo) ✓ (will be)
  - [ ] `repo` URL publicly cloneable ← needs the flip
  - [ ] released tags exist ← needs the release step
  - [ ] catalog validation GitHub Action green on the PR (schema, SHA
        format, reachability)
  - [ ] **pinned commit SHA** — the catalog installs exactly one immutable
        40-char SHA; never self-updating. Updates = SHA-bump PR + bump
        `version` in the same PR so the label matches the code.
  - [ ] optional: `screenshots:` in the entry fills the plugin page
        (`/docs/plugins/<name>`).
- [ ] After merge: users install via `hermes plugins install kimchi-provider`
      (catalog name), and updates flow through `hermes plugins update` +
      your SHA-bump PRs.
- [ ] **Promote** in the Nous Research Discord
      [`#plugins-skills-and-skins`](https://discord.gg/NousResearch) —
      the documented discovery channel for standalone plugins.
- [ ] Close the loop on #126026 with a comment pointing at the standalone
      repo + catalog entries (helps the next third-party provider author).

## Either path — follow-ups

- [ ] If Hermes lacks a capability the plugin needs (e.g. relaying ACP
      permission prompts into the approval UI), file it as a feature
      request to **widen the generic plugin surface** — CONTRIBUTING.md
      explicitly prefers this over special-casing a plugin in core.
- [ ] Candidate: generic ACP shim upgrade (native tool-event rendering for
      all external-process providers, true streaming, image passthrough).
- [ ] Keep `SPEC.md` evidence table and this checklist current as the
      upstream policy evolves.

---

## Contribution guidelines compliance (what reviewers will check)

Already satisfied by the staged work — re-verify at PR time:

| Guideline (CONTRIBUTING.md / PR template) | Status |
|---|---|
| Conventional Commits (`feat(scope):`, `fix(scope):`) | ✓ staged branch uses them |
| Branch naming (`feat/description`) | ✓ `feat/kimchi-providers` |
| Hermetic test runner `scripts/run_tests.sh` (CI parity; clears creds, isolates `HERMES_HOME`, per-file subprocesses) | ✓ 32 files / 332 tests green |
| Tests for changes, co-located, no live network in CI env | ✓ 19 new tests, all mocked |
| `scripts/check-windows-footguns.py` clean | ✓ run on the diff |
| Ruff clean (PLW1514 exemption is `providers/**`-only; ASYNC gates apply) | ✓ |
| Cross-platform (no `os.kill(pid,0)`, `shutil.which` before shelling out, `pathlib` paths) | ✓ providers comply |
| PR template checklist (Code + Documentation & Housekeeping sections) | ✓ pre-filled in `upstream/PR.md` |
| One logical change per PR; no unrelated commits | ✓ both providers = one feature |
| Search-first (no duplicate PRs/issues) | ✓ done when the issue was filed |
| Dependency pinning (`<next_major` upper bounds; no new deps added) | ✓ zero new dependencies |
| Error messages name cause + remediation (never symptom-only) | ✓ subclass rewrites Copilot-branded shim errors to Kimchi guidance |
| No secrets in logs; `.env.example` additions in an isolated commented block | ✓ |
| Docs updated (providers page, `.env.example` block) | ✓ in staged branch |
| Tested on your platform (macOS 15 arm64, TUI + Desktop) | ✓ |
| MIT license agreement for contributions | ✓ (by opening the PR) |

Upstream dev-environment notes (for future upstream work): Python
`>=3.14,<3.15` via the PM developer workflow (`source ./activate`), Node
per root `package.json` engines, canonical runner
`scripts/run_tests.sh`, JS workspaces via `npm ci` (website separately).
Do not run raw pip/uv inside PM-built environments.

---

## Curated catalog entry, concretely

`plugin-catalog/kimchi-provider.yaml` (schema per the
[plugin-catalog README](https://github.com/NousResearch/hermes-agent/tree/main/plugin-catalog)):

```yaml
name: kimchi-provider        # exact plugin manifest name
repo: https://github.com/getkimchi/kimchi-hermes
subdir: model-providers/kimchi   # monorepo: catalog entries carry subdir (repo#subdir)
sha: <40-char commit SHA>        # the immutable pin; bump = new PR + version bump
version: 1.0.0                   # matches the pinned plugin.yaml version
description: Kimchi (kimchi.dev) models via OpenAI-compatible API
# screenshots: [...]             # optional, fills /docs/plugins/<name>
```

Repeat for `subdir: model-providers/kimchi-acp`. The installer resolves
`repo#subdir` natively (`_resolve_git_url`), so monorepo entries are a
first-class pattern — same shape as our README quick-start commands.

> **Caveat:** the YAML above was drafted from the documented schema
> (plugin-catalog docs, 2026-09-29). Catalog tooling evolves — re-check the
> exact field list against the `plugin-catalog/` README on upstream `main`
> **at submission time**, and dry-run with `hermes plugins validate` + the
> catalog validation action before opening the PR. If the field list has
> drifted, trust the README over this file.
