# kimchi-acp-provider — the Kimchi harness over ACP

Hermes Agent model-provider plugin: Hermes spawns the
[Kimchi](https://kimchi.dev) coding harness (`kimchi --mode acp --yolo`)
and the harness itself serves each turn over stdio (Agent Client
Protocol). The harness's own tools (shell, file edits, web search)
execute inside the harness; completed tool calls are surfaced in the
reply as markdown bullets (`- ⚙ **web_search** ✓ — excerpt`).

This is Layer 2 — the primary use case — of the
[kimchi-hermes](https://github.com/getkimchi/kimchi-hermes) monorepo.
The API-key alternative [`kimchi-provider`](../kimchi/) keeps Hermes'
tool pipeline in charge instead.

## Install

```bash
hermes plugins install getkimchi/kimchi-hermes/model-providers/kimchi-acp
# or, once listed in the Hermes plugin catalog:
hermes plugins install kimchi-acp-provider
```

## Prerequisites

- The [Kimchi CLI](https://kimchi.dev) on PATH and logged in
  (`kimchi login`). The subprocess owns its own auth — **no API key is
  shared with Hermes**.

## Use

```bash
hermes model    # pick "Kimchi (Harness via ACP)"
hermes          # tool-using turns show inline harness tool bullets
```

The model picker lists the harness's live advertised models
(provider-prefixed ids such as `kimchi-dev/...`, plus its `auto`
router mode). The `kimchi-acp` row means "harness session default"
(no explicit model selection).

## Environment variables

| Variable | Purpose |
|---|---|
| `KIMCHI_ACP_COMMAND` | Override the spawned binary (default `kimchi`). In GUI apps (Hermes Desktop), point this at the absolute binary path — GUI apps do not inherit your shell PATH. |
| `KIMCHI_ACP_ARGS` | Override the spawn args. **Trap: an empty value falls back to the default args (including `--yolo`)** — to run without YOLO set `KIMCHI_ACP_ARGS="--mode acp"`. |

## Behaviour & disclosures

- **Subprocess**: every turn spawns `kimchi --mode acp --yolo` and
  speaks JSON-RPC over stdio; the process is terminated when the turn
  ends. `--yolo` is Kimchi's designed no-restrictions permission mode:
  tools inside the harness (shell commands, file writes, web requests)
  execute **without approval prompts**. Without YOLO, permission
  requests are cancelled fail-safe (Hermes' ACP shim has no human
  approval channel yet — see the monorepo README's roadmap for the
  full picture and the upstream feature request it implies).
- **Reads outside the plugin's own data**: to report setup status, the
  plugin checks whether the Kimchi CLI is logged in by reading the
  Kimchi CLI's own config (`~/.config/kimchi/config.json`, or
  `KIMCHI_CONFIG_PATH` overridable) — it checks for the *presence* of
  a stored key only; the key itself is never read by Hermes or sent
  anywhere.
- **Auth**: `env_vars=()` — the harness subprocess authenticates
  itself with its own credential store; Hermes never handles a Kimchi
  key on this path.
- **Reply rendering**: completed/failed tool calls are rendered as one
  markdown bullet each in the visible reply (registration and
  in-progress churn suppressed), so harness tool activity is visible
  in Hermes' UI and reaches later turns' context.
- Registers only a provider profile (`register_provider`); no tools,
  no hooks, no middleware.

## Known limitations

- No incremental streaming — Hermes' ACP shim blocks until the turn
  completes, then chunks the result; each turn also pays a
  fresh-process cold start.
- Images are dropped on the ACP path (vision unsupported here; the
  API-key `kimchi-provider` layer is unaffected).
- In-session yes/no confirms from the harness degrade to "no"
  (fail-safe).

Details, evidence and the decision log: monorepo
[README](https://github.com/getkimchi/kimchi-hermes#readme) and
[`SPEC.md`](../../SPEC.md).
