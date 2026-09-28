# Upstream issue draft — open at NousResearch/hermes-agent

> Paste as a new GitHub **issue** (not PR) to signal intent before the PR,
> per their contributor etiquette. Link the kimchi-hermes repo for the full
> spec. Optionally cross-post in Discord `#plugins-skills-and-skins`.

---

**Title:** Add Kimchi (kimchi.dev) provider — API-key + ACP harness support (implementation ready)

**Summary**

We'd like to contribute first-class support for [Kimchi](https://kimchi.dev)
(Cast AI's coding-agent product): an OpenAI-compatible **inference API**
(`llm.kimchi.dev`) and an **ACP harness backend** (the Kimchi CLI runs the
turn over Agent Client Protocol, the same pattern as `copilot-acp`).

Both are implemented, tested, and verified end-to-end (TUI + Desktop on
macOS arm64); the working branch is ready to PR. **One question first —
placement.** We saw the standalone-plugin guidance for memory providers and
product integrations, and also the plugin catalog's standalone provider
precedents (`kiro-provider`, `telnyx-provider` — the latter
vendor-maintained, `category: models`). At the same time, 38 bundled
`model-providers` exist with in-tree additions as recent as this month
(`commandcode`, `kilocode`, `arcee`). **Which do you prefer for Kimchi —
bundled in-tree (PR ready) or a vendor-maintained standalone plugin with a
catalog entry (Telnyx pattern)?** We're the Kimchi maintainers, so the
standalone route also gives us direct update autonomy; happy with either.
Please correct us if the policy changed.

**What the providers do**

- `kimchi` — API-key provider against `https://llm.kimchi.dev/openai/v1`
  (OpenAI-compatible; `KIMCHI_API_KEY`, `KIMCHI_BASE_URL` override). Model
  catalog is discovered live from Kimchi's metadata endpoint
  (`/v1/models/metadata?include_in_cli=true` — ids under `slug`, retired
  models filtered); no hardcoded fallback list.
- `kimchi-acp` — external-process provider spawning `kimchi --mode acp
  --yolo` (default; `KIMCHI_ACP_ARGS` escape hatch). The subprocess owns its
  own auth — Hermes never handles a key on this path. Model selection goes
  through the standard `session/set_config_option` flow; a
  `kimchi-acp` placeholder model id means "harness session default".

**Notable findings from building it (may be useful beyond Kimchi)**

1. Hermes' ACP shim silently drops `tool_call`/`tool_call_update` session
   updates — harness-native execution is invisible in Hermes' UI and absent
   from later turns' flattened context (we observed the model disbelieving
   its own completed work and redoing it). Our profile renders terminal tool
   events as markdown bullets into the visible reply; a generic shim upgrade
   (render ACP tool events natively for *any* ACP provider, incl.
   `copilot-acp`) would be a better home for this and we're happy to
   contribute it separately.
2. Some client-construction paths (Desktop/auxiliary rebuilds) don't pass
   `command`/`args` to external-process clients, so the shim's fallback
   spawned the *copilot* CLI for our provider. We self-heal in the subclass;
   a generic fix (thread `process_command`/`process_args` through every
   construction path) may be worth doing upstream.
3. The gateway's WAF 403s catalog probes without `Accept: application/json`
   (the base `fetch_models` already sends it — profiles must not override
   the UA/header set).

**Verification** (macOS arm64, managed install)

- `hermes model` picker: both providers listed, live catalogs fetched
- real turns on both paths; Desktop app verified
- ACP probe: harness-native tool execution confirmed (filesystem artifact),
  zero permission requests under YOLO

**Tests:** hermetic pytest under `tests/plugins/model_providers/`
(`test_kimchi_profile.py`, `test_kimchi_acp_profile.py`) — registration,
catalog shape adapter, spawn-target healing, tool rendering, placeholder
selection, `setup_status`. No new dependencies.
