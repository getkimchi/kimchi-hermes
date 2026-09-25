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
See [`SPEC.md`](SPEC.md) for the full spec and evidence table.

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
| `KIMCHI_ACP_ARGS` | kimchi-acp | Override spawn args (default `--mode acp --yolo`) |

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
human approval.** Proper relay of permission prompts into Hermes' approval
UI requires upstreaming a generic ACP client — future work.

### 2. In-session confirms/elicitation degrade to "no" (Kimchi limitation × Hermes limitation)

Kimchi's ACP server uses `session/request_permission` as a fallback for
general UI confirms (yes/no questions, choices) when the client does not
advertise elicitation support
(`kimchi-harness/src/modes/acp/acp-ui-context.test.ts:188-229`). Hermes'
shim neither advertises elicitation nor answers these requests (it
cancels — see #1), so such confirms resolve to "no"/cancelled (fail-safe).
Under YOLO this should only affect non-tool confirms; adversarial turns are
part of e2e verification (SPEC §OQ-B3) and outcomes will be recorded here.

### 3. Model selection through ACP (under investigation)

Hermes selects models via `session/set_config_option` / legacy
`session/set_model` based on what `session/new` advertises
(`agent/copilot_acp_client.py`). Whether Kimchi's `session/new` advertises
model config options is unverified (SPEC §OQ-B2). If it does not, picking a
specific model under `kimchi-acp` falls back to the session default.

### 4. Reasoning-effort pass-through on the API-key path (under investigation)

Whether `llm.kimchi.dev` accepts `reasoning_effort` and at which levels is
unverified (SPEC §OQ-A2). A `build_api_kwargs_extras` override will be added
only if the live gateway needs it.

### 5. Upstreaming (deferred)

These plugins ship user-level first. Hermes' contribution policy has been
closing in-tree third-party plugin categories in favor of standalone
distribution (`CONTRIBUTING.md`, memory-provider closure); confirm with the
maintainers before proposing a bundled-provider PR.

## Status

Spec approved pending review (`SPEC.md`). Implementation has not started.
