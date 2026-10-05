# kimchi-provider — Kimchi models via API key

Hermes Agent model-provider plugin: use [Kimchi](https://kimchi.dev)
models with Hermes' own agent loop over the OpenAI-compatible gateway
(`https://llm.kimchi.dev/openai/v1`).

This is Layer 1 of the two-plugin
[kimchi-hermes](https://github.com/getkimchi/kimchi-hermes) monorepo —
the API-key alternative to
[`kimchi-acp-provider`](../kimchi-acp/), which drives the full Kimchi
harness over ACP.

## Install

```bash
hermes plugins install getkimchi/kimchi-hermes/model-providers/kimchi
# or, once listed in the Hermes plugin catalog:
hermes plugins install kimchi-provider
```

The installer prompts for `KIMCHI_API_KEY` if it is not already set
(the key is stored in `~/.hermes/.env`, masked at entry).

## Authenticate

```bash
export KIMCHI_API_KEY=...   # or persist it in ~/.hermes/.env
```

## Use

```bash
hermes model    # pick "Kimchi"
hermes          # you're on Kimchi
```

Or make it the default in `~/.hermes/config.yaml`:

```yaml
model:
  default: glm-5.3-flash
  provider: kimchi
```

The model picker lists the **live catalog** fetched from Kimchi's model
metadata endpoint. There is deliberately no hardcoded fallback list: a
transient fetch failure means an empty picker until the next attempt —
never a stale list.

## Environment variables

| Variable | Purpose |
|---|---|
| `KIMCHI_API_KEY` | API key (required; checked before `~/.hermes/.env`) |
| `KIMCHI_BASE_URL` | Override the inference gateway base URL |

## Behaviour & disclosures

- **Network**: fetches the live model catalog from
  `https://llm.kimchi.dev/v1/models/metadata` with your API key
  attached (Authorization header, via Hermes' credentialed-URL
  wrapper). Model inference goes through Hermes' own provider client
  to `https://llm.kimchi.dev/openai/v1`.
- **Credentials**: none stored by the plugin — the key is resolved by
  Hermes' built-in env / `~/.hermes/.env` ladder.
- **Error mapping**: the Kimchi gateway's
  "no registered providers found" 400 (unknown model id) is classified
  as `model_not_found`, so Hermes' model-not-found recovery applies
  instead of a generic format error.
- Registers only a provider profile (`register_provider`); no tools,
  no hooks, no middleware.

## Known limitations

See the monorepo
[README](https://github.com/getkimchi/kimchi-hermes#readme)
(Roadmap & known gaps) and [`SPEC.md`](../../SPEC.md) for the full
evidence table and decision log.
