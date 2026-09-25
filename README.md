# kimchi-hermes

Hermes Agent provider plugins for [Kimchi](https://kimchi.dev):

- **`kimchi`** — API-key model provider. Hermes' own agent loop drives
  Kimchi-served models over the OpenAI-compatible gateway
  (`https://llm.kimchi.dev/openai/v1`).
- **`kimchi-acp`** — ACP external-process provider. Hermes spawns
  `kimchi --mode acp --yolo` and the **Kimchi harness itself** serves the
  turn over stdio (Agent Client Protocol). This is the primary use case.

Both are user-level plugins: they install into
`~/.hermes/plugins/model-providers/` and require no changes to Hermes core.
See [`SPEC.md`](SPEC.md) for the full spec, evidence table, and decision log.

## Install

```bash
./install.sh          # copies model-providers/* into ~/.hermes/plugins/model-providers/
hermes model          # pick "Kimchi" or "Kimchi (Harness via ACP)"
```

Requirements:
- `kimchi` — a Kimchi API key (get one at https://app.kimchi.dev)
- `kimchi-acp` — the Kimchi CLI installed and logged in (`kimchi login`);
  no key is shared with Hermes (the subprocess owns its own auth)

## Environment variables

| Variable | Plugin | Purpose |
|---|---|---|
| `KIMCHI_API_KEY` | kimchi | API key (checked before `~/.hermes/.env`) |
| `KIMCHI_BASE_URL` | kimchi | Override the inference gateway base URL |
| `KIMCHI_ACP_COMMAND` | kimchi-acp | Override the spawned binary (default `kimchi`) |
| `KIMCHI_ACP_ARGS` | kimchi-acp | Override spawn args. **Note: empty string falls back to the default args** (including `--yolo`); to run *without* YOLO set `KIMCHI_ACP_ARGS="--mode acp"` |

## Roadmap & known gaps

Each item states **who owns the gap**: an explicit decision of ours, a
limitation of the upstream Kimchi harness ACP server, or a limitation of
Hermes' ACP shim. Source references are given so each claim is checkable.

### 1. Permission requests are relayed to no one (Hermes limitation; our workaround)

Hermes' ACP client auto-CANCELS every `session/request_permission` from the
subagent — there is no human channel in the shim
(`agent/copilot_acp_client.py::_handle_server_message` answers
`{"outcome": {"outcome": "cancelled"}}`; comment: "the ACP shim has no
human channel"). Our workaround is a decision: spawn the harness in YOLO
mode (`--yolo`, Kimchi's designed no-restrictions permission mode —
`kimchi-harness/src/modes/acp/server.ts:149-154`), so tool-permission
prompts never fire. **Consequence: tools inside the harness execute without
human approval.** Without YOLO (`KIMCHI_ACP_ARGS="--mode acp"`), permission
requests are silently denied (fail-safe). Proper relay of permission
prompts into Hermes' approval UI requires upstreaming a generic ACP client
— future work.

### 2. In-session confirms/elicitation degrade to "no" (Kimchi limitation × Hermes limitation)

Kimchi's ACP server uses `session/request_permission` as a fallback for
general UI confirms (yes/no questions, choices) when the client does not
advertise elicitation support
(`kimchi-harness/src/modes/acp/acp-ui-context.test.ts:188-229`). Hermes'
shim neither advertises elicitation nor answers these requests (it
cancels — see #1), so such confirms resolve to "no"/cancelled (fail-safe).
Under YOLO this should only affect non-tool confirms; adversarial turns are
part of e2e verification (SPEC §OQ-B3) and outcomes will be recorded here.

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

### 5. Tool-routing collision under YOLO (under investigation — key risk)

Under YOLO the Kimchi harness executes its own tools during a turn, while
Hermes' shim instructs the agent to emit OpenAI-shaped tool-call text
blocks that Hermes then executes itself. Whether both happen on the same
turn (double execution) and how to route tools (harness-side vs
Hermes-side) is the main open question (SPEC §OQ-B4); resolution options
and the e2e probe plan are in the spec.

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
maintainers before proposing a bundled-provider PR.

## Status

- **Layer 1 (`kimchi`) verified end-to-end** (2026-09-25): provider picker
  lists 20 live models; model switch + real turn on `glm-5.3-flash`
  succeeded (~41 t/s, `reasoning_effort: medium` accepted — SPEC OQ-A2
  default path works).
- **Layer 2 (`kimchi-acp`)**: catalog probe verified live (31 models after
  pseudo-entry filtering); real-turn verification pending (OQ-B4).
- Ops note: `./install.sh` is a plain copy into `~/.hermes` — **re-run it
  after every plugin change**; Hermes does not watch the plugin files (a
  stale copy caused the 0-models incident on 2026-09-25).
- Spec reviewed (kimi-k3, glm-5.3 — both APPROVE-WITH-CHANGES, findings
  incorporated).
