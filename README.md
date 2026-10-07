# kimchi-hermes

Hermes Agent provider plugins for [Kimchi](https://kimchi.dev):

- **`kimchi`** — API-key model provider. Hermes' own agent loop drives
  Kimchi-served models over the OpenAI-compatible gateway
  (`https://llm.kimchi.dev/openai/v1`).
- **`kimchi-acp`** — ACP external-process provider. Hermes spawns
  `kimchi --mode acp` (YOLO — no approval prompts — is opt-in via
  `KIMCHI_ACP_ARGS="--mode acp --yolo"`) and the **Kimchi harness itself**
  serves the turn over stdio (Agent Client Protocol). This is the primary
  use case.

Both are user-level plugins: they install into
`~/.hermes/plugins/model-providers/` and require no changes to Hermes core.
See [`SPEC.md`](SPEC.md) for the full spec, evidence table, and decision log.

## Quick start

### Prerequisites

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — CLI or Desktop app
- A Kimchi API key — get one at https://app.kimchi.dev
- `kimchi-acp` only: the [Kimchi CLI](https://kimchi.dev) installed and logged in
  (`kimchi login`). The harness subprocess owns its own auth; no key is shared
  with Hermes.

### Install

The repo is a two-plugin monorepo; install one or both layers by path
(run from any directory — the CLI resolves the repo itself):

```bash
# Layer 1 — API-key model provider
hermes plugins install getkimchi/kimchi-hermes/model-providers/kimchi

# Layer 2 — ACP external-process provider (primary use case)
hermes plugins install getkimchi/kimchi-hermes/model-providers/kimchi-acp
```

Pin an exact commit with `--ref <40-char-sha>`; update with
`hermes plugins update`; remove with `hermes plugins remove`.

### Authenticate

```bash
# Layer 1 — put the key where Hermes reads it
export KIMCHI_API_KEY=...          # or persist in ~/.hermes/.env
# (the installer prompts for it automatically if it is not already set)

# Layer 2 — the CLI holds its own credentials
kimchi login
```

### Pick a model and send a turn

```bash
hermes model        # pick "Kimchi" or "Kimchi (Harness via ACP)"
hermes              # say hello — you're on Kimchi
```

Or make it the default in `~/.hermes/config.yaml`:

```yaml
model:
  default: glm-5.3-flash
  provider: kimchi
```

Verify `kimchi-acp` is really driving the harness: tool-using turns show
harness-native activity as inline bullets in the reply
(`- ⚙ **web_search** ✓ — …`).

### Troubleshooting

- **Model picker shows 0 Kimchi models** — the installed copy is stale;
  re-install and restart Hermes (plugin files are not hot-reloaded).
- **Profile-scoped Desktop bots don't see the plugin** — each
  `~/.hermes/profiles/*/` home has separate plugin dirs; use the
  [manual install](#manual--multi-profile-install).
- **ACP spawn fails inside the Desktop app** — GUI apps don't inherit your
  shell PATH; point `KIMCHI_ACP_COMMAND` at the absolute binary path
  (e.g. `launchctl setenv KIMCHI_ACP_COMMAND /Users/you/.local/bin/kimchi`).
- **Project skills/config don't load through `kimchi-acp`** — the harness
  runs the session **untrusted** in projects it was never approved for
  (Hermes can't answer the harness's trust prompt; roadmap #9). Run
  `kimchi` once interactively in that project and approve it, or set
  `defaultProjectTrust: "always"` in the Kimchi global settings.

## Manual / multi-profile install

```bash
git clone https://github.com/getkimchi/kimchi-hermes
cd kimchi-hermes
./install.sh          # copies model-providers/* into ~/.hermes/plugins/model-providers/
hermes model          # pick "Kimchi" or "Kimchi (Harness via ACP)"
```

`install.sh` also targets every `~/.hermes/profiles/*/` plugin home, which is
what profile-scoped Desktop bots need. Hermes does not watch plugin files —
re-run it after every plugin change.

## Environment variables

| Variable | Plugin | Purpose |
|---|---|---|
| `KIMCHI_API_KEY` | kimchi | API key (checked before `~/.hermes/.env`) |
| `KIMCHI_BASE_URL` | kimchi | Override the inference gateway base URL — for the plugin this is the **OpenAI base including `/openai/v1`** (e.g. `https://llm.eu.kimchi.dev/openai/v1`; needed for EU/self-hosted keys). **Name collision:** the Kimchi harness reads the same-named variable with *bare* gateway-base semantics (no path — it appends `/openai/v1` itself) and its env override beats its own region config, so a shell-wide export also mis-derives the endpoints of the harness spawned by `kimchi-acp`. For non-US regions prefer the harness's own region selection (`KIMCHI_REGION`, or region choice at `kimchi login`) and scope `KIMCHI_BASE_URL` to where Hermes reads it |
| `KIMCHI_ACP_COMMAND` | kimchi-acp | Override the spawned binary (default `kimchi`) |
| `KIMCHI_ACP_ARGS` | kimchi-acp | Override spawn args. **Note: empty string falls back to the default args**; YOLO is **opt-in** — set `KIMCHI_ACP_ARGS="--mode acp --yolo"` |

## Roadmap & known gaps

Each item states **who owns the gap**: an explicit decision of ours, a
limitation of the upstream Kimchi harness ACP server, or a limitation of
Hermes' ACP shim. Source references are given so each claim is checkable.

### 1. Permission requests are relayed to no one (Hermes limitation; our workaround)

Hermes' ACP client auto-CANCELS every `session/request_permission` from the
subagent — there is no human channel in the shim
(`agent/copilot_acp_client.py::_handle_server_message` answers
`{"outcome": {"outcome": "cancelled"}}`; comment: "the ACP shim has no
human channel"). The default spawn therefore **keeps the harness's
permission prompts on** (`kimchi --mode acp`): tool-permission requests
are cancelled fail-safe, so approval-gated tools don't run and nothing
executes silently. YOLO mode (`--yolo`, Kimchi's designed no-restrictions
permission mode — `kimchi-harness/src/modes/acp/server.ts:149-154`) makes
harness tools execute **without human approval** and is **opt-in**:
`KIMCHI_ACP_ARGS="--mode acp --yolo"` (catalog review 2026-10-06 — enable
it only where unsupervised in-harness execution is acceptable, not in
shared gateway/cron contexts). Proper relay of permission prompts into
Hermes' approval UI requires upstreaming a generic ACP client — future
work.

### 2. In-session confirms/elicitation degrade to "no" (Kimchi limitation × Hermes limitation)

Kimchi's ACP server uses `session/request_permission` as a fallback for
general UI confirms (yes/no questions, choices) when the client does not
advertise elicitation support
(`kimchi-harness/src/modes/acp/acp-ui-context.test.ts:188-229`). Hermes'
shim neither advertises elicitation nor answers these requests (it
cancels — see #1), so such confirms resolve to "no"/cancelled (fail-safe).
Under YOLO (opt-in) this should only affect non-tool confirms; a tool-executing probe
(2026-09-25) saw zero confirm/permission traffic (SPEC §OQ-B3). The non-tool
confirm fallback path remains unexercised.

### 3. No true streaming; per-request cold start (Hermes shim limitation)

Hermes' shim blocks until the Kimchi turn finishes and then fake-chunks the
result — you will not see incremental token streaming from the harness
(`agent/copilot_acp_client.py::_run_prompt`). Each request also spawns a
fresh harness process (initialize + session/new), so every turn pays a
cold-start cost. Both are properties of the reused shim, accepted for v1.
Long agentic turns vs the shim's 900 s default timeout are under
investigation (SPEC §OQ-B5).

### 4. Images are dropped on the ACP path (Hermes shim limitation)

The shim flattens the conversation to text; image parts are silently
discarded (`agent/copilot_acp_client.py::_render_message_content`). Vision
through `kimchi-acp` is not supported in v1. The API-key path (`kimchi`)
is unaffected.

### 5. Tool routing — RESOLVED (2026-09-25, probes/acp_tool_execution_probe.py)

The Kimchi harness **executes its own tools for real** when driven over
ACP in YOLO mode (opt-in; probe: live tool_call updates, filesystem
artifact verified). Consequences, in order of importance:

1. **Harness-side execution is invisible to Hermes by default** — the
   shim forwards only text. **Addressed in this plugin** (commit 5b5362b):
   `KimchiACPClient` renders one markdown bullet per
   completed/failed tool (`- ⚙ **web_search** ✓ — excerpt`) into the
   visible reply (pending/in_progress churn suppressed), so activity
   shows in Hermes' UI and reaches later turns' context — the model can
   verify its own prior work. Residual: plain text lines, not Hermes'
   native tool cards (upstreaming a richer bridge remains future work).
2. **Hermes' forwarded toolset is effectively unused** — the harness
   prefers its native tools (observed under YOLO).
3. **Double-execution was NOT observed** — the model narrates results
   instead of emitting re-runnable tool-call blocks; residual risk noted.

Practical guidance: use `kimchi-acp` for harness-native agentic work —
tool activity is now visible inline and the model can verify its own
claims across turns. Use the `kimchi` API-key layer when you want
Hermes' tool pipeline fully in charge.

### 6. Model picker contents (resolved — shipped unfiltered)

The ACP session advertises the harness's full model registry —
provider-prefixed ids (`kimchi-dev/...`, `openai-codex/...`), the harness's
`auto` router mode, and real models like `auto-beta`. All ship unfiltered
(user decision 2026-09-25; the earlier "pseudo-entry filtering" plan is
retracted — `multi-model` never appeared live). Note: selecting an
`openai-codex/*` id means the *harness* (not Hermes) calls Codex — the
harness discovered it from this machine's environment. The `kimchi-acp`
row (harness session default) comes from the profile's fallback_models.

### 7. Copilot-branded errors (Hermes shim limitation; mitigated in plugin)

Because the plugin reuses Hermes' `CopilotACPClient`, its failure messages
reference Copilot ("Install GitHub Copilot CLI"). A thin subclass rewrites
the common cases to Kimchi guidance (SPEC §4); any paths the subclass
cannot reach will be documented here after e2e.

### 8. Upstreaming (deferred)

These plugins ship user-level first. Hermes' contribution policy has been
closing in-tree third-party plugin categories in favor of standalone
distribution (`CONTRIBUTING.md`, memory-provider closure); confirm with the
maintainers before proposing a bundled-provider PR. The full submission
checklist lives in [`UPSTREAM.md`](UPSTREAM.md).

### 9. Project trust gates project-scoped resources on the ACP path (Kimchi change 2026-09-28; Hermes limitation)

Since harness #1266 (LLM-3628), a headless ACP session resolves project
trust **fail-closed**: when the working directory has trust-requiring
resources (project skills, `.kimchi/`/`.claude/` config, permissions,
hooks, `.pi/settings.json`) and no stored decision, the session starts
untrusted and **silently drops all project-scoped resources**
(`kimchi-harness/src/project-trust.ts`, `src/modes/acp/server.ts`
`createSessionSettings`). The same commit added the client-side fix — a
`_kimchi.dev/project_trust_update` push plus a `set_project_trust` ext
method (Kimchi Studio prompts and un-blocks live) — but Hermes' shim can
neither call ext methods nor surface the push, so through `kimchi-acp`
the decision stays undecided and the drop persists. YOLO does **not**
bypass this: trust gates project-scoped resources, YOLO only gates
tool-approval prompts. User recovery: run `kimchi` once interactively in
the project (persists the decision to the harness's trust store), or set
`defaultProjectTrust: "always"` globally. Real support means upstreaming
trust handling into Hermes' ACP shim — same bucket as #1.

## Status

- **Layer 1 (`kimchi`) verified end-to-end** (2026-09-25): provider picker
  lists 20 live models; model switch + real turn on `glm-5.3-flash`
  succeeded (~41 t/s, `reasoning_effort: medium` accepted — SPEC OQ-A2
  default path works).
- **Layer 2 (`kimchi-acp`) verified end-to-end** (2026-09-25): live catalog,
  model selection via config options, session-default placeholder, and
  harness-native tool execution confirmed by probe (OQ-B3/B4 resolved;
  see roadmap #5). Verified in the TUI and the Desktop app (the latter
  after the spawn-target self-heal, commit e337a1a). Spawn default
  revised 2026-10-06 (catalog review): prompts-on `--mode acp`; YOLO
  now opt-in (roadmap #1).
- Ops note: `./install.sh` is a plain copy into `~/.hermes` — **re-run it
  after every plugin change**; Hermes does not watch the plugin files (a
  stale copy caused the 0-models incident on 2026-09-25).
- Spec reviewed (kimi-k3, glm-5.3 — both APPROVE-WITH-CHANGES, findings
  incorporated).
